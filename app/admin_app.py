import streamlit as st
import subprocess
import os
import sys
import pandas as pd
from datetime import date, datetime
import time
import plotly.graph_objects as go

# Add ml to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml'))
try:
    import train_model
    import feature_engineering
    import importlib
    importlib.reload(train_model)
    importlib.reload(feature_engineering)
except ImportError:
    st.error("Failed to import train_model. Make sure ml/train_model.py exists.")

# Set page config
st.set_page_config(page_title="JRA データ管理パネル", layout="wide")

st.title("🏇 JRA スクレイピング管理パネル")

# --- UI Layout ---
st.markdown("### ⚙️ 設定")

mode_option = st.radio("開催モード (Mode)", ["JRA (中央競馬)", "NAR (地方競馬)"], index=0)
mode_val = "JRA" if "JRA" in mode_option else "NAR"
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Target filenames based on mode
if mode_val == "NAR":
    csv_filename = "database_nar.parquet"
    target_parquet = os.path.join(project_root, "data", "raw", "database_nar.parquet")
    target_csv = os.path.join(project_root, "data", "raw", "database_nar.csv")
    model_name = "lgbm_model_nar.pkl"
    processed_data_path = os.path.join(project_root, "ml", "processed_data_nar.parquet")
else:
    csv_filename = "database.parquet"
    target_parquet = os.path.join(project_root, "data", "raw", "database.parquet")
    target_csv = os.path.join(project_root, "data", "raw", "database.csv")
    model_name = "lgbm_model.pkl"
    processed_data_path = os.path.join(project_root, "ml", "processed_data.parquet")

st.markdown("---")

# --- 1. Data Management Section (Top Priority) ---
st.markdown("## 🛠️ データ管理 (Data Management)")

# 1.1 Upload
st.markdown("### 📤 データアップロード (CSV)")
uploaded_file = st.file_uploader("既存のデータベースCSV (database.csvなど) をアップロード", type=["csv"], key="uploader")

if uploaded_file is not None:
    if st.button("変換して保存 (CSV -> Parquet)", type="primary"):
        with st.spinner("CSVを読み込み、Parquetに変換中..."):
            try:
                df_upload = pd.read_csv(uploaded_file, low_memory=False, dtype={'horse_id': str, 'race_id': str})
                
                # Save as CSV (Raw)
                df_upload.to_csv(target_csv, index=False)
                st.success(f"✅ CSV保存完了: {os.path.basename(target_csv)}")
                
                # Save as Parquet
                df_upload.to_parquet(target_parquet, compression='snappy', index=False)
                st.success(f"✅ Parquet変換・保存完了: {os.path.basename(target_parquet)}")
            except Exception as e:
                st.error(f"変換エラー: {e}")

st.markdown("---")

# 1.2 Preview
st.markdown("### 📊 データベースプレビュー")
if os.path.exists(target_parquet):
    try:
        df = pd.read_parquet(target_parquet)
        st.metric("総データ数 (行)", len(df))
        st.caption("※データ量が多いため、最新の1000件のみ表示しています。")
        st.dataframe(df.tail(1000), width='stretch')
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
else:
    st.warning(f"{csv_filename} が見つかりません。")

st.caption("使い方: Colabでデータを取得後、ここでアップロードするか、Git経由で反映させてください。")

st.markdown("---")

# --- 3. MLOps Section (Training & Deploy) ---
st.markdown("## 🤖 機械学習モデルの管理 (MLOps)")

st.info("💡 **全自動プロセス**: ボタン一つで「前処理 → 最適化(100回) → 学習 → 較正(Calibration) → Git Push」まで実行します。")

# 2.1 Settings
st.markdown("### 学習設定")
# All settings are fixed/default now
st.markdown("""
- **最適化 (Optuna)**: ✅ ON (100 trials)
- **確率較正 (Calibration)**: ✅ ON
- **前処理**: ✅ 自動実行
""")

