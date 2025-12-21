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
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml'))

try:
    import auto_scraper
    from feature_engineering import process_data
except ImportError as e:
    st.error(f"Import Error: {e}")

st.set_page_config(page_title="AI Keiba Predictor", layout="wide")

# --- Utils ---
@st.cache_resource
def load_model(mode="JRA"):
    model_path = os.path.join(os.path.dirname(__file__), f"ml/models/lgbm_model_nar.pkl" if mode == "NAR" else "ml/models/lgbm_model.pkl")
    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    return None

def load_schedule_data(mode="JRA"):
    json_path = os.path.join(os.path.dirname(__file__), "todays_data_nar.json" if mode == "NAR" else "todays_data.json")
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
    このシステムは**LightGBM**という機械学習モデルを使用し、過去の膨大なレースデータから「3着以内に入る確率」を算出しています。
    
    #### 使用しているデータ
    - **基本情報**: 枠番、馬番、馬齢、斤量、騎手
    - **過去5走の成績**: 着順、走破タイム、上り3F、通過順（脚質）、馬体重、馬場状態、**天気**、**最終オッズ**
    - **直近重視**: 過去のレースは直近のものほど重要視する「時間減衰」処理を行っています。
    
    #### 期待値 (EV) の計算式
    単に勝つ確率が高い馬を選ぶのではなく、「オッズに対して期待値が高い馬」を見つける設計です。
    $$
    Expected Value = (AI勝率 \\times 予想家の印補正 \\times 現在オッズ) - 1.0
    $$
    - **プラス (緑色)**: 長期的に買ってプラスになる可能性が高い馬
    - **予想家の印**: あなたの直感（印）を入力することで、AIの確率を補正できます

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

# --- Race Selection ---
st.subheader("📍 レース選択")

schedule_data = load_schedule_data(mode=mode_val)
race_id = None

if schedule_data and "races" in schedule_data:
    races = schedule_data['races']
    
    # 1. Filter by Date
    dates = sorted(list(set([r.get('date', 'Unknown') for r in races])))
    
    # Layout columns for selection
    col_date, col_venue, col_race = st.columns(3)
    
    with col_date:
         selected_date = st.selectbox("1. 日付を選択", dates)
    
    # Filter races by date
    todays_races = [r for r in races if r.get('date') == selected_date]
    
    if todays_races:
        # 2. Filter by Venue (New)
        venues = sorted(list(set([r['venue'] for r in todays_races])))
        
        with col_venue:
            selected_venue = st.selectbox("2. 開催地を選択", venues)
            
        # Filter races by venue
        venue_races = [r for r in todays_races if r['venue'] == selected_venue]
        
        # 3. Select Race
        # Sort by race number just in case
        venue_races.sort(key=lambda x: int(x['number']))
        
        race_options = {f"{r['number']}R: {r['name']}": r['id'] for r in venue_races}
        
        with col_race:
            selected_label = st.selectbox("3. レースを選択", list(race_options.keys()))
            if selected_label:
                race_id = race_options[selected_label]
    else:
        st.warning(f"{selected_date} のレースはありません。")
        
else:
    st.warning("レースデータがありません。管理者メニューから更新ボタンを押してください。")
    race_id = st.text_input("レースID直接入力 (12桁)", value="202305021211")


