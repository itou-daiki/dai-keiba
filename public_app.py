import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import pickle
import json
import plotly.express as px
import plotly.graph_objects as go

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
def load_model():
    model_path = os.path.join(os.path.dirname(__file__), 'ml/models/lgbm_model.pkl')
    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    return None

def load_schedule_data():
    path = os.path.join(os.path.dirname(__file__), 'todays_data.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
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

# Sidebar
st.sidebar.header("🕹️ コントロールパネル")

if st.sidebar.button("📅 レース一覧を更新 (今後1週間)"):
    with st.spinner("最新のレース情報を取得中 (約1分)..."):
        success, msg = auto_scraper.scrape_todays_schedule()
        if success:
            st.sidebar.success(msg)
            st.rerun()
        else:
            st.sidebar.error(f"エラー: {msg}")

if st.sidebar.button("🧠 最新モデルを再読み込み"):
    load_model.clear()
    st.cache_resource.clear()
    st.success("モデルを再読み込みしました！")


schedule_data = load_schedule_data()
race_id = None

if schedule_data and "races" in schedule_data:
    races = schedule_data['races']
    
    # 1. Filter by Date
    # Extract available dates
    # races have "date" field "YYYY-MM-DD"
    dates = sorted(list(set([r.get('date', 'Unknown') for r in races])))
    
    selected_date = st.sidebar.selectbox("日付を選択", dates)
    
    # Filter races
    todays_races = [r for r in races if r.get('date') == selected_date]
    
    if todays_races:
        race_options = {f"{r['venue']}{r['number']}R: {r['name']}": r['id'] for r in todays_races}
        selected_label = st.sidebar.selectbox("レースを選択", list(race_options.keys()))
        if selected_label:
            race_id = race_options[selected_label]
    else:
        st.sidebar.warning(f"{selected_date} のレースはありません。")
        
else:
    st.sidebar.warning("レースデータがありません。更新ボタンを押してください。")
    race_id = st.sidebar.text_input("レースID直接入力 (12桁)", value="202305021211")

# Main Analysis
if race_id:
    st.header(f"レース分析: {race_id}")
    
    if st.button("🚀 このレースを分析する (データ取得・AI予測)"):
        with st.spinner("出馬表と過去データを取得中 (20〜30秒かかります)..."):
            # 1. Scrape
            df = auto_scraper.scrape_shutuba_data(race_id)
            
            if df is not None and not df.empty:
                # 2. FE
                X_df = process_data(df)
                
                # 3. Predict
                model = load_model()
                if model:
                    try:
                        # Drop meta cols for prediction
                        # Meta cols are handled in process_data, but result has meta + features + rank
                        # We need to filter only numeric features matching model
                        # Model expects features used in training.
                        # Features: weighted_avg_... + age
                        # We should robustly select.
                        
                        # Identify feature cols from X_df
                        # Exclude non-numeric and 'rank'
                        meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
                        features = [c for c in X_df.columns if c not in meta_cols and c != 'target_top3']
                        # Ensure numeric
                        X_pred = X_df[features].select_dtypes(include=['number']).fillna(0)
                        
                        probs = model.predict(X_pred)
                        
                        df['AI_Prob'] = probs
                        df['AI_Score'] = (probs * 100).astype(int)
                        
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
        
        display_cols = ['枠', '馬 番', '馬名', '性齢', 'AI_Score', 'Odds']
        # Map nice names
        rename_map = {
            'AI_Score': 'AIスコア(%)',
            'Odds': '現在オッズ',
            '性齢': '年齢',
            '馬 番': '馬番'
        }
        
        edited_df = df_display[display_cols].copy()
        edited_df.rename(columns=rename_map, inplace=True)
        
        # Add Mark column
        edited_df['予想印'] = ""
        
        st.subheader("📝 予想・オッズ入力")
        st.info("「予想印」や「現在オッズ」を編集すると、リアルタイムで期待値(EV)が計算されます。")
        
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
                "予想印": st.column_config.SelectboxColumn(
                    "予想印",
                    options=["", "◎", "◯", "▲", "△", "✕"],
                    required=False,
                )
            },
            hide_index=True,
            num_rows="fixed"  
        )
        
        # Calculate EV with JRA/NAR distinction
        # Determine race type from venue
        race_type = 'JRA'  # Default

        if '会場' in df_display.columns and len(df_display) > 0:
            venue = df_display['会場'].iloc[0] if '会場' in df_display.columns else ''

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

        # EV calculation with race type specific parameters
        if race_type == 'JRA':
            # 中央競馬: 信頼性が高いので印の影響を抑える
            mark_weights = {"◎": 1.3, "◯": 1.15, "▲": 1.08, "△": 1.03, "✕": 0.0, "": 1.0}
            safety_threshold = 0.08  # 8%
            st.info(f"🏇 中央競馬（JRA）モード - より堅実な期待値計算")
        else:
            # 地方競馬: 波乱が多いので印の重みを大きく
            mark_weights = {"◎": 1.8, "◯": 1.4, "▲": 1.2, "△": 1.1, "✕": 0.0, "": 1.0}
            safety_threshold = 0.05  # 5%（地方は低確率でも狙う価値あり）
            st.info(f"🌙 地方競馬（NAR）モード - 波乱を考慮した期待値計算")

        probs = edited_df['AIスコア(%)'] / 100.0
        odds = edited_df['現在オッズ']
        marks = edited_df['予想印']

        evs = []
        for p, o, m in zip(probs, odds, marks):
            # Safety filter (race type specific)
            if p < safety_threshold:
                ev = -1.0
            else:
                w = mark_weights.get(m, 1.0)

                # Adjust probability for NAR (higher uncertainty)
                if race_type == 'NAR':
                    # 地方は予測の不確実性を考慮
                    # 高い確率は少し下げ、低い確率は少し上げる
                    adjusted_p = p * 0.9 + 0.05
                else:
                    adjusted_p = p

                ev = (adjusted_p * w * o) - 1.0
            evs.append(ev)
            
        edited_df['期待値(EV)'] = evs
        
        # Highlight high EV
        def highlight_ev(s):
            is_high = s > 0
            return ['background-color: #d4edda' if v else '' for v in is_high]
        
        st.dataframe(edited_df.style.applymap(lambda x: 'background-color: #d4edda' if x > 0 else '', subset=['期待値(EV)']))
        
        # Visualization
        st.subheader("📊 詳細分析")
        
        try:
            # 1. Select a horse for detailed analysis
            horse_options = df_display['馬名'].tolist()
            selected_horse_name = st.selectbox("詳細を見る馬を選択", horse_options)
            
            # Find row
            row = df_display[df_display['馬名'] == selected_horse_name].iloc[0]
            
            # 2. Radar Chart (5 Axes)
            # Speed (3F), Stamina (Rank), Power (Weight), Experience (Age), Style (RunStyle)
            
            score_speed = max(0, min(10, (40 - row.get('weighted_avg_last_3f', 36)) * 1.5))
            score_stamina = max(0, min(10, (18 - row.get('weighted_avg_rank', 18)) / 1.8))
            score_power = max(0, min(10, (row.get('weighted_avg_horse_weight', 470) - 400) / 15))
            score_exp = max(0, min(10, (row.get('age', 3) - 2) * 2))
            score_style = row.get('weighted_avg_run_style', 3) * 2.5
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=[score_speed, score_stamina, score_power, score_exp, score_style, score_speed],
                theta=['スピード (3F)', 'スタミナ (着順)', 'パワー (馬体重)', '経験 (年齢)', '脚質'],
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