auto_push = st.checkbox("学習完了後、リポジトリを自動更新 (Git Push)", value=True, help="学習成功時に変更を自動的にコミット＆プッシュします")

st.markdown("---")

# 2.2 Action
st.markdown("### アクション")
if st.button("🚀 フル学習プロセスを開始 (最適化+較正+デプロイ)", type="primary", use_container_width=True):
    
    # Paths
    db_path = target_parquet
    data_path = processed_data_path
    
    model_dir = os.path.join(project_root, "ml", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, model_name)

    # 1. Preprocess
    with st.spinner("1/4 データ前処理 & 統計データ作成中..."):
        if os.path.exists(db_path):
            # Calculate Features
            try:
                feature_engineering.calculate_features(db_path, data_path)
                
                # Export Stats
                import export_stats
                importlib.reload(export_stats)
                if export_stats.export_stats(mode=mode_val):
                    st.success("統計データ(Inference用)のエクスポート完了")
                else:
                    st.warning("統計データのエクスポートに失敗 (学習は続行)")
                    
                # Save to SQL DB (Optional but good for inspection)
                try:
                    import db_helper
                    importlib.reload(db_helper)
                    df_proc = pd.read_parquet(data_path)
                    db_path_sql = os.path.join(project_root, "keiba_data.db")
                    # Ensure file creation
                    conn_check = importlib.import_module("sqlite3").connect(db_path_sql)
                    conn_check.close()
                    db = db_helper.KeibaDatabase(db_path_sql)
                    db.save_processed_data(df_proc, mode=mode_val)
                except Exception as e:
                    print(f"SQL Save skipped: {e}")

            except Exception as e:
                st.error(f"前処理エラー: {e}")
                st.stop()
        else:
                st.error(f"{csv_filename} が見つかりません。")
                st.stop()

    # 2. Optimization
    n_trials = 100
    with st.spinner(f"2/4 ハイパーパラメータ最適化中 (Optuna {n_trials} trials)..."):
        try:
            opt_res = train_model.optimize_hyperparameters(data_path, n_trials=n_trials)
            if opt_res:
                st.success(f"最適化完了: Best AUC {opt_res['best_auc']:.4f}")
                st.session_state['best_params'] = opt_res['best_params']
            else:
                st.warning("最適化スキップ（デフォルト設定を使用）")
        except Exception as e:
            st.error(f"最適化エラー: {e}")
            st.stop()
    
    # 3. Training & Calibration
    with st.spinner("3/4 モデル学習 & 確率較正中..."):
        params = st.session_state.get('best_params', None)
        try:
            # Force calibrate=True
            results = train_model.train_and_save_model(data_path, model_path, params=params, calibrate=True)
            if results:
                st.success("学習完了！")
                st.session_state['ml_results'] = results
            else:
                st.error("学習失敗")
                st.stop()
        except Exception as e:
            st.error(f"学習エラー: {e}")
            st.stop()

    # 4. Auto Push
    if auto_push:
        with st.spinner("4/4 リポジトリ更新中 (Git Push)..."):
            try:
                # Relative paths for git
                if mode_val == "NAR":
                    model_path_rel = "ml/models/lgbm_model_nar.pkl"
                else:
                    model_path_rel = "ml/models/lgbm_model.pkl"
                
                meta_path_rel = model_path_rel.replace('.pkl', '_meta.json')
                stats_path_rel = f"ml/models/feature_stats{'_nar' if mode_val == 'NAR' else ''}.pkl" # Stats file

                commit_msg = f"Auto-update model ({mode_val}): {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                cmds = [
                    ["git", "add", model_path_rel, meta_path_rel, stats_path_rel],
                    ["git", "commit", "-m", commit_msg],
                    ["git", "push", "origin", "main"]
                ]
                
                for cmd in cmds:
                    res = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
                    if res.returncode != 0:
                        if "nothing to commit" not in (res.stdout + res.stderr).lower():
                            st.warning(f"Git Warning: {res.stderr}")
                
                st.success("✅ 全プロセス完了！リポジトリ更新済み")
            except Exception as e:
                st.error(f"Git Push Error: {e}")


