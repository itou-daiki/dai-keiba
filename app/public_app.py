import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import pickle
import json
import plotly.express as px
import plotly.graph_objects as go
import time

# Add paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT, 'scraper'))
sys.path.append(os.path.join(PROJECT_ROOT, 'ml'))

try:
    import importlib
    import auto_scraper
    importlib.reload(auto_scraper) # Force reload to apply fixes
    from feature_engineering import process_data
    from db_helper import KeibaDatabase
except ImportError as e:
    st.error(f"Import Error: {e}")

st.set_page_config(page_title="AI Keiba Predictor", layout="wide")

# --- Utils ---
@st.cache_resource
def load_model(mode="JRA"):
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"ml/models/lgbm_model_nar.pkl" if mode == "NAR" else "ml/models/lgbm_model.pkl")
    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    return None

@st.cache_resource
def load_model_metadata(mode="JRA"):
    """モデルのメタデータ（訓練日時、性能指標など）を読み込む"""
    meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"ml/models/lgbm_model_nar_meta.json" if mode == "NAR" else "ml/models/lgbm_model_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@st.cache_resource
def load_history_csv(mode):
    """過去データをキャッシュとしてロード (高速化)"""
    csv_path = os.path.join(PROJECT_ROOT, "data", "raw", "database_nar.csv" if mode == "NAR" else "database.csv")
    if os.path.exists(csv_path):
        try:
            # 高速化のために必要な列だけ...といきたいが、汎用性を考え全読み込み
            return pd.read_csv(csv_path, dtype={'horse_id': str, 'race_id': str})
        except:
            pass
    return None