# Main Analysis
if race_id:
    st.header(f"レース分析: {race_id}")
    
    # Load Model
    model = load_model(mode=mode_val)

    button_analyze = st.button("🚀 このレースを分析する (データ取得・AI予測)")
    
    if button_analyze:
        if not race_id:
             st.error("レースIDが選択されていません。")
        elif not model:
             st.error(f"モデル ({mode_val}) が読み込めませんでした。管理画面で学習を実行するか、モデルファイルを確認してください。")
        else:
            with st.spinner("出馬表を取得し、AI予測を実行中..."):
                # Scrape Shutuba
                df = auto_scraper.scrape_shutuba_data(race_id, mode=mode_val)
            
            if df is not None and not df.empty:
                # 2. FE (use_venue_features=False to match existing model trained with 27 features)
                X_df = process_data(df, use_venue_features=False)
                
                # 3. Predict
                if model:
                    try:
                        # Drop meta cols for prediction
                        # Meta cols are handled in process_data, but result has meta + features + rank
                        # We need to filter only numeric features matching model
                        # Model expects features used in training.
                        # Features: weighted_avg_... + age
                        # We should robustly select.
                        
                        # Identify feature cols from X_df
                        # Robustly select features matching the model
                        try:
                            model_features = model.feature_name()
                            # Ensure all model features exist in X_df
                            for f in model_features:
                                if f not in X_df.columns:
                                    X_df[f] = 0.0
                            
                            X_pred = X_df[model_features].fillna(0.0)
                            
                            probs = model.predict(X_pred)
                            
                            df['AI_Prob'] = probs
                            df['AI_Score'] = (probs * 100).astype(int)
                        except Exception as e:
                            st.error(f"Prediction Error (Feature Mismatch): {e}")
                            st.write(f"Model expects: {model.feature_name()}")
                            st.write(f"Data has: {list(X_df.columns)}")
                            raise e
                        
                        # Merge features back to df for display
                        # We need: turf_compatibility, dirt_compatibility, jockey_compatibility, distance_compatibility, weighted_avg_speed, weighted_avg_rank
                        cols_to_merge = [
                            'turf_compatibility', 'dirt_compatibility', 
                            'jockey_compatibility', 'distance_compatibility', 
                            'weighted_avg_speed', 'weighted_avg_rank'
                        ]
                        for c in cols_to_merge:
                            if c in X_df.columns:
                                df[c] = X_df[c]

                        
                    except Exception as e:
                        st.error(f"Prediction Error: {e}")
                        df['AI_Prob'] = 0.0
                        df['AI_Score'] = 0.0
                else:
                    st.warning("モデルが見つかりません。予測スキップ。")
                    df['AI_Prob'] = 0.0
                    df['AI_Score'] = 0.0

                # 4. Display
                # Store in session state to persist edits
                st.session_state[f'data_{race_id}'] = df
            else:
                st.error("データの取得に失敗しました。")

    # Show Data if available
    if f'data_{race_id}' in st.session_state:
        df_display = st.session_state[f'data_{race_id}'].copy()
        
        # Prepare Editor DF
        # Columns: Horse, Prob, Odds, Mark
        if 'Odds' not in df_display.columns:
             # Try to get scraped odds if available
             if '単勝' in df_display.columns:
                 df_display['Odds'] = pd.to_numeric(df_display['単勝'], errors='coerce').fillna(0.0)
             else:
                 df_display['Odds'] = 0.0
        
        rename_map = {
            'AI_Score': 'AIスコア(%)',
            'Odds': '現在オッズ',
            '性齢': '年齢',
            '馬 番': '馬番',
            'jockey_compatibility': '騎手相性',
            'distance_compatibility': '距離適性',
            'course_compatibility': 'コース適性',
            'weighted_avg_speed': '平均スピード'
        }
        
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
             
        # Ensure all display columns exist
        defaults = {
            'jockey_compatibility': 10.0,
            'distance_compatibility': 10.0,
            'weighted_avg_speed': 16.0
        }
        for c, v in defaults.items():
            if c not in df_display.columns:
                df_display[c] = v


        display_cols = ['枠', '馬 番', '馬名', '性齢', 'AI_Score', 'Odds', 'jockey_compatibility', 'course_compatibility', 'distance_compatibility']

        
        edited_df = df_display[display_cols].copy()
        edited_df.rename(columns=rename_map, inplace=True)
        
        # Add Mark column
        edited_df['予想印'] = ""
        
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
                    help="3着以内に入るAI予測確率",
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
                ),
                "騎手相性": st.column_config.NumberColumn(
                    "騎手相性",
                    help="この騎手での平均着順 (小さいほど良い)",
                    format="%.1f"
                ),
                "コース適性": st.column_config.NumberColumn(
                    "コース適性",
                    help="芝/ダート別 平均着順 (小さいほど良い)",
                    format="%.1f"
                ),
                "距離適性": st.column_config.NumberColumn(
                    "距離適性",
                    help="同距離での平均着順 (小さいほど良い)",
                    format="%.1f"
                )
            },
            hide_index=True,
            num_rows="fixed"  
        )
        
        # Calculate EV with JRA/NAR distinction
        # Determine race type from venue
        race_type = 'JRA'  # Default
        venue = ''  # Initialize venue

        if '会場' in df_display.columns and len(df_display) > 0:
            venue = df_display['会場'].iloc[0]

            # Import race classifier
            try:
                import sys
                import os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ml'))
                from race_classifier import classify_race_type
                race_type = classify_race_type(venue)
            except:
                # Fallback
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
            # 中央競馬: 信頼性が高いので印の影響を抑える
            mark_weights = {"◎": 1.3, "◯": 1.15, "▲": 1.08, "△": 1.03, "✕": 0.0, "": 1.0}
            safety_threshold = 0.08  # 8%
            venue_info = f"🏇 中央競馬（JRA）" + (f" - {venue}" if venue else "")
        else:
            # 地方競馬: 波乱が多いので印の重みを大きく
            mark_weights = {"◎": 1.8, "◯": 1.4, "▲": 1.2, "△": 1.1, "✕": 0.0, "": 1.0}
            safety_threshold = 0.05  # 5%（地方は低確率でも狙う価値あり）
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

        probs = edited_df['AIスコア(%)'] / 100.0
        odds = edited_df['現在オッズ']
        marks = edited_df['予想印']

        # Get run style compatibility if available
        run_style_compatibility = None
        if 'venue_run_style_compatibility' in edited_df.columns:
            run_style_compatibility = edited_df['venue_run_style_compatibility']

        # Get frame (枠) for venue-specific frame advantage
        frames = None
        if '枠' in edited_df.columns:
            frames = edited_df['枠']

        evs = []
        kellys = []

        for idx, (p, o, m) in enumerate(zip(probs, odds, marks)):
            # Safety filter (race type specific)
            if p < safety_threshold:
                ev = -1.0
                kelly = 0.0
            else:
                w = mark_weights.get(m, 1.0)

                # Adjust probability for NAR (higher uncertainty)
                if race_type == 'NAR':
                    # 地方は予測の不確実性を考慮
                    # 高い確率は少し下げ、低い確率は少し上げる
                    adjusted_p = p * 0.9 + 0.05
                else:
                    adjusted_p = p

                # Apply run style compatibility if available
                if run_style_compatibility is not None:
                    run_compat = run_style_compatibility.iloc[idx]
                    if not pd.isna(run_compat):
                        # 脚質相性が良い馬は期待値を上げる
                        adjusted_p *= run_compat

                # Apply frame advantage if available
                if frames is not None:
                    try:
                        frame = int(frames.iloc[idx])
                         
                        # Default Venue Char adjustments
                        if venue_char:
                            outer_advantage = venue_char.get('outer_track_advantage', 1.0)
                            if frame >= 6:  # 外枠
                                adjusted_p *= outer_advantage
                            elif frame <= 3:  # 内枠
                                adjusted_p *= (2.0 - outer_advantage)
                        
                        # Tipster Logic: Mizusawa Specific
                        # 水沢は「小回り」「先行有利」「内枠有利（特に1300/1400m）」
                        if '水沢' in venue_info:
                             # 内枠 (1-3) 有利
                             if frame <= 3:
                                 adjusted_p *= 1.15 # 内枠ボーナス
                             # 外枠 (7-8) 割引
                             elif frame >= 7:
                                 adjusted_p *= 0.95
                        
                        # Tipster Logic: Kanazawa Specific
                        # 金沢は「1500mは外枠も自在」「1400mは内枠先行有利」
                        if '金沢' in venue_info:
                            # 距離判定
                            is_1400 = False
                            if '距離' in edited_df.columns:
                                try:
                                    d_val = int(str(edited_df['距離'].iloc[idx]).replace('m',''))
                                    if d_val == 1400: is_1400 = True
                                except: pass
                            
                            if is_1400:
                                # 1400m: 内枠（1-3枠）先行有利（基本セオリー）
                                if frame <= 3:
                                    adjusted_p *= 1.10
                                elif frame >= 7:
                                    adjusted_p *= 0.95
                                    
                                # 距離適性一致（1400m得意）の馬（AIスコア高評価馬）へのボーナス
                                if p > 0.25:
                                    adjusted_p *= 1.05
                            else:
                                # 1500m他: 外枠(5-8)も割引せず、むしろ自在性でプラス評価（特に人気馬）
                                if frame >= 5:
                                    adjusted_p *= 1.05 # 外枠の自在性を評価
                            
                            # 1. 逃げ・先行（脚質1-2）を大幅プラス（全距離共通）
                            pass

                        # Tipster Logic: Kawasaki Specific
                        # 川崎1500mは「コーナー4回の独特なコース」「内枠（特に1-2枠）が圧倒的有利」「外枠は距離ロス大」
                        if '川崎' in venue_info:
                            # 1. 内枠（1-2枠）は「聖域」級の有利
                            if frame <= 2:
                                adjusted_p *= 1.20 # 強力な内枠ボーナス
                            
                            # 2. 外枠（7-8枠）はコーナーきつく距離ロス大
                            elif frame >= 7:
                                adjusted_p *= 0.90 # 厳しめの割引
                            
                            # 3. 騎手の腕（コーナー巧者）
                            # jockey_compatibilityが高い場合、少しボーナス
                            if 'jockey_compatibility' in edited_df.columns:
                                j_compat = edited_df['jockey_compatibility'].iloc[idx]
                                if j_compat <= 5.0 and j_compat > 0: # 1に近いほど好成績（平均着順）
                                     adjusted_p *= 1.05

                        # Tipster Logic: Sonoda Specific
                        # 園田は「1230mは外枠有利（スムーズに先行）」
                        if '園田' in venue_info:
                             # 1230m戦かどうかの判定（距離列があれば）
                             is_1230 = False
                             if '距離' in edited_df.columns:
                                 try:
                                     d_val = int(str(edited_df['距離'].iloc[idx]).replace('m',''))
                                     if d_val == 1230: is_1230 = True
                                 except: pass
                             
                             if is_1230:
                                 # 外枠（6-8枠）有利
                                 if frame >= 6:
                                     adjusted_p *= 1.10
                             else:
                                 # 園田1400m他: 「内枠の先行馬は被せられるリスクあり」「外枠（特に8枠）が好成績」
                                 if frame >= 7:
                                     adjusted_p *= 1.05 # 外枠ボーナス
                                 elif frame <= 2:
                                     adjusted_p *= 0.95 # 内枠の被されリスク割引
                                 
                                 # スピード絶対主義（持ち時計）
                                 if p > 0.3: # AIが高評価している場合（＝能力上位）
                                     adjusted_p *= 1.05 # さらに後押し
                        
                        # Tipster Logic: Kasamatsu Specific
                        # 笠松1400m/1600mは「逃げ・先行圧倒的有利」「内枠の逃げ残りが強い」
                        if '笠松' in venue_info:
                             # 1600mも1コーナーまで200mと短く、内枠先行が絶対有利
                             
                             # 2. 内枠（1-3枠）有利（特に逃げ馬）
                             if frame <= 3:
                                 adjusted_p *= 1.15
                             # 外枠は割引（被されるリスク大）
                             elif frame >= 7:
                                 adjusted_p *= 0.95
                                 
                             # 3. 先行力（持ち時計換算）
                             # 1600m換算などでトップの馬（AI高評価馬）をさらに後押し
                             if p > 0.25:
                                 adjusted_p *= 1.05

                    except: pass

                # Market Confidence Fallback (Missing Data Safeguard)
                # オッズ1.0~2.0倍の圧倒的人気馬に対し、AIが極端に低い評価（20%未満）を下している場合、
                # データ欠落の可能性が高いため、市場評価（オッズ）を一部信頼して補正する。
                if o > 1.0 and o <= 2.5:
                     implied_prob = 0.8 / o # 控除率考慮
                     if adjusted_p < (implied_prob * 0.4): # AIが市場の4割以下しか評価していない場合
                         adjusted_p = max(adjusted_p, implied_prob * 0.4) # 最低でも市場評価の4割は持たせる

                ev = (adjusted_p * m * o) - 1.0
                
                # Kelly Criterion
                # f = (p(b+1) - 1) / b  => (p*o - 1) / (o - 1)
                # p = adjusted_p * mark_bias
                p_final = adjusted_p * m
                
                if o > 1.0 and p_final > 0:
                    k = ((p_final * o) - 1.0) / (o - 1.0)
                    kelly = max(0.0, k * 100) # Convert to %
                    
                    # Cap Kelly at reasonable amounts (e.g. 50%) to prevent reckless betting
                    kelly = min(kelly, 50.0)
                else:
                    kelly = 0.0
            
            evs.append(ev)
            kellys.append(kelly)

        edited_df['期待値(EV)'] = evs
        edited_df['推奨度(Kelly)'] = kellys

        
        # Highlight high EV
        def highlight_ev(s):
            is_high = s > 0
            return ['background-color: #d4edda' if v else '' for v in is_high]
        
        # Highlight high EV and Kelly
        def highlight_ev(s):
            is_high = s > 0
            return ['background-color: #d4edda' if v else '' for v in is_high]
        
        st.dataframe(
            edited_df.style
            .format({'推奨度(Kelly)': lambda x: '-' if x <= 0 else f'{x:.1f}%', '期待値(EV)': '{:.2f}'})
            .applymap(lambda x: 'background-color: #d4edda' if x > 0 else '', subset=['期待値(EV)', '推奨度(Kelly)'])
        )

        
        # Visualization
        st.subheader("📊 詳細分析")
        
        try:
            # 1. Select a horse for detailed analysis
            horse_options = df_display['馬名'].tolist()
            selected_horse_name = st.selectbox("詳細を見る馬を選択", horse_options)
            
            # Find row
            row = df_display[df_display['馬名'] == selected_horse_name].iloc[0]
            
            # 2. Radar Chart (5 Axes)
            # Speed (Real), Stamina/Form (Rank), Jockey, Course, Distance
            
            # --- Scoring Logic (Lower rank is better, so Invert) ---
            # Rank 1 -> Score 10, Rank 10 -> Score 1, Rank 18 -> 0
            def rank_to_score(r):
                if pd.isna(r) or r > 18: return 0
                return max(0, min(10, (14 - r) * (10/13))) # Approx 1->10, 14->0

            # Speed: 16.0 is baseline. >17 is fast? <15 slow?
            # 1000m/60s = 16.6. 
            sp_val = row.get('weighted_avg_speed', 16.0)
            score_speed = max(0, min(10, (sp_val - 15.0) * 5)) # 17.0->10, 15.0->0

            j_val = row.get('jockey_compatibility', 10.0)
            score_jockey = rank_to_score(j_val)
            
            c_val = row.get('course_compatibility', 10.0) # Calculated above but only in display_df... wait, we are accessing df_display row.
            # We added 'course_compatibility' to df_display in UI section.
            # Re-calculate here if needed OR ensure row comes from df_display.
            # row comes from df_display!
            score_course = rank_to_score(c_val)
            
            d_val = row.get('distance_compatibility', 10.0)
            score_dist = rank_to_score(d_val)
            
            rank_val = row.get('weighted_avg_rank', 10.0)
            score_form = rank_to_score(rank_val)

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=[score_speed, score_form, score_jockey, score_course, score_dist, score_speed],
                theta=['スピード', '実績(着順)', '騎手相性', 'コース適性', '距離適性'],
                fill='toself',
                name=selected_horse_name
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 10])), 
                title=f"能力チャート: {selected_horse_name}"
            )
            
            # 3. Multi-Axis Line Chart (Past 5 Runs)
            history_data = []
            for i in range(5, 0, -1): # Chronological 5->1 (Oldest to Newest)
                if f"past_{i}_rank" in row and pd.notna(row[f"past_{i}_rank"]):
                     history_data.append({
                         "Run": f"{i}走前",
                         "着順": row[f"past_{i}_rank"],
                         "3Fタイム": row[f"past_{i}_last_3f"],
                         "馬体重": row[f"past_{i}_horse_weight"]
                     })
            
            if history_data:
                hist_df = pd.DataFrame(history_data)
                
                # Plotly with Secondary Y
                from plotly.subplots import make_subplots
                fig_line = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Rank (Left Y, Inverted)
                fig_line.add_trace(go.Scatter(x=hist_df['Run'], y=hist_df['着順'], name="着順", mode='lines+markers'), secondary_y=False)
                
                # 3F (Right Y)
                fig_line.add_trace(go.Scatter(x=hist_df['Run'], y=hist_df['3Fタイム'], name="上り3F", mode='lines+markers', line=dict(dash='dot')), secondary_y=True)
                
                fig_line.update_layout(title="過去5走の推移 (着順 vs 3Fタイム)")
                fig_line.update_yaxes(title_text="着順 (低い方が良い)", autorange="reversed", secondary_y=False)
                fig_line.update_yaxes(title_text="上り3Fタイム (秒)", secondary_y=True)
                
            else:
                fig_line = go.Figure()
                fig_line.add_annotation(text="詳細な過去データがありません")

            col_viz1, col_viz2 = st.columns(2)
            col_viz1.plotly_chart(fig_radar, use_container_width=True)
            col_viz2.plotly_chart(fig_line, use_container_width=True)
            
        except Exception as e:
            st.warning(f"可視化エラー: {e}")
            import traceback
            st.text(traceback.format_exc())