# --- Display Training Results ---
if 'ml_results' in st.session_state:
    st.markdown("---")
    res = st.session_state['ml_results']
    
    st.markdown("#### 📊 学習結果レポート")
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Accuracy", f"{res['accuracy']:.4f}")
    m_col2.metric("AUC", f"{res['auc']:.4f}")
    m_col3.metric("Positive Rate", f"{res.get('win_rate', 0.0):.2%}")
    
    # Feature Importance only (Learning Curve requires evals_result which might be bulky or different format now)
    if 'feature_importance' in res:
        fi = pd.DataFrame(res['feature_importance'])
        if not fi.empty:
            fig_fi = go.Figure(go.Bar(
                x=fi['Value'], y=fi['Feature'], orientation='h'
            ))
            fig_fi.update_layout(
                title="特徴量重要度 (Top 20)",
                yaxis=dict(autorange="reversed"),
                xaxis_title="Importance (Gain)",
                 height=600
            )
            st.plotly_chart(fig_fi, width="stretch")

st.markdown("---")

# --- 2. D-Index Optimization Section ---
st.markdown("## ⚖️ D指数 重み最適化 (D-Index Optimization)")
st.info("💡 過去のレースデータを用いて、D指数の構成要素（AI指数、適性指数、血統指数）の最適な重み配分を算出します。")

# 2.1 Settings
st.markdown("### 期間設定")
period_opt = st.selectbox("検証期間 (Verification Period)", ["直近1年間 (Recommended)", "直近3年間", "全期間"], index=0)

# Load current weights
current_weights = {'ai': 0.4, 'compat': 0.5, 'blood': 0.1}
d_index_conf_path = os.path.join(project_root, "config", "d_index_config.json")
if os.path.exists(d_index_conf_path):
    try:
        with open(d_index_conf_path, 'r') as f:
            current_weights = json.load(f)
    except:
        pass

st.markdown("### 現在の重み")
st.write(current_weights)

st.markdown("---")