def get_data_freshness(mode="JRA"):
    """データベースの最終更新日時を取得（SQL対応）"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keiba_data.db")
    if os.path.exists(db_path):
        try:
            db = KeibaDatabase(db_path)
            freshness = db.get_data_freshness(mode)
            return freshness, 0  # 鮮度情報を文字列で返す
        except Exception as e:
            st.warning(f"データ鮮度の取得に失敗: {e}")
            return "不明", -1
    return "DBなし", -1
    return None, None

def calculate_confidence_score(ai_prob, model_meta, jockey_compat=None, course_compat=None, distance_compat=None, is_rest_comeback=0):
    """
    予測の信頼度スコアを計算（0-100）

    Args:
        ai_prob: AI予測確率（0-1）
        model_meta: モデルメタデータ
        jockey_compat: 騎手相性スコア（0-10、Noneの場合は考慮しない）
        course_compat: コース適性スコア（0-10、Noneの場合は考慮しない）
        distance_compat: 距離適性スコア（0-10、Noneの場合は考慮しない）
        is_rest_comeback: 休養明けフラグ（1=True, 0=False）

    Returns:
        int: 信頼度スコア（0-100）
    """
    if not model_meta:
        return 50  # デフォルト

    # ===== 1. ベース信頼度: モデルのAUCから算出 =====
    base_confidence = model_meta.get('performance', {}).get('auc', 0.75) * 100

    # ===== 2. データ量による調整 =====
    data_size = model_meta.get('data_stats', {}).get('total_records', 0)
    if data_size < 1000:
        data_penalty = -20  # データ量少ない
    elif data_size < 3000:
        data_penalty = -8
    elif data_size < 5000:
        data_penalty = -3
    else:
        data_penalty = 0

    # ===== 3. 予測確率による調整（連続的な調整） =====
    # 0.5から離れるほど信頼度が高い（モデルが確信を持っている）
    # 0.5に近いほど信頼度が低い（モデルが迷っている）
    distance_from_uncertain = abs(ai_prob - 0.5)

    # 距離に基づく信頼度ボーナス: 0.5離れていると最大+20、0.0だと-20
    # 式を調整して範囲を拡大
    prob_bonus = (distance_from_uncertain * 2 - 0.25) * 40

    # さらに極端な予測（<0.05 or >0.95）には追加ボーナス
    if ai_prob < 0.05 or ai_prob > 0.95:
        prob_bonus += 12

    # AI確率が極端に低い場合は信頼度を下げる（データ不足の可能性）
    if ai_prob < 0.08:
        prob_bonus -= 10

    # ===== 4. 適性スコアによる調整（新規追加） =====
    compat_bonus = 0

    # 利用可能な適性スコアを集計
    compat_scores = []
    if jockey_compat is not None and not pd.isna(jockey_compat):
        compat_scores.append(jockey_compat)
    if course_compat is not None and not pd.isna(course_compat):
        compat_scores.append(course_compat)
    if distance_compat is not None and not pd.isna(distance_compat):
        compat_scores.append(distance_compat)

    if compat_scores:
        avg_compat = sum(compat_scores) / len(compat_scores)
        min_compat = min(compat_scores)

        # 平均適性による調整
        if avg_compat >= 9:
            compat_bonus = +15  # 全て高適性
        elif avg_compat >= 7:
            compat_bonus = +8
        elif avg_compat >= 5:
            compat_bonus = 0
        elif avg_compat >= 3:
            compat_bonus = -12
        else:
            compat_bonus = -25  # データ品質が低い

        # 最低スコアによる追加ペナルティ（いずれかの適性が極端に低い場合）
        if min_compat < 3:
            compat_bonus -= 15  # 致命的な不適性
        elif min_compat < 5:
            compat_bonus -= 8

    # ===== 5. 休養明け・間隔による調整 (新規追加) =====
    interval_penalty = 0
    if is_rest_comeback == 1:
        interval_penalty = -10 # 長期休養明けは不確定要素が多い

    # ===== 最終計算 =====
    confidence = base_confidence + data_penalty + prob_bonus + compat_bonus + interval_penalty

    # 範囲を拡大: 20-95（より差別化）
    return int(max(20, min(95, confidence)))

def predict_race_logic(df, model, model_meta):
    """
    データフレームに対してAI予測と信頼度計算を行う
    """
    try:
        # 特徴量エンジニアリング（会場特性あり）
        X_df = process_data(df, use_venue_features=True)

        # Align features with model
        if hasattr(model, 'feature_name'):
             model_features = model.feature_name()
             # Ensure all features exist
             for f in model_features:
                 if f not in X_df.columns:
                     X_df[f] = 0
             
             X_pred = X_df[model_features].fillna(0)
        else:
             # Fallback for older sklearn models or if feature_name not available
             meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
             features = [c for c in X_df.columns if c not in meta_cols and c != 'target_win']
             X_pred = X_df[features].select_dtypes(include=['number']).fillna(0)

        # Predict
        probs = model.predict(X_pred)

        df['AI_Prob'] = probs
        df['AI_Score'] = (probs * 100).astype(int)

        # Calculate Confidence
        confidences = []
        for idx, p in enumerate(probs):
            jockey_c = X_df['jockey_compatibility'].iloc[idx] if 'jockey_compatibility' in X_df.columns else None
            distance_c = X_df['distance_compatibility'].iloc[idx] if 'distance_compatibility' in X_df.columns else None
            
            # Course compatibility
            course_c = None
            if 'turf_compatibility' in X_df.columns and 'dirt_compatibility' in X_df.columns:
                if 'コースタイプ' in df.columns:
                    course_type = df['コースタイプ'].iloc[idx]
                    if '芝' in str(course_type):
                        course_c = X_df['turf_compatibility'].iloc[idx]
                    elif 'ダ' in str(course_type):
                        course_c = X_df['dirt_compatibility'].iloc[idx]
                else:
                    course_c = X_df['turf_compatibility'].iloc[idx] # Default

            is_rest = X_df['is_rest_comeback'].iloc[idx] if 'is_rest_comeback' in X_df.columns else 0

            conf = calculate_confidence_score(p, model_meta, jockey_c, course_c, distance_c, is_rest)
            confidences.append(conf)

        df['Confidence'] = confidences

        # Merge relevant features back to df
        cols_to_merge = [
            'turf_compatibility', 'dirt_compatibility', 
            'jockey_compatibility', 'distance_compatibility', 
            'weighted_avg_speed', 'weighted_avg_rank'
        ]
        for c in cols_to_merge:
            if c in X_df.columns:
                df[c] = X_df[c]
                
        return df
    except Exception as e:
        import traceback
        st.error(f"Prediction Error: {e}")
        st.code(traceback.format_exc())
        return None

def load_schedule_data(mode="JRA"):
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temp", "todays_data_nar.json" if mode == "NAR" else "todays_data.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# --- UI ---
st.title("🏇 AI競馬予想システム")

# Logic Explanation
with st.expander("ℹ️ このAI予想のロジックについて (クリックして開く)"):
    st.markdown("""
    ### 🧠 AI予想の仕組み
    このシステムは**LightGBM**という機械学習モデルを使用し、過去の膨大なレースデータから「1着（勝利）の確率」を算出しています。
    
    #### 使用しているデータ
    - **基本情報**: 枠番、馬番、馬齢、斤量、騎手
    - **過去5走の成績**: 着順、走破タイム、上り3F、通過順（脚質）、馬体重、馬場状態、**天気**、**最終オッズ**
    - **直近重視**: 過去のレースは直近のものほど重要視する「時間減衰」処理を行っています。
    
    #### 🎯 期待値 (EV) とは？
    「その馬券を買い続けたときに、最終的にいくら儲かるか」の指標です。
    
    $$
    \text{調整後期待値} = (\text{AIの勝率} \times \text{あなたの印} \times \text{オッズ}) - 1.0
    $$
    
    - **プラス (0以上)**: 買えば買うほど儲かるチャンスがある馬（推奨！）
    - **マイナス**: 勝つ確率に比べてオッズが低すぎる（割に合わない）馬
    - **あなたの印**: AIの予測に、あなたの直感（◎や◯）をミックスして計算します。AIだけでなく、あなたの相馬眼も反映されます。

    #### 🏇 中央競馬 vs 🌙 地方競馬
    このシステムは、会場から自動的に中央競馬（JRA）と地方競馬（NAR）を判定し、それぞれに最適化された期待値を計算します。

    **中央競馬（JRA）:**
    - 印の補正係数: ◎=1.3倍, ◯=1.15倍（控えめ）
    - 安全フィルタ: AI確率8%未満は除外
    - 特徴: レベルが高く、予想が堅め

    **地方競馬（NAR）:**
    - 印の補正係数: ◎=1.8倍, ◯=1.4倍（積極的）
    - 安全フィルタ: AI確率5%未満は除外
    - 特徴: 波乱が多く、人気薄が勝ちやすい

    #### 📊 信頼性向上の取り組み
    - **モデルメタデータ**: 訓練日時、性能指標（AUC）、データ量を常時表示
    - **予測信頼度スコア**: 各予測にモデルの信頼性を0-100%で数値化
    - **データ新鮮度**: データベースの最終更新日時を表示（3日以内が理想）
    - **注意喚起**: データ量不足や予測の限界を明示
    - **透明性**: モデルの性能・限界を隠さず開示
    """)

# --- Admin Menu ---
st.markdown("### 設定")
mode = st.radio("開催モード (Mode)", ["JRA (中央競馬)", "NAR (地方競馬)"], horizontal=True)
mode_val = "JRA" if "JRA" in mode else "NAR"

with st.expander("🛠️ 管理ツール (スケジュール更新など)"):
    col_admin_1, col_admin_2 = st.columns([1, 1])
    with col_admin_1:
         if st.button("📅 レース一覧を更新 (今後1週間)"):
            with st.spinner(f"{mode_val}の最新レース情報を取得中..."):
                success, msg = auto_scraper.scrape_todays_schedule(mode=mode_val)
                if success:
                    st.success(msg)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"エラー: {msg}")
    
    with col_admin_2:
         if st.button("🧠 AIモデルを再読み込み"):
             st.cache_resource.clear()
             st.success("モデルキャッシュをクリアしました。次回予測時に再ロードされます。")

st.markdown("---")

# --- Analysis Mode Selection ---
st.markdown("### 分析モード")
analysis_mode = st.radio("機能を選択", ["🔍 個別レース分析", "💎 堅いレースを探す (一括分析)"], horizontal=True)

st.markdown("---")

# --- Race Selection ---
st.subheader("📍 レース選択")

schedule_data = load_schedule_data(mode=mode_val)
race_id = None

if schedule_data and "races" in schedule_data:
    races = schedule_data['races']
    
    # 1. Filter by Date
    dates = sorted(list(set([r.get('date', 'Unknown') for r in races])))
    
    if analysis_mode == "🔍 個別レース分析":
        # Layout columns for selection
        col_date, col_venue, col_race = st.columns(3)
        
        with col_date:
             selected_date = st.selectbox("1. 日付を選択", dates)
        
        # Filter races by date
        todays_races = [r for r in races if r.get('date') == selected_date]
        
        if todays_races:
            # 2. Filter by Venue
            venues = sorted(list(set([r['venue'] for r in todays_races])))
            
            with col_venue:
                selected_venue = st.selectbox("2. 開催地を選択", venues)
                
            # Filter races by venue
            venue_races = [r for r in todays_races if r['venue'] == selected_venue]
            
            # 3. Select Race
            # Sort by race number
            venue_races.sort(key=lambda x: int(x['number']) if str(x['number']).isdigit() else 0)
            
            race_options = {f"{r['number']}R: {r['name']}": r['id'] for r in venue_races}
            
            with col_race:
                selected_label = st.selectbox("3. レースを選択", list(race_options.keys()))
                if selected_label:
                    race_id = race_options[selected_label]
        else:
            st.warning(f"{selected_date} のレースはありません。")

    elif analysis_mode == "💎 堅いレースを探す (一括分析)":
        st.info("💡 **機能説明**: 指定した日の全レースをAIが分析し、信頼度が高い「堅いレース」のみを抽出します。")
        
        col_date, col_venue_multi = st.columns([1, 2])
        with col_date:
             selected_date = st.selectbox("1. 日付を選択", dates)
        
        todays_races = [r for r in races if r.get('date') == selected_date]
        if todays_races:
            venues = sorted(list(set([r.get('venue', 'Unknown') for r in todays_races])))
            
            with col_venue_multi:
                 selected_venues = st.multiselect("2. 開催地を選択 (空欄で全会場)", venues, default=venues)
            
            target_races = [r for r in todays_races if not selected_venues or r.get('venue') in selected_venues]
            st.write(f"対象レース数: {len(target_races)} レース")
            
            confidence_threshold = st.slider("信頼度フィルター (これ以上の信頼度のレースを表示)", 0, 100, 80)
            
            if st.button("🚀 一括分析を開始する", type="primary"):
                 if not target_races:
                     st.warning("対象レースがありません。")
                 else:
                     with st.spinner("モデルを読み込み中..."):
                         # from app.public_app import load_model, load_model_metadata
                         model = load_model(mode_val)
                         model_meta = load_model_metadata(mode_val)
                     
                     if not model:
                         st.error("モデルの読み込みに失敗しました。")
                     else:
                         results_container = st.container()
                         progress_bar = st.progress(0)
                         status_text = st.empty()
                         
                         solid_races_data = []
                         
                         for i, race in enumerate(target_races):
                             r_name = f"{race['venue']}{race['number']}R: {race['name']}"
                             status_text.text(f"分析中 ({i+1}/{len(target_races)}): {r_name}...")
                             
                             try:
                                 # 1. Scrape with cached history
                                 if i > 0: time.sleep(1) 
                                 history_df_cache = load_history_csv(mode_val)
                                 df_race = auto_scraper.scrape_shutuba_data(race['id'], mode=mode_val, history_df=history_df_cache)
                                 
                                 if df_race is not None and not df_race.empty:
                                     # 2. Predict
                                     processed_df = predict_race_logic(df_race, model, model_meta)
                                     
                                     if processed_df is not None:
                                         # 3. Find Top Horses (Top 3)
                                         processed_df = processed_df.sort_values('AI_Score', ascending=False)
                                         
                                         top_horse = processed_df.iloc[0]
                                         conf = top_horse['Confidence']
                                         
                                         # Construct Multi-Horse String
                                         picks_str = []
                                         marks = ["◎", "◯", "▲", "△", "☆"]
                                         
                                         # Helper for circled numbers (local scope)
                                         def to_circled_num_local(n):
                                             try:
                                                 n = int(n)
                                                 if 1 <= n <= 20:
                                                     return chr(9311 + n)
                                                 return f"({n})"
                                             except:
                                                 return ""

                                         for rank in range(min(5, len(processed_df))):
                                             h = processed_df.iloc[rank]
                                             m = marks[rank]
                                             h_num = h.get('馬 番', '')
                                             c_num = to_circled_num_local(h_num)
                                             picks_str.append(f"{m} {c_num} {h['馬名']} ({h['AI_Score']}%)")
                                         
                                         picks_display = " / ".join(picks_str)

                                         if conf >= confidence_threshold:
                                             solid_races_data.append({
                                                 "会場": race['venue'],
                                                 "R": f"{race['number']}R",
                                                 "レース名": race['name'],
                                                 "AI予想 (◎/◯/▲/△/☆)": picks_display,
                                                  # "本命馬": top_horse['馬名'], # Removed in favor of multi-display
                                                 "信頼度": f"{conf}%",
                                                 # "AI指数": f"{score}%", # Included in string
                                                 "race_id": race['id']
                                             })
                             
                             except Exception as e:
                                 print(f"Error analyzing {race['id']}: {e}")
                                 
                             progress_bar.progress((i + 1) / len(target_races))
                         
                         status_text.success(f"完了！ {len(target_races)}レース中、条件を満たすレースは {len(solid_races_data)} 件でした。")
                         
                         if solid_races_data:
                             st.markdown("### 💎 堅いレース候補")
                             res_df = pd.DataFrame(solid_races_data)
                             st.dataframe(res_df, use_container_width=True)
                             st.info("詳細を見たい場合は、上の「個別レース分析」モードで該当レースを選択してください。")
                         else:
                             st.warning("条件を満たす堅いレースは見つかりませんでした。信頼度基準を下げてみてください。")
        else:
             st.warning(f"{selected_date} のレースはありません。")
        
else:
    st.warning("レースデータがありません。管理者メニューから更新ボタンを押してください。")
    # No fallback text input for now to keep it clean, or keep it inside Individual mode if needed.
    # But existing code had it. Let's omitting it for Batch mode safety.
    if analysis_mode == "🔍 個別レース分析":
         race_id = st.text_input("レースID直接入力 (12桁)", value="202305021211")


# Main Analysis
if race_id:
    st.header(f"レース分析: {race_id}")

    # Load Model and Metadata
    model = load_model(mode=mode_val)
    model_meta = load_model_metadata(mode=mode_val)
    last_updated, days_ago = get_data_freshness(mode=mode_val)

    # Display Model Information and Data Freshness
    with st.expander("📊 モデル情報・データ品質", expanded=False):
        if model_meta:
            col_info1, col_info2, col_info3 = st.columns(3)

            with col_info1:
                st.metric(
                    "モデルAUC（予測精度）",
                    f"{model_meta.get('performance', {}).get('auc', 0):.3f}",
                    help="0.5=ランダム、1.0=完全予測。0.75以上が目安"
                )
                st.caption(f"学習データ量: {model_meta.get('data_stats', {}).get('total_records', 0):,}件")

            with col_info2:
                if last_updated:
                    freshness_color = "🟢" if days_ago <= 3 else "🟡" if days_ago <= 7 else "🔴"
                    st.metric(
                        "データ最終更新",
                        f"{days_ago}日前",
                        delta=f"{freshness_color} {last_updated}"
                    )
                else:
                    st.metric("データ最終更新", "不明")

            with col_info3:
                data_size = model_meta.get('data_stats', {}).get('total_records', 0)
                if data_size < 1000:
                    quality = "⚠️ 小規模"
                    quality_help = "データ量が少ないため、予測精度は限定的です"
                elif data_size < 3000:
                    quality = "🟡 中規模"
                    quality_help = "さらにデータを増やすと精度向上が期待できます"
                else:
                    quality = "🟢 十分"
                    quality_help = "十分なデータ量で学習されています"

                st.metric("データ品質", quality, help=quality_help)

            # Warnings
            if model_meta.get('warnings'):
                st.warning("**⚠️ 注意事項:**\n" + "\n".join([f"- {w}" for w in model_meta['warnings']]))
        else:
            st.info("モデルメタデータが見つかりません")

    button_analyze = st.button("🚀 このレースを分析する (データ取得・AI予測)", type="primary", use_container_width=True)

    if button_analyze:
        if not race_id:
             st.error("レースIDが選択されていません。")
        elif not model:
             st.error(f"モデル ({mode_val}) が読み込めませんでした。管理画面で学習を実行するか、モデルファイルを確認してください。")
        else:
            # === 処理フローの可視化 ===
            st.markdown("---")
            st.subheader("🔄 AI予測処理フロー")

            # ステップ表示用のプログレスバー
            progress_bar = st.progress(0)
            status_text = st.empty()

            # ステップ1: データ取得
            status_text.info("**ステップ 1/4:** 出馬表データを取得中...")
            progress_bar.progress(25)
            history_df_cache = load_history_csv(mode_val)
            df = auto_scraper.scrape_shutuba_data(race_id, mode=mode_val, history_df=history_df_cache)

            if df is not None and not df.empty:
                status_text.success("✅ ステップ 1/4: 出馬表データを取得しました")

                # ステップ2-4: AI予測プロセス（共通関数化）
                status_text.info("**ステップ 2-4:** 特徴量計算・AI予測・信頼度算出を実行中...")
                progress_bar.progress(60)
                
                if model:
                    processed_df = predict_race_logic(df, model, model_meta)
                    
                    if processed_df is not None:
                         df = processed_df
                         status_text.success("✅ AI分析が完了しました！")
                         progress_bar.progress(100)
                    else:
                         status_text.error("❌ 予測処理中にエラーが発生しました。")
                         df['AI_Prob'] = 0.0
                         df['AI_Score'] = 0.0
                else:
                     status_text.warning("モデルが見つかりません。予測スキップ。")
                     df['AI_Prob'] = 0.0
                     df['AI_Score'] = 0.0

                # 4. Display
                # Store in session state to persist edits
                st.session_state[f'data_{race_id}'] = df

                # 完了メッセージ
                st.markdown("---")
                st.success("🎉 **AI分析が完了しました！** 下記の結果をご確認ください。")
            else:
                st.error("データの取得に失敗しました。")

    # Show Data if available
    if f'data_{race_id}' in st.session_state:
        df_display = st.session_state[f'data_{race_id}'].copy()

        # === レース概要の表示 ===
        st.markdown("---")
        st.subheader("🏇 レース概要")

        # レース基本情報
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            # Try multiple possible column names for venue
            venue = "不明"
            for col in ['会場', 'venue', '競馬場', '場所']:
                if col in df_display.columns and len(df_display) > 0:
                    venue = df_display[col].iloc[0]
                    if pd.notna(venue) and venue != "":
                        break

            # If still unknown, try to extract from race_id (first 4 digits indicate place code)
            if venue == "不明" and race_id and len(race_id) >= 6:
                try:
                    place_code = int(race_id[4:6])
                    place_map = {
                        1: "札幌", 2: "函館", 3: "福島", 4: "新潟", 5: "東京",
                        6: "中山", 7: "中京", 8: "京都", 9: "阪神", 10: "小倉",
                        30: "門別", 35: "盛岡", 36: "水沢", 42: "浦和", 43: "船橋",
                        44: "大井", 45: "川崎", 46: "金沢", 47: "笠松", 48: "名古屋",
                        50: "園田", 51: "姫路", 54: "高知", 55: "佐賀", 3: "帯広"
                    }
                    venue = place_map.get(place_code, "不明")
                except:
                    pass

            st.metric("開催場", venue)
        with col_r2:
            race_name = df_display['レース名'].iloc[0] if 'レース名' in df_display.columns else "不明"
            st.metric("レース名", race_name if len(str(race_name)) < 20 else str(race_name)[:17] + "...")
        with col_r3:
            course_type = df_display['コースタイプ'].iloc[0] if 'コースタイプ' in df_display.columns else "不明"
            distance = df_display['距離'].iloc[0] if '距離' in df_display.columns else "不明"
            st.metric("コース", f"{course_type} {distance}m")
        with col_r4:
            num_horses = len(df_display)
            st.metric("出走頭数", f"{num_horses}頭")

        # AI予測サマリー
        if 'AI_Score' in df_display.columns and 'Confidence' in df_display.columns:
            avg_confidence = df_display['Confidence'].mean()
            max_ai_score = df_display['AI_Score'].max()
            st.info(f"📊 **AI予測サマリー**: 最高AI勝率 {max_ai_score}% | 平均信頼度 {avg_confidence:.0f}%")

        # コース特性の詳細表示
        venue = df_display['会場'].iloc[0] if '会場' in df_display.columns else None
        if venue:
            try:
                from ml.venue_characteristics import get_venue_characteristics
                venue_char = get_venue_characteristics(venue)

                if venue_char:
                    st.markdown("#### 🏟️ コース特性")

                    col_c1, col_c2, col_c3, col_c4 = st.columns(4)

                    # 直線距離
                    with col_c1:
                        straight = venue_char.get('turf_straight', 0)
                        if straight:
                            straight_label = "長い" if straight > 500 else "短い" if straight < 300 else "標準"
                            st.metric("直線距離", f"{straight}m", delta=straight_label)
                        else:
                            st.metric("直線距離", "不明")

                    # 勾配（傾斜）
                    with col_c2:
                        slope = venue_char.get('slope', 'normal')
                        slope_map = {
                            'steep': '急坂あり',
                            'moderate': '緩やかな坂',
                            'flat': '平坦',
                            'normal': '標準'
                        }
                        slope_label = slope_map.get(slope, slope)
                        slope_icon = "⛰️" if slope == 'steep' else "🏔️" if slope == 'moderate' else "━"
                        st.metric("勾配（傾斜）", slope_label, delta=slope_icon)

                    # コース幅
                    with col_c3:
                        track_width = venue_char.get('track_width', 'standard')
                        width_map = {
                            'narrow': '小回り',
                            'standard': '標準',
                            'wide': '広いコース'
                        }
                        width_label = width_map.get(track_width, track_width)
                        st.metric("コース幅", width_label)

                    # 外枠有利度
                    with col_c4:
                        outer_advantage = venue_char.get('outer_track_advantage', 1.0)
                        if outer_advantage > 1.05:
                            outer_label = "外枠有利"
                            outer_delta = "↑"
                        elif outer_advantage < 0.95:
                            outer_label = "内枠有利"
                            outer_delta = "↓"
                        else:
                            outer_label = "公平"
                            outer_delta = "="
                        st.metric("枠番傾向", outer_label, delta=outer_delta)

                    # 特性の影響説明
                    with st.expander("💡 このコース特性がEV計算に与える影響", expanded=False):
                        st.markdown(f"""
                        #### 🏟️ {venue}の特性

                        **1. 直線距離: {straight}m ({straight_label})**
                        - 長い直線（500m以上）: 人気馬やや不利 (-5%)、穴馬やや有利 (+5%)
                        - 短い直線（300m未満）: 人気馬有利 (+5%)、穴馬不利 (-5%)
                        - 理由: 長い直線は差し馬に有利、短い直線は逃げ・先行馬に有利

                        **2. 勾配（傾斜）: {slope_label}**
                        - 急坂あり: 人気馬（パワーがある馬）が有利 (+2%)
                        - 理由: 坂を登る際に馬力が必要で、実績馬が優位
                        - 該当競馬場: 中山、阪神など

                        **3. コース幅: {width_label}**
                        - 小回り: 人気馬やや有利 (+3%)
                        - 理由: コーナーが多く、器用さが求められる

                        **4. 枠番傾向: {outer_label}**
                        - 外枠有利な場合: 6-8枠の馬の確率を調整 (×{outer_advantage:.2f})
                        - 内枠有利な場合: 1-3枠の馬の確率を調整

                        ⚠️ これらの調整は期待値(EV)計算時に自動的に適用されています。
                        """)
            except Exception as e:
                pass  # venue_characteristics が利用できない場合はスキップ

        # Prepare Editor DF
        # Columns: Horse, Prob, Odds, Mark
        if 'Odds' not in df_display.columns:
             # Try to get scraped odds if available
             if '単勝' in df_display.columns:
                 df_display['Odds'] = pd.to_numeric(df_display['単勝'], errors='coerce').fillna(0.0)
             else:
                 df_display['Odds'] = 0.0
        
        # Select appropriate course compatibility
        # If 'コースタイプ' contains '芝', use turf, else dirt
        # Default to turf if unknown
        is_turf_race = True
        if 'コースタイプ' in df_display.columns:
             # Check first row (all same race)
             c_type = str(df_display['コースタイプ'].iloc[0])
             if 'ダ' in c_type:
                 is_turf_race = False

        if is_turf_race:
             df_display['course_compatibility'] = df_display.get('turf_compatibility', 10.0)
        else:
             df_display['course_compatibility'] = df_display.get('dirt_compatibility', 10.0)

        # === 適性スコアを適性度に変換（10点満点、高い方が良い） ===
        # 元の値は「平均着順」（小さい方が良い）
        # 適性度 = 10 - 平均着順（0-10点、高い方が良い）

        for compat_col in ['jockey_compatibility', 'distance_compatibility', 'course_compatibility']:
            if compat_col in df_display.columns:
                # 10 - 値 で反転（ただし、0-10の範囲に制限）
                df_display[compat_col] = df_display[compat_col].apply(
                    lambda x: max(0, min(10, 10 - x)) if pd.notna(x) else 5.0
                )

        rename_map = {
            'AI_Score': 'AIスコア(%)',
            'Confidence': '信頼度',
            'Odds': '現在オッズ',
            '性齢': '年齢',
            '馬 番': '馬番',
            'jockey_compatibility': '騎手適性度',
            'distance_compatibility': '距離適性度',
            'course_compatibility': 'コース適性度',
            'weighted_avg_speed': '平均スピード'
        }
             
        # Ensure all display columns exist
        defaults = {
            'jockey_compatibility': 10.0,
            'distance_compatibility': 10.0,
            'weighted_avg_speed': 16.0,
            'Confidence': 50
        }
        for c, v in defaults.items():
            if c not in df_display.columns:
                df_display[c] = v

        # Add Mark column BEFORE selecting display columns
        if '予想印' not in df_display.columns:
            df_display['予想印'] = ""

        # Display columns with 予想印 next to 馬名
        display_cols = ['枠', '馬 番', '馬名', '予想印', '性齢', 'AI_Score', 'Confidence', 'Odds', 'jockey_compatibility', 'course_compatibility', 'distance_compatibility']


        edited_df = df_display[display_cols].copy()
        edited_df.rename(columns=rename_map, inplace=True)
        
        st.subheader("📝 予想・オッズ入力")
        
        col_input_1, col_input_2 = st.columns([3, 1])
        with col_input_1:
             st.info("「予想印」や「現在オッズ」を編集すると、リアルタイムで期待値(EV)が計算されます。")
        with col_input_2:
             if st.button("🔄 最新オッズを取得"):
                 with st.spinner("最新オッズを取得中..."):
                     try:
                         current_odds = auto_scraper.scrape_odds_for_race(race_id, mode=mode_val)
                         # Update session state df
                         if current_odds:
                             odds_map = {x['number']: x['odds'] for x in current_odds}
                             
                             target_df = st.session_state[f'data_{race_id}']
                             
                             # Update '単勝' and 'Odds'
                             def update_odds(row):
                                 try:
                                     num = int(row['馬 番'])
                                     return odds_map.get(num, row.get('Odds', 0.0))
                                 except:
                                     return row.get('Odds', 0.0)
                                 
                             target_df['Odds'] = target_df.apply(update_odds, axis=1)
                             target_df['単勝'] = target_df['Odds'] # Sync
                             
                             st.session_state[f'data_{race_id}'] = target_df
                             st.success("オッズを更新しました！")
                             st.rerun()
                         else:
                             st.warning("オッズの取得に失敗したか、データが見つかりませんでした。")
                     except Exception as e:
                         st.error(f"オッズ取得エラー: {e}")

        
        edited_df = st.data_editor(
            edited_df,
            column_config={
                "AIスコア(%)": st.column_config.ProgressColumn(
                    "AI期待度",
                    help="1着（勝利）の AI予測確率",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "信頼度": st.column_config.ProgressColumn(
                    "予測信頼度",
                    help="この予測の信頼性スコア（モデルAUC、データ量、予測確率を考慮）",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "現在オッズ": st.column_config.NumberColumn(
                    "現在オッズ",
                    help="最新の単勝オッズを入力",
                    step=0.1,
                    format="%.1f"
                ),
                "AI期待値": st.column_config.NumberColumn(
                    "AI期待値",
                    help="純粋な期待値（印補正なし）= (AI確率 × オッズ) - 1.0",
                    format="%.2f"
                ),
                "調整後期待値": st.column_config.NumberColumn(
                    "調整後期待値",
                    help="AIの予測にあなたの「印」と「会場特性」を加味した、最終的な『儲かりやすさ』です。ここがプラスの馬を狙おう！",
                    format="%.2f"
                ),
                "推奨度(Kelly)": st.column_config.ProgressColumn(
                    "推奨度(Kelly)",
                    help="ケリー基準による推奨賭け率 (リスクを考慮した推奨度)",
                    format="%.1f%%",
                    min_value=0,
                    max_value=30, # Max display scale (usually >30% is rare)
                ),
                "予想印": st.column_config.SelectboxColumn(
                    "予想印",
                    options=["", "◎", "◯", "▲", "△", "✕"],
                    required=False,
                    help="予想印を入力すると、調整後期待値に反映されます"
                ),
                "騎手適性度": st.column_config.ProgressColumn(
                    "騎手適性度",
                    help="この騎手との相性（10点満点、高いほど良い）",
                    format="%.1f",
                    min_value=0,
                    max_value=10
                ),
                "コース適性度": st.column_config.ProgressColumn(
                    "コース適性度",
                    help="芝/ダート別 相性（10点満点、高いほど良い）",
                    format="%.1f",
                    min_value=0,
                    max_value=10
                ),
                "距離適性度": st.column_config.ProgressColumn(
                    "距離適性度",
                    help="この距離での相性（10点満点、高いほど良い）",
                    format="%.1f",
                    min_value=0,
                    max_value=10
                )
            },
            hide_index=True,
            num_rows="fixed"  
        )
        
        # Calculate EV with JRA/NAR distinction
        # Determine race type from user's mode selection (as primary source)
        race_type = mode_val  # Use user's selected mode (JRA or NAR) as primary source of truth
        venue = ''  # Initialize venue

        # Get venue information if available
        if '会場' in df_display.columns and len(df_display) > 0:
            venue = df_display['会場'].iloc[0]

            # If venue is available, use it to verify/override race_type for accuracy
            if venue:
                try:
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml'))
                    from race_classifier import classify_race_type
                    venue_based_type = classify_race_type(venue)
                    # Use venue-based classification (more accurate than mode selection)
                    race_type = venue_based_type
                except:
                    # Fallback: manual classification
                    jra_venues = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']
                    race_type = 'JRA' if venue in jra_venues else 'NAR'

        # EV calculation with race type AND venue specific parameters
        # Import venue characteristics
        venue_char = None
        try:
            from ml.venue_characteristics import get_venue_characteristics, get_distance_category
            if venue:
                venue_char = get_venue_characteristics(venue)
        except Exception as e:
            # Silently fail if venue characteristics not available
            pass

        # Base parameters by race type
        if race_type == 'JRA':
            # === 中央競馬（JRA）設定 ===
            # 特徴: レベルが高く、予想が堅め。AI予測の信頼性が高い
            mark_weights = {
                "◎": 1.3,   # 本命: 控えめに1.3倍
                "◯": 1.15,  # 対抗: 1.15倍
                "▲": 1.08,  # 単穴: 1.08倍
                "△": 1.03,  # 連下: 1.03倍
                "✕": 0.0,   # 消し: 0倍
                "": 1.0     # 印なし: 1.0倍
            }
            safety_threshold = 0.08  # AI確率8%未満は除外（信頼性重視）
            venue_info = f"🏇 中央競馬（JRA）" + (f" - {venue}" if venue else "")
        else:
            # === 地方競馬（NAR）設定 ===
            # 特徴: 波乱が多く、人気薄が勝ちやすい。大穴狙いも有効
            mark_weights = {
                "◎": 1.8,   # 本命: 積極的に1.8倍
                "◯": 1.4,   # 対抗: 1.4倍
                "▲": 1.2,   # 単穴: 1.2倍
                "△": 1.1,   # 連下: 1.1倍
                "✕": 0.0,   # 消し: 0倍
                "": 1.0     # 印なし: 1.0倍
            }
            safety_threshold = 0.05  # AI確率5%未満は除外（低確率でも狙う価値あり）
            venue_info = f"🌙 地方競馬（NAR）" + (f" - {venue}" if venue else "")

        # Venue-specific adjustments
        venue_features = []
        if venue_char:
            # 直線距離による調整
            straight = venue_char.get('turf_straight', 300)
            if straight and straight > 500:  # 長い直線（新潟など）
                mark_weights["◎"] *= 0.95  # 人気馬やや不利
                mark_weights["△"] *= 1.05  # 穴馬やや有利
                venue_features.append("長直線")
            elif straight and straight < 300:  # 短い直線（中山、函館など）
                mark_weights["◎"] *= 1.05  # 人気馬有利
                mark_weights["△"] *= 0.95  # 穴馬不利
                venue_features.append("短直線")

            # コース幅による調整
            track_width = venue_char.get('track_width')
            if track_width == 'narrow':  # 狭いコース
                mark_weights["◎"] *= 1.03  # 先行有利、人気馬やや有利
                venue_features.append("小回り")
            elif track_width == 'wide':  # 広いコース
                # 馬群が広がりやすく、展開次第
                pass

            # 勾配による調整
            slope = venue_char.get('slope')
            if slope == 'steep':  # 急坂あり（中山など）
                mark_weights["◎"] *= 1.02  # パワーある人気馬有利
                venue_features.append("坂あり")

        if venue_features:
            venue_info += f" ({', '.join(venue_features)})"

        st.info(venue_info)

        # === 確率較正のチェック ===
        is_calibrated = False
        if model_meta and 'training_config' in model_meta:
             is_calibrated = model_meta['training_config'].get('calibrated', False)

        # Uncalibrated NAR Correction (Global application for consistency)
        if race_type == 'NAR' and not is_calibrated:
             # 地方競馬かつ未較正の場合のみ、保守的な調整を行う
             # これにより、表示されるAIスコアとEV計算に使われる確率が一致する
             def adjust_nar_prob_row(row):
                 p = row['AIスコア(%)'] / 100.0
                 new_p = p * 0.9 + 0.05
                 return int(new_p * 100)
             
             edited_df['AIスコア(%)'] = edited_df.apply(adjust_nar_prob_row, axis=1)
             st.caption("ℹ️ NAR調整: AIスコアと期待値を保守的に補正しました（未較正モデルのため）")

        probs = edited_df['AIスコア(%)'] / 100.0
        odds = edited_df['現在オッズ']
        marks = edited_df['予想印']

        # Get run style compatibility if available
        # Get run style compatibility if available
        run_style_compatibility = None
        if 'venue_run_style_compatibility' in edited_df.columns:
            run_style_compatibility = edited_df['venue_run_style_compatibility']

        # Get frame (枠) for venue-specific frame advantage
        frames = None
        if '枠' in edited_df.columns:
            frames = edited_df['枠']

        evs_pure = []      # 純粋EV（印補正なし）
        evs_adjusted = []  # 調整後EV（印補正あり）
        kellys = []

        evs_pure = []      # 純粋EV（印補正なし）
        evs_adjusted = []  # 調整後EV（印補正あり）
        kellys = []
        bias_reasons_list = [] # 補正理由リスト

        for idx, (p, o, m) in enumerate(zip(probs, odds, marks)):
            reasons = [] # この馬の補正理由
            
            # Safety filter (race type specific)
            if p < safety_threshold:
                ev_pure = -1.0
                ev_adj = -1.0
                kelly = 0.0
                reasons.append("確率過低(除外)")
            else:
                w = mark_weights.get(m, 1.0)
                if w != 1.0:
                     reasons.append(f"印{m} (x{w:.2f})")
                
                # Already adjusted in Dataframe if needed
                adjusted_p = p

                # Apply run style compatibility if available
                if run_style_compatibility is not None:
                    run_compat = run_style_compatibility.iloc[idx]
                    if not pd.isna(run_compat) and run_compat != 1.0:
                        # 脚質相性が良い馬は期待値を上げる
                        adjusted_p *= run_compat
                        reasons.append(f"脚質適性 (x{run_compat:.2f})")

                # Apply frame advantage if available
                if frames is not None and venue_char:
                    frame = frames.iloc[idx]
                    if not pd.isna(frame):
                        outer_advantage = venue_char.get('outer_track_advantage', 1.0)
                        try:
                            frame_num = int(frame)
                            if frame_num >= 6 and outer_advantage > 1.0:  # 外枠有利
                                adjusted_p *= outer_advantage
                                reasons.append(f"外枠有利 (x{outer_advantage:.2f})")
                            elif frame_num <= 3 and outer_advantage > 1.0:  # 内枠不利
                                penalty = 2.0 - outer_advantage
                                adjusted_p *= penalty
                                reasons.append(f"内枠不利 (x{penalty:.2f})")
                            
                            # 内枠有利な場合(outer_advantage < 1.0)
                            elif frame_num <= 3 and outer_advantage < 1.0:
                                bonus = 2.0 - outer_advantage
                                adjusted_p *= bonus
                                reasons.append(f"内枠有利 (x{bonus:.2f})")
                            elif frame_num >= 6 and outer_advantage < 1.0:
                                adjusted_p *= outer_advantage
                                reasons.append(f"外枠不利 (x{outer_advantage:.2f})")
                                
                        except: pass

                # 純粋EV: 印補正なし（統計的に正しい）
                ev_pure = (adjusted_p * o) - 1.0

                # 調整後EV: 印補正あり（ユーザーの主観を反映）
                ev_adj = (adjusted_p * w * o) - 1.0

                # Kelly criterion (placeholder for now)
                kelly = 0.0
            
            evs_pure.append(ev_pure)
            evs_adjusted.append(ev_adj)
            kellys.append(kelly)
            bias_reasons_list.append(", ".join(reasons) if reasons else "-")

        edited_df['AI期待値'] = evs_pure
        edited_df['調整後期待値'] = evs_adjusted
        edited_df['推奨度(Kelly)'] = kellys
        edited_df['補正内容'] = bias_reasons_list

        # === AI期待度TOP5のグラフ（デフォルト表示） ===
        st.markdown("---")
        st.subheader("📊 AI期待度 TOP5 分析")

        # TOP5を調整後期待値でソート（印補正を含む）
        top5_df = edited_df.nlargest(5, '調整後期待値')

        # 1. 横棒グラフ: AI確率 vs 期待値
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig_top5 = make_subplots(
            rows=1, cols=2,
            subplot_titles=("AI勝率予測 TOP5", "調整後期待値 TOP5"),
            specs=[[{"type": "bar"}, {"type": "bar"}]]
        )

        # 左: AI勝率
        fig_top5.add_trace(
            go.Bar(
                y=top5_df['馬名'],
                x=top5_df['AIスコア(%)'],
                orientation='h',
                name='AI勝率',
                marker=dict(color='lightblue'),
                text=top5_df['AIスコア(%)'].apply(lambda x: f'{x}%'),
                textposition='auto'
            ),
            row=1, col=1
        )

        # 右: 調整後期待値
        colors = ['green' if ev > 0 else 'red' for ev in top5_df['調整後期待値']]
        fig_top5.add_trace(
            go.Bar(
                y=top5_df['馬名'],
                x=top5_df['調整後期待値'],
                orientation='h',
                name='調整後期待値',
                marker=dict(color=colors),
                text=top5_df['調整後期待値'].apply(lambda x: f'{x:.2f}'),
                textposition='auto'
            ),
            row=1, col=2
        )

        fig_top5.update_xaxes(title_text="AI勝率 (%)", row=1, col=1)
        fig_top5.update_xaxes(title_text="調整後期待値", row=1, col=2)
        fig_top5.update_yaxes(autorange="reversed", row=1, col=1)
        fig_top5.update_yaxes(autorange="reversed", row=1, col=2)
        fig_top5.update_layout(height=400, showlegend=False)

        st.plotly_chart(fig_top5, use_container_width=True)

        # 補正内容の表示
        st.markdown("##### ℹ️ 期待値調整の詳細 (TOP5)")
        st.dataframe(
            top5_df[['予想印', '馬名', '現在オッズ', '調整後期待値', '補正内容']],
            column_config={
                "調整後期待値": st.column_config.NumberColumn(format="%.2f"),
                "推奨度(Kelly)": st.column_config.ProgressColumn(format="%.1f%%", max_value=30),
            },
            hide_index=True,
            use_container_width=True
        )

        # 2. 適性スコア比較（ヒートマップ）
        st.markdown("#### 🎯 TOP5 適性度比較")

        compatibility_cols = ['騎手適性度', 'コース適性度', '距離適性度']
        compat_data = []
        for idx, row in top5_df.iterrows():
            compat_data.append({
                '馬名': row['馬名'],
                '騎手適性度': row.get('騎手適性度', 5.0),
                'コース適性度': row.get('コース適性度', 5.0),
                '距離適性度': row.get('距離適性度', 5.0)
            })

        compat_df = pd.DataFrame(compat_data)

        # ヒートマップ用データ（既に10点満点に変換済み）
        heatmap_data = []
        for col in compatibility_cols:
            heatmap_data.append([val for val in compat_df[col]])

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=compat_df['馬名'],
            y=compatibility_cols,
            colorscale='RdYlGn',
            text=[[f'{val:.1f}' for val in compat_df[col]] for col in compatibility_cols],
            texttemplate='%{text}',
            textfont={"size": 12},
            colorbar=dict(title="適性度<br>(10点満点)")
        ))

        fig_heatmap.update_layout(
            title="適性度（10点満点、高いほど良い）",
            xaxis_title="馬名",
            height=300
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

        # 3. 予測結果の解釈ガイド
        with st.expander("💡 予測結果の見方・解釈ガイド", expanded=False):
            st.markdown("""
            ### 📈 各指標の意味

            **1. AIスコア（AI勝率予測）**
            - AIが予測した1着になる確率（%）
            - **目安**: 10%以上なら有力候補、15%以上なら本命候補
            - ⚠️ 注意: 現在のモデルは古い可能性があります（管理ページで再学習推奨）

            **2. 信頼度（予測信頼度）**
            - この予測の信頼性スコア（20-95%）
            - 以下の要素を考慮:
              - モデルAUC（予測精度）
              - 学習データ量
              - AI予測確率（極端な値ほど信頼度高）
              - 適性スコア（騎手・コース・距離）
            - **目安**: 70%以上なら高信頼、50%以下なら要注意

            **3. 期待値（EV: Expected Value）**

            **AI期待値（純粋EV）:**
            - 統計的に正しい期待値（印補正なし）
            - **計算式**: `(調整後AI確率 × オッズ) - 1.0`
            - 長期的な収益性を評価する客観的指標

            **調整後期待値（印補正あり）:**
            - 予想印を反映した期待値
            - **計算式**: `(調整後AI確率 × 印補正 × オッズ) - 1.0`
            - ユーザーの主観的判断を含む

            **目安**:
              - EV > 0.2 → 強い買い推奨
              - EV > 0.0 → 買い推奨
              - EV < 0.0 → 見送り推奨

            **使い分け**:
              - **AI期待値**: 客観的な判断に使用（統計的に正しい）
              - **調整後期待値**: 印を付けた馬の最終判断に使用

            **4. 適性度（騎手・コース・距離）**
            - 過去のデータから計算した適性度（10点満点）
            - **数値が高いほど良い** (10点=抜群の相性、0点=相性悪い)
            - 7点以上: 抜群の相性
            - 5点以上: 良好
            - 3点以下: やや不安
            - 5点前後: データ不足（標準値）

            **5. コース特性（傾斜・直線距離・コース幅・枠番）**
            - **勾配（傾斜）**: 急坂ありの競馬場では人気馬が有利（+2%）
              - 中山、阪神など: 坂でパワーが必要なため実績馬が優位
            - **直線距離**:
              - 長い直線（500m以上）: 差し馬有利、穴馬チャンス（人気馬-5%、穴馬+5%）
              - 短い直線（300m未満）: 逃げ・先行馬有利、人気馬堅い（人気馬+5%）
            - **コース幅**:
              - 小回りコース: コーナーが多く器用な馬が有利（人気馬+3%）
            - **枠番傾向**:
              - 外枠有利な競馬場: 6-8枠の確率を上方調整
              - 内枠有利な競馬場: 1-3枠の確率を上方調整

            ⚠️ **これらのコース特性は、レース概要セクションで確認できます**

            ### 🎯 推奨される使い方

            1. **TOP5グラフ**でAI期待度の高い馬を確認
            2. **期待値(EV)がプラス**の馬に注目
            3. **信頼度が70%以上**の予測を優先
            4. **適性度**で相性を確認（特に騎手適性度は重要）
            5. **現在オッズ**と**予想印**を入力してEVを最終調整

            ### ⚠️ 重要な注意事項

            - **モデルの再学習が必要**: 現在のモデルは「3着以内」を予測している可能性があります
            - 管理ページで両モデル（JRA/NAR）を再学習してください
            - 再学習後、AI確率は5-15%の範囲（1着確率として妥当）になります
            """)

        st.markdown("---")
        st.subheader("📋 詳細データテーブル")

        # Highlight high EV and Kelly
        def highlight_ev(s):
            is_high = s > 0
            return ['background-color: #d4edda' if v else '' for v in is_high]

        st.dataframe(
            edited_df.style
            .format({
                '推奨度(Kelly)': lambda x: '-' if x <= 0 else f'{x:.1f}%',
                'AI期待値': '{:.2f}',
                '調整後期待値': '{:.2f}'
            })
            .applymap(lambda x: 'background-color: #d4edda' if x > 0 else '', subset=['AI期待値', '調整後期待値', '推奨度(Kelly)'])
        )



        # Visualization
        st.markdown("---")
        st.subheader("🔍 個別馬の詳細分析")

        # ヘルパー関数：馬の詳細分析を生成
        def create_horse_analysis(horse_name, df_display, edited_df):
            """個別馬の能力チャートと過去5走の推移を生成"""
            # Find row
            row = df_display[df_display['馬名'] == horse_name].iloc[0]

            # --- Scoring Logic (Lower rank is better, so Invert) ---
            def rank_to_score(r):
                if pd.isna(r) or r > 18: return 0
                return max(0, min(10, (14 - r) * (10/13)))

            # Calculate scores
            sp_val = row.get('weighted_avg_speed', 16.0)
            score_speed = max(0, min(10, (sp_val - 15.0) * 5))
            j_val = row.get('jockey_compatibility', 10.0)
            score_jockey = rank_to_score(j_val)
            c_val = row.get('course_compatibility', 10.0)
            score_course = rank_to_score(c_val)
            d_val = row.get('distance_compatibility', 10.0)
            score_dist = rank_to_score(d_val)
            rank_val = row.get('weighted_avg_rank', 10.0)
            score_form = rank_to_score(rank_val)

            # Radar Chart
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=[score_speed, score_form, score_jockey, score_course, score_dist, score_speed],
                theta=['スピード', '実績(着順)', '騎手相性', 'コース適性', '距離適性'],
                fill='toself',
                name=horse_name,
                line=dict(color='#1f77b4')
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                height=300,
                margin=dict(l=40, r=40, t=40, b=40)
            )

            # Past 5 Runs Line Chart
            history_data = []
            for i in range(5, 0, -1):
                if f"past_{i}_rank" in row and pd.notna(row[f"past_{i}_rank"]):
                    history_data.append({
                        "Run": f"{i}走前",
                        "着順": row[f"past_{i}_rank"],
                        "3Fタイム": row[f"past_{i}_last_3f"]
                    })

            if history_data:
                hist_df = pd.DataFrame(history_data)
                from plotly.subplots import make_subplots
                fig_line = make_subplots(specs=[[{"secondary_y": True}]])
                fig_line.add_trace(go.Scatter(x=hist_df['Run'], y=hist_df['着順'], name="着順", mode='lines+markers', line=dict(color='#ff7f0e')), secondary_y=False)
                fig_line.add_trace(go.Scatter(x=hist_df['Run'], y=hist_df['3Fタイム'], name="上り3F", mode='lines+markers', line=dict(dash='dot', color='#2ca02c')), secondary_y=True)
                fig_line.update_layout(height=300, margin=dict(l=40, r=40, t=40, b=40))
                fig_line.update_yaxes(title_text="着順", autorange="reversed", secondary_y=False)
                fig_line.update_yaxes(title_text="上り3F (秒)", secondary_y=True)
            else:
                fig_line = go.Figure()
                fig_line.add_annotation(text="過去データなし")
                fig_line.update_layout(height=300)

            # Get prediction summary
            pred_row = edited_df[edited_df['馬名'] == horse_name].iloc[0]

            return fig_radar, fig_line, pred_row

        try:
            # === 分析対象の馬を選択 ===
            st.info("💡 分析対象の馬を選択してください（デフォルトはAI期待度上位5頭）")

            # Get all horses sorted by AI Score
            all_horses = edited_df.sort_values('AIスコア(%)', ascending=False)['馬名'].tolist()
            default_horses = top5_df['馬名'].tolist()
            
            # Ensure default horses are in the options (sanity check)
            default_horses = [h for h in default_horses if h in all_horses]

            selected_horses = st.multiselect(
                "分析対象の馬を選択",
                options=all_horses,
                default=default_horses
            )

            for idx, horse_name in enumerate(selected_horses):
                with st.expander(f"**{idx+1}位: {horse_name}**", expanded=(idx < 2)):  # 1-2位は展開表示
                    fig_radar, fig_line, pred_row = create_horse_analysis(horse_name, df_display, edited_df)

                    # Prediction Summary
                    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
                    with col_s1:
                        st.metric("AI勝率", f"{pred_row['AIスコア(%)']}%")
                    with col_s2:
                        st.metric("信頼度", f"{pred_row['信頼度']}%")
                    with col_s3:
                        ai_ev_val = pred_row['AI期待値']
                        st.metric("AI期待値", f"{ai_ev_val:.2f}")
                    with col_s4:
                        adj_ev_val = pred_row['調整後期待値']
                        ev_delta = "買い推奨" if adj_ev_val > 0 else "見送り"
                        st.metric("調整後EV", f"{adj_ev_val:.2f}", delta=ev_delta)
                    with col_s5:
                        odds_val = pred_row.get('現在オッズ', 0.0)
                        st.metric("オッズ", f"{odds_val:.1f}倍")

                    # Charts
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.markdown("**能力チャート**")
                        st.plotly_chart(fig_radar, use_container_width=True)
                    with col_c2:
                        st.markdown("**過去5走の推移**")
                        st.plotly_chart(fig_line, use_container_width=True)

            # === おすすめの買い方提案 ===
            st.markdown("---")
            st.subheader("🎫 AIおすすめの買い方")
            
            # Budget Input
            budget = st.number_input("💰 予算 (円)", min_value=100, step=100, value=1000, help="この予算に合わせて購入金額を配分します")

            # Logic for betting recommendations using 'edited_df' (which includes updated Odds/Marks)
            sorted_df = edited_df.sort_values('調整後期待値', ascending=False)
            top1 = sorted_df.iloc[0]
            top2 = sorted_df.iloc[1] if len(sorted_df) > 1 else None
            top3 = sorted_df.iloc[2] if len(sorted_df) > 2 else None
            
            # Helper for circled numbers
            def to_circled_num(n):
                try:
                    n = int(n)
                    if 1 <= n <= 20:
                        return chr(9311 + n)
                    return f"({n})"
                except:
                    return ""

            # Helper to format horse name with circle num
            def fmt_horse(row):
                num = row.get('馬 番', '')
                name = row['馬名']
                c_num = to_circled_num(num)
                return f"{c_num} {name}".strip()

            # Cards Layout
            col_bet1, col_bet2, col_bet3 = st.columns(3)

            # 1. 🎯 Tankei (Tansho/Fukusho)
            with col_bet1:
                st.markdown("#### 🎯 単系 (WIN/PLACE)")
                if top1['AIスコア(%)'] >= 10 and top1['信頼度'] >= 60 and top1['調整後期待値'] > 0:
                    bet_type = "単勝 (WIN)" if top1['AIスコア(%)'] >= 20 else "複勝 (PLACE)"
                    
                    # Allocation: 50% of budget for Tankei focus
                    amount = int((budget * 0.5) / 100) * 100
                    if amount < 100: amount = 100
                    
                    st.success(f"**{bet_type}**")
                    st.metric(fmt_horse(top1), f"{amount}円", delta=f"EV: {top1['調整後期待値']:.2f}")
                    st.caption(f"信頼度: {top1['信頼度']}%")
                else:
                    st.info("条件に合う軸馬がいません")
                    st.caption("見送り (No Bet)")

            # 2. 🔄 Renkei (Umaren/Wide)
            with col_bet2:
                st.markdown("#### 🔄 連系 (EXACTA/WIDE)")
                if top1['AIスコア(%)'] >= 30:
                    # Solid Favorite -> Nagashi
                    st.success("**馬連・ワイド 流し**")
                    targets = []
                    if top2 is not None: targets.append(fmt_horse(top2))
                    if top3 is not None: targets.append(fmt_horse(top3))
                    
                    # Allocation: Budget / points
                    points = len(targets)
                    if points > 0:
                        amount_per_point = int((budget / points) / 100) * 100 
                        if amount_per_point < 100: amount_per_point = 100
                        st.write(f"軸: **{fmt_horse(top1)}**")
                        st.write(f"紐: {', '.join(targets)}")
                        st.metric("1点あたり", f"{amount_per_point}円", help=f"合計 {(amount_per_point * points)}円")
                    else:
                        st.write("相手馬不足")
                elif top1['AIスコア(%)'] < 20:
                     # Confused -> Box
                     st.warning("**馬連・ワイド BOX**")
                     box_horses = [fmt_horse(row) for i, row in sorted_df.head(5).iterrows()][:4] # Top 4 box = 6 points
                     
                     points = 6 # 4C2
                     amount_per_point = int((budget / points) / 100) * 100
                     if amount_per_point < 100: amount_per_point = 100
                     
                     st.write(f"推奨: {', '.join(box_horses)}")
                     st.caption("混戦模様です")
                     st.metric("1点あたり", f"{amount_per_point}円", help=f"4頭BOX (6点): {amount_per_point * 6}円")
                else:
                     st.info("**馬連 フォーメーション**")
                     st.caption("適宜調整してください")
                     st.write(f"1列目: {fmt_horse(top1)}")
                     targets = []
                     if top2 is not None: targets.append(fmt_horse(top2))
                     if top3 is not None: targets.append(fmt_horse(top3))
                     st.write(f"2列目: {', '.join(targets)}")

            # 3. 🧨 Aname (Longshot)
            with col_bet3:
                st.markdown("#### 🧨 穴目 (LONGSHOT)")
                # Find high EV but low probability (Score < 15%)
                longshots = sorted_df[
                    (sorted_df['AIスコア(%)'] < 15) & 
                    (sorted_df['調整後期待値'] > 0.3) &
                    (sorted_df['信頼度'] >= 40)
                ]
                
                if not longshots.empty:
                    ls_horse = longshots.iloc[0]
                    st.error(f"**狙い目: {fmt_horse(ls_horse)}**")
                    st.metric("期待値", f"{ls_horse['調整後期待値']:.2f}", delta="High EV")
                    st.write(f"単オッズ: {ls_horse.get('現在オッズ', 0)}倍")
                    st.caption("ワイド・複勝の紐に推奨")
                else:
                    st.info("推奨できる穴馬なし")
                    st.caption("堅い決着の可能性大")
                    
        except Exception as e:
            st.warning(f"可視化エラー: {e}")
            import traceback
            st.text(traceback.format_exc())
