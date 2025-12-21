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
    - **予想家の印**: あなたの直感（印）を入力することで、AIの確率を補正できます (◎=1.5倍など)。
    """)

# --- Admin Menu ---
with st.expander("🛠 管理者メニュー (データ更新・モデル再読み込み)"):
    col_admin1, col_admin2 = st.columns(2)
    
    with col_admin1:
        if st.button("📅 レース一覧を更新 (今後1週間)"):
            with st.spinner("最新のレース情報を取得中 (約1分)..."):
                success, msg = auto_scraper.scrape_todays_schedule()
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"エラー: {msg}")

    with col_admin2:
        if st.button("🧠 最新モデルを再読み込み"):
            load_model.clear()
            st.cache_resource.clear()
            st.success("モデルを再読み込みしました！")

# --- Race Selection ---
st.subheader("📍 レース選択")

schedule_data = load_schedule_data()
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
             if st.button("🔄 現在オッズのみ更新"):
                 with st.spinner("最新オッズを取得中..."):
                     new_odds = auto_scraper.scrape_odds_for_race(race_id)
                     if new_odds:
                         # Update Session State
                         # new_odds is list of {number, odds}
                         odds_map = {x['number']: x['odds'] for x in new_odds}
                         
                         target_df = st.session_state[f'data_{race_id}']
                         
                         # Update '単勝' and 'Odds'
                         # Map using '馬 番' (ensure int type matching)
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
        
        # Calculate EV
        mark_weights = {"◎": 1.5, "◯": 1.2, "▲": 1.1, "△": 1.05, "✕": 0.0, "": 1.0}
        
        probs = edited_df['AIスコア(%)'] / 100.0
        odds = edited_df['現在オッズ']
        marks = edited_df['予想印']
        
        evs = []
        kellys = []
        
        for p, o, m in zip(probs, odds, marks):
            # Penalize low probability (Safety filter)
            if p < 0.08: # Ignore if AI chance is less than 8%
                ev = -1.0
                kelly = 0.0
            else:
                w = mark_weights.get(m, 1.0)
                p_weighted = p * w
                
                # EV
                ev = (p_weighted * o) - 1.0
                
                # Kelly: (p*o - 1) / (o - 1)
                if o > 1.0:
                    k = ((p_weighted * o) - 1.0) / (o - 1.0)
                    kelly = max(0.0, k * 100) # Convert to %
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