# 2.2 Action
st.markdown("### アクション")
if st.button("⚖️ 重みを最適化する (Optimize Weights)", type="primary"):
    with st.spinner("最適化を実行中... (これには数分かかる場合があります)"):
        try:
            # 1. Load Data
            if not os.path.exists(processed_data_path):
                st.error("処理済みデータが見つかりません。先に「MLOps」で前処理を実行してください。")
                st.stop()
            
            df_proc = pd.read_parquet(processed_data_path)
            
            # 2. Filter Period
            df_proc['date'] = pd.to_datetime(df_proc['date'])
            max_date = df_proc['date'].max()
            
            if "1年間" in period_opt:
                start_date = max_date - pd.Timedelta(days=365)
                df_proc = df_proc[df_proc['date'] >= start_date]
            elif "3年間" in period_opt:
                start_date = max_date - pd.Timedelta(days=365*3)
                df_proc = df_proc[df_proc['date'] >= start_date]
            
            st.write(f"検証データ数: {len(df_proc)} rows (期間: {df_proc['date'].min().date()} ~ {df_proc['date'].max().date()})")

            # 3. Optimize (Inline logic for now, using scoring.py)
            import scoring
            importlib.reload(scoring)
            import optuna
            from sklearn.metrics import roc_auc_score
            
            def objective(trial):
                # 1. Top Level Weights
                w_ai = trial.suggest_float('ai', 0.0, 1.0)
                w_compat = trial.suggest_float('compat', 0.0, 1.0)
                w_blood = trial.suggest_float('blood', 0.0, 1.0)
                
                # 2. Sub Weights for Compatibility
                w_jockey = trial.suggest_float('jockey', 0.0, 1.0)
                w_dist = trial.suggest_float('distance', 0.0, 1.0)
                w_course = trial.suggest_float('course', 0.0, 1.0)

                # Normalize constraints
                top_sum = w_ai + w_compat + w_blood
                if top_sum == 0: return 0.0
                
                sub_sum = w_jockey + w_dist + w_course
                if sub_sum == 0: return 0.0

                # Create config dict
                config = {
                    'top_level': {
                        'ai': w_ai / top_sum,
                        'compat': w_compat / top_sum,
                        'blood': w_blood / top_sum
                    },
                    'compat_sub_weights': {
                        'jockey': w_jockey / sub_sum,
                        'distance': w_dist / sub_sum,
                        'course': w_course / sub_sum
                    }
                }
                
                # Calculate D-Scores for all rows
                # We need to compute Compat_Index DYNAMICALLY based on sub-weights
                
                # Vectorized Calc for Speed
                # Extract columns
                j_compat = df_proc.get('jockey_compatibility', 0).fillna(0)
                d_compat = df_proc.get('distance_compatibility', 0).fillna(0)
                c_compat = df_proc.get('course_compatibility', 0).fillna(0)
                
                # Calculate Dynamic Compat Index
                # Weighted Sum
                compat_scores = (j_compat * config['compat_sub_weights']['jockey']) + \
                                (d_compat * config['compat_sub_weights']['distance']) + \
                                (c_compat * config['compat_sub_weights']['course'])
                
                # Note: Original logic was specialized (ranking average). 
                # For optimization speed, we approximate: 
                # If the inputs are already 0-100 or ranks, we must handle carefully.
                # Looking at public_app logic: compatibility is RANK based (1-18).
                # So we need to average the Ranks, then Normalize.
                
                avg_rank = compat_scores # Since weights sum to 1.0
                
                # Convert Rank to Score (0-100)
                # score = (18.0 - avg_rank) / 17.0 * 100
                compat_index_vec = (18.0 - avg_rank) / 17.0 * 100
                compat_index_vec = compat_index_vec.clip(0, 100)
                
                # Bloodline Index (Fixed logic usually, but can re-calc if needed)
                if 'Bloodline_Index' not in df_proc.columns:
                    df_proc['Bloodline_Index'] = df_proc.apply(scoring.calculate_bloodline_index, axis=1)
                
                # Final D-Index
                d_scores = (df_proc['AI_Score'] * config['top_level']['ai']) + \
                           (compat_index_vec * config['top_level']['compat']) + \
                           (df_proc['Bloodline_Index'] * config['top_level']['blood'])
                
                try:
                    auc = roc_auc_score(df_proc['target_win'], d_scores)
                    return auc
                except:
                    return 0.0

            study = optuna.create_study(direction='maximize')
            study.optimize(objective, n_trials=50) 
            
            # Extract Best Parameters
            best_p = study.best_params
            
            # Normalize Best Params to final config
            top_total = best_p['ai'] + best_p['compat'] + best_p['blood']
            sub_total = best_p['jockey'] + best_p['distance'] + best_p['course']
            
            final_config = {
                "top_level": {
                    "ai": round(best_p['ai'] / top_total, 3),
                    "compat": round(best_p['compat'] / top_total, 3),
                    "blood": round(best_p['blood'] / top_total, 3)
                },
                "compat_sub_weights": {
                    "jockey": round(best_p['jockey'] / sub_total, 3),
                    "distance": round(best_p['distance'] / sub_total, 3),
                    "course": round(best_p['course'] / sub_total, 3)
                }
            }
            
            st.success(f"✅ 詳細最適化完了! Best AUC: {study.best_value:.4f}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 大枠の重み (Top Level)")
                st.write(final_config['top_level'])
            with c2:
                st.markdown("#### 適性指数の内訳 (Sub Weights)")
                st.write(final_config['compat_sub_weights'])
            
            # 4. Save
            if st.button("💾 この設定を保存して適用する"):
               with open(d_index_conf_path, 'w') as f:
                   json.dump(final_config, f, indent=4)
               st.success("設定を保存しました。")
               st.session_state['current_weights'] = final_config

        except Exception as e:
            st.error(f"最適化エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
