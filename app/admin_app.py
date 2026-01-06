import streamlit as st
import subprocess
import os
import sys
import pandas as pd
from datetime import date, datetime
import time
import plotly.graph_objects as go
import json

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
period_opt = st.selectbox("検証期間 (Verification Period)", ["直近1ヶ月間 (Latest 1 Month)", "直近1年間 (Recommended)", "直近3年間", "全期間"], index=0)

# Load current weights
current_weights = {'ai': 0.4, 'compat': 0.5, 'blood': 0.1}
d_index_conf_path = os.path.join(project_root, "config", f"d_index_config_{mode_val.lower()}.json")

if os.path.exists(d_index_conf_path):
    try:
        with open(d_index_conf_path, 'r') as f:
            current_weights = json.load(f)
    except:
        pass
# Fallback to default if specific doesn't exist but generic does (migration)
elif os.path.exists(os.path.join(project_root, "config", "d_index_config.json")):
     try:
        with open(os.path.join(project_root, "config", "d_index_config.json"), 'r') as f:
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
            # Fix: Handle mixed formats or Japanese format
            # Keep original for fallback
            date_raw_temp = df_proc['date'].copy()
            df_proc['date'] = pd.to_datetime(df_proc['date'], errors='coerce')
            
            # If many dates failed (NaT), try Japanese format explicit parsing using saved raw data
            if df_proc['date'].isna().sum() > len(df_proc) * 0.5:
                 df_proc['date'] = pd.to_datetime(date_raw_temp, format='%Y年%m月%d日', errors='coerce')
            
            max_date = df_proc['date'].max()
            
            if "1ヶ月間" in period_opt:
                start_date = max_date - pd.Timedelta(days=30)
                df_proc = df_proc[df_proc['date'] >= start_date]
            elif "1年間" in period_opt:
                start_date = max_date - pd.Timedelta(days=365)
                df_proc = df_proc[df_proc['date'] >= start_date]
            elif "3年間" in period_opt:
                start_date = max_date - pd.Timedelta(days=365*3)
                df_proc = df_proc[df_proc['date'] >= start_date]
            
            st.write(f"検証データ数: {len(df_proc)} rows (期間: {df_proc['date'].min().date()} ~ {df_proc['date'].max().date()})")

            # Prepare Predictions (AI_Score)
            if 'AI_Score' not in df_proc.columns:
                st.info("🔄 AIスコアを算出中 (Calculating AI Scores)...")
                import joblib
                import lightgbm as lgb
                
                # Fix: Define model_path
                # The Find command showed it is in "ml/models/lgbm_model.pkl"
                model_path = os.path.join(project_root, "ml", "models", model_name)
                
                if os.path.exists(model_path):
                    try:
                        clf = joblib.load(model_path)
                        
                        # Prepare features for prediction
                        # We need to use the exact same features as training. 
                        # Ideally we load 'features' from metadata, but let's try to use all numeric/category cols available
                        # that match the model's feature_name() requirements.
                        
                        model_features = clf.feature_name()
                        
                        # Check exist
                        missing_feats = [f for f in model_features if f not in df_proc.columns]
                        if missing_feats:
                             # Try to reconstruct if possible or zero-fill? 
                             # Zero-fill is safer than crashing, though precision drops.
                             for mf in missing_feats:
                                 df_proc[mf] = 0
                        
                        X_pred = df_proc[model_features].copy()
                        
                        # Ensure categories are cast to category type if model expects it
                        # (LGBM handles categories if passed as 'category' dtype)
                        # We should check metadata for categorical features but simple attempt:
                        for col in X_pred.select_dtypes(include=['object']).columns:
                            try:
                                X_pred[col] = X_pred[col].astype('category')
                            except:
                                pass
                        
                        # Predict
                        # clf is either LGBMBooster or LGBMClassifier/Wrapper
                        if hasattr(clf, 'predict_proba'):
                             y_pred = clf.predict_proba(X_pred)[:, 1]
                        else:
                             # Booster
                             y_pred = clf.predict(X_pred)
                        
                        df_proc['AI_Score'] = y_pred * 100.0
                        st.success(f"✅ AIスコアの算出完了")

                    except Exception as e:
                        st.error(f"AIスコア算出エラー: {e}")
                        # Fallback for optimization not to crash entirely, but warn heavily
                        if 'odds' in df_proc.columns:
                             df_proc['AI_Score'] = (100.0 / (df_proc['odds'] + 1.0)).clip(0, 100) * 3.0
                             st.warning("⚠️ モデル予測に失敗したため、オッズから簡易算出したスコアで代用します。")
                        else:
                             df_proc['AI_Score'] = 50.0
                else:
                    # Fallback if no model exists
                     st.warning("⚠️ 学習済みモデルが見つかりません。先に「MLOps」で学習を実行してください。現在はオッズからの簡易スコアを使用します。")
                     if 'odds' in df_proc.columns:
                         df_proc['AI_Score'] = (100.0 / (df_proc['odds'] + 1.0)).clip(0, 100) * 3.0 
                     else:
                         df_proc['AI_Score'] = 50.0
            
            # Ensure Score is 0-100
            df_proc['AI_Score'] = df_proc['AI_Score'].clip(0, 100).fillna(0)

            st.markdown("### 最適化設定")
            # Enforce Top 3 Optimization as per user request
            st.info("ℹ️ **最適化の目標**: 3着内率の最大化 (Top 3 Priority)\n\n安定した的中精度を確保するため、今回は「3着以内に入る確率」を高める設定で最適化を行います。")
            opt_target = "3着内重視 (Top 3)"
            target_col = 'target_top3'

            # Prepare Targets
            if 'target_win' not in df_proc.columns:
                 # Try to create from rank
                 if 'rank' in df_proc.columns:
                     df_proc['target_win'] = (df_proc['rank'] == 1).astype(int)
                     df_proc['target_top3'] = (df_proc['rank'] <= 3).astype(int)
                 else:
                     st.error("Target column (rank or target_win) not found.")
                     st.stop()
            else:
                 # Ensure top3 exists if not present
                 if 'target_top3' not in df_proc.columns:
                     if 'rank' in df_proc.columns:
                         df_proc['target_top3'] = (df_proc['rank'] <= 3).astype(int)
                     else:
                         s_target_win = df_proc['target_win']
                         df_proc['target_top3'] = s_target_win # Fallback logic

            # 3. Optimize (Inline logic for now, using scoring.py)
            import scoring
            importlib.reload(scoring)
            import optuna
            from sklearn.metrics import roc_auc_score
            from scipy.stats import spearmanr
            
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
                # Fix: 'get' returns default value if key missing. If 0 is returned, .fillna fails.
                # Only use .fillna if the column exists.
                j_compat = df_proc['jockey_compatibility'] if 'jockey_compatibility' in df_proc.columns else 0
                d_compat = df_proc['distance_compatibility'] if 'distance_compatibility' in df_proc.columns else 0
                c_compat = df_proc['course_compatibility'] if 'course_compatibility' in df_proc.columns else 0
                
                # Fill NaNs if it is a Series
                if isinstance(j_compat, pd.Series): j_compat = j_compat.fillna(0)
                if isinstance(d_compat, pd.Series): d_compat = d_compat.fillna(0)
                if isinstance(c_compat, pd.Series): c_compat = c_compat.fillna(0)
                
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
                
                # Approximate rank normalization (1 is best, 18 is worst)
                # We want Higher Score = Better. 
                # Since input compat scores are RANKS (smaller is better), 
                # The weighted sum will be a "Weighted Rank". Smaller is still Better.
                # To make it 0-100 Score where 100 is best:
                
                weighted_rank = compat_scores 
                
                # Convert Rank to Score (0-100)
                # 1 -> 100, 18 -> 0
                compat_index_vec = (18.0 - weighted_rank) / 17.0 * 100
                compat_index_vec = compat_index_vec.clip(0, 100)
                
                # Bloodline Index (Fixed logic usually, but can re-calc if needed)
                if 'Bloodline_Index' not in df_proc.columns:
                    df_proc['Bloodline_Index'] = df_proc.apply(scoring.calculate_bloodline_index, axis=1)
                
                # Final D-Index
                d_scores = (df_proc['AI_Score'] * config['top_level']['ai']) + \
                           (compat_index_vec * config['top_level']['compat']) + \
                           (df_proc['Bloodline_Index'] * config['top_level']['blood'])
                
                try:
                    # Metric: AUC (Win Discrimination or Top3 Discrimination)
                    auc = roc_auc_score(df_proc[target_col], d_scores)
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
            
            
            # Save to session state to persist after rerun (needed for Save button)
            st.session_state['optimized_config'] = final_config
            st.session_state['opt_auc'] = study.best_value
            st.rerun()

        except Exception as e:
            st.error(f"最適化エラー: {e}")
            import traceback
            st.code(traceback.format_exc())

# --- Results Display & Save Section (Persistent) ---
if 'optimized_config' in st.session_state:
    final_config = st.session_state['optimized_config']
    best_auc = st.session_state.get('opt_auc', 0.0)
    
    st.markdown("---")
    st.markdown(f"### ✅ 最適化結果 (Best AUC: {best_auc:.4f})")
    st.info("最適化が完了しました。以下の設定を保存して適用できます。")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 大枠の重み (Top Level)")
        st.write(final_config['top_level'])
    with c2:
        st.markdown("#### 適性指数の内訳 (Sub Weights)")
        st.write(final_config['compat_sub_weights'])
    
    # 4. Save
    if st.button("💾 この設定を保存して適用する", type="primary"):
        try:
           with open(d_index_conf_path, 'w') as f:
               json.dump(final_config, f, indent=4)
           st.success("設定を保存しました！次回リロード時から新しい重みが適用されます。")
           st.session_state['current_weights'] = final_config
        except Exception as e:
            st.error(f"保存エラー: {e}")

# --- 5. Recent Race Verification Section ---
st.markdown("---")
st.markdown("## 🏁 直近レースの的中確認 (Recent Race Verification)")
st.info("データ・学習モデル・重み設定を使って、直近開催日のレース結果と予想（D指数上位6頭）を照合します。")

if not os.path.exists(processed_data_path):
    st.error(f"データが見つかりません: {processed_data_path}")
else:
    # 1. Pre-load Dates for Selection (Lightweight)
    try:
        # Read only date column
        df_dates = pd.read_parquet(processed_data_path, columns=['date'])
        
        # Robust Date Parsing
        date_raw_dates = df_dates['date'].copy()
        df_dates['date'] = pd.to_datetime(df_dates['date'], errors='coerce')
        if df_dates['date'].isna().sum() > len(df_dates) * 0.5:
             df_dates['date'] = pd.to_datetime(date_raw_dates, format='%Y年%m月%d日', errors='coerce')
        
        df_dates['date_norm'] = df_dates['date'].dt.normalize()
        unique_dates = sorted(df_dates['date_norm'].dropna().unique(), reverse=True)
        
        if not unique_dates:
            st.warning("利用可能な日付データがありません。")
            st.stop()
            
        # Select Date
        selected_date_norm = st.selectbox(
            "対象日を選択 (Verification Date)", 
            unique_dates, 
            index=0,
            format_func=lambda x: x.strftime('%Y-%m-%d')
        )
        
    except Exception as e:
        st.error(f"日付データの読み込みに失敗: {e}")
        st.stop()

    if st.button("🚀 レース結果を確認する"):
        # 2. Load Full Data & Filter
        df_recent = pd.read_parquet(processed_data_path)
        
        # Ensure Date (Repeat robust parsing for full dataframe)
        date_raw_temp = df_recent['date'].copy()
        df_recent['date'] = pd.to_datetime(df_recent['date'], errors='coerce')
        if df_recent['date'].isna().sum() > len(df_recent) * 0.5:
             df_recent['date'] = pd.to_datetime(date_raw_temp, format='%Y年%m月%d日', errors='coerce')
        
        df_recent['date_norm'] = df_recent['date'].dt.normalize()
        
        # Filter by Selected Date
        df_target = df_recent[df_recent['date_norm'] == selected_date_norm].copy()
        
        # --- Fix: Merge Race Metadata from Raw Database if missing ---
        # Processed data often drops non-numeric columns like 'レース名'. 
        # We recover them from the original 'database.parquet' (target_parquet).
        meta_cols_needed = ['race_name', 'レース名', '会場', 'レース番号', 'R']
        missing_meta = [c for c in meta_cols_needed if c not in df_target.columns]
        
        if missing_meta and os.path.exists(target_parquet):
            try:
                # Load raw data (subset of cols)
                # We don't know exact col names in raw, so load needed + race_id
                df_raw = pd.read_parquet(target_parquet)
                
                # Select relevant columns that exist in raw
                raw_cols = [c for c in meta_cols_needed if c in df_raw.columns]
                if 'race_id' in df_raw.columns and raw_cols:
                    # Create a metadata map (one row per race_id)
                    df_meta = df_raw[['race_id'] + raw_cols].drop_duplicates(subset=['race_id'])
                    
                    # Check types for merge (race_id often str vs int mismatch)
                    df_target['race_id'] = df_target['race_id'].astype(str)
                    df_meta['race_id'] = df_meta['race_id'].astype(str)
                    
                    # Merge
                    df_target = pd.merge(df_target, df_meta, on='race_id', how='left', suffixes=('', '_raw'))
                    
                    # Fill missing columns from _raw
                    for col in raw_cols:
                        if col not in df_target.columns:
                            df_target[col] = df_target[f"{col}_raw"]
                        elif col in df_target.columns and df_target[col].isna().all():
                             df_target[col] = df_target[f"{col}_raw"].fillna(df_target[col])
            except Exception as e:
                st.warning(f"メタデータ結合警告: {e}")
        # -------------------------------------------------------------
    
        st.write(f"対象日: **{selected_date_norm.date()}** (全 {len(df_target['race_id'].unique())} レース)")

        # 3. Load Current Config Weights
        import scoring
        importlib.reload(scoring)
        
        current_conf = {}
        if os.path.exists(d_index_conf_path):
            try:
                with open(d_index_conf_path, 'r') as f:
                    current_conf = json.load(f)
            except:
                pass
        
        # 4. Calculate AI Score (if missing)
        if 'AI_Score' not in df_target.columns:
            model_path = os.path.join(project_root, "ml", "models", model_name)
            if os.path.exists(model_path):
                try:
                    import joblib
                    clf = joblib.load(model_path)
                    model_features = clf.feature_name()
                    
                    # Fill missing
                    for mf in model_features:
                        if mf not in df_target.columns:
                            df_target[mf] = 0
                    
                    
                    # Check if data exists
                    if df_target.empty:
                        st.warning("この開催日のデータが見つかりませんでした。")
                        st.stop()
                    
                    # Category Handling
                    X_pred = df_target[model_features].copy()
                    for col in X_pred.select_dtypes(include=['object']).columns:
                         X_pred[col] = X_pred[col].astype('category')

                    # Predict
                    if hasattr(clf, 'predict_proba'):
                         y_pred = clf.predict_proba(X_pred)[:, 1]
                    else:
                         y_pred = clf.predict(X_pred)
                    
                    
                    df_target['AI_Score'] = y_pred * 100.0
                except Exception as e:
                    st.warning(f"AIスコア算出失敗: {e}")
                    df_target['AI_Score'] = 50.0
            else:
                 st.warning("学習済みモデルがないため、AIスコアは仮定値(50)またはオッズから計算されます。")
                 if 'odds' in df_target.columns:
                     df_target['AI_Score'] = (100.0 / (df_target['odds'] + 1.0)).clip(0, 100) * 3.0
                 else:
                     df_target['AI_Score'] = 50.0

        # 5. Calculate D-Index
        df_target['Compat_Index'] = df_target.apply(lambda row: scoring.calculate_pure_compat(
            row, 
            current_conf.get('compat_sub_weights', {'jockey': 0.4, 'distance': 0.3, 'course': 0.3})
        ), axis=1)
        df_target['Bloodline_Index'] = df_target.apply(scoring.calculate_bloodline_index, axis=1)
        df_target['D_Index'] = df_target.apply(lambda row: scoring.calculate_d_index(row, current_conf), axis=1)

        # 6. Display Results Race by Race
        race_ids = sorted(df_target['race_id'].unique())
        
        for rid in race_ids:
            df_race = df_target[df_target['race_id'] == rid].copy()        
            # Prepare Race Info
            # Prioritize 'レース名' from raw data as 'race_name' might be empty or dash
            r_name_raw = df_race['レース名'].iloc[0] if 'レース名' in df_race.columns else ""
            r_name_proc = df_race['race_name'].iloc[0] if 'race_name' in df_race.columns else "-"
            race_name = r_name_raw if r_name_raw and str(r_name_raw) != "nan" else r_name_proc
            
            race_no = df_race['レース番号'].iloc[0] if 'レース番号' in df_race.columns else ""
            if not race_no and 'R' in df_race.columns:
                 race_no = df_race['R'].iloc[0]
            
            # Remove 'R' if exists to avoid '1RR'
            race_no = str(race_no).replace('R', '').replace('r', '')
            
            venue = df_race['会場'].iloc[0] if '会場' in df_race.columns else ""
            if not venue and 'venue_id' in df_race.columns:
                 # Simple mapping fallback or just show ID
                 venue = str(df_race['venue_id'].iloc[0])

            header_str = f"#### {venue} {race_no}R: {race_name}" if race_no else f"#### {race_name} ({venue})"
            
            
            # Ensure '単勝 オッズ' exists for display
            if '単勝 オッズ' not in df_race.columns and 'odds' in df_race.columns:
                df_race['単勝 オッズ'] = df_race['odds']
            
            # Sort by D-Index (Prediction)
            df_pred = df_race.sort_values('D_Index', ascending=False)
            # Handle cases where '単勝 オッズ' might still be missing (rare)
            disp_cols = ['馬 番', '馬名', 'D_Index', 'rank']
            if '単勝 オッズ' in df_pred.columns:
                disp_cols.append('単勝 オッズ')
                
            top6_pred = df_pred.head(6)[disp_cols]
            
            # Actual Result (Top 3)
            df_actual = df_race[df_race['rank'].isin([1, 2, 3])].sort_values('rank')
            
            disp_cols_act = ['rank', '馬 番', '馬名', 'D_Index']
            if '単勝 オッズ' in df_actual.columns:
                 disp_cols_act.append('単勝 オッズ')
                 
            top3_actual = df_actual[disp_cols_act]
            
            # Rename for Display
            rename_map = {'D_Index': 'D指数', 'rank': '着順'}
            top6_pred = top6_pred.rename(columns=rename_map)
            top3_actual = top3_actual.rename(columns=rename_map)

            # Integer Cast for Rank (着順)
            if '着順' in top6_pred.columns:
                top6_pred['着順'] = top6_pred['着順'].fillna(0).astype(int).astype(str).replace('0', '-')
            if '着順' in top3_actual.columns:
                top3_actual['着順'] = top3_actual['着順'].astype(int)
            
            with st.container():
                st.markdown(header_str)
                c1, c2 = st.columns(2)
                
                with c1:
                    st.markdown("🎯 **D指数 上位6頭 (予想)**")
                    # Highlight if correct
                    def highlight_hit(row):
                        try:
                            r_val = int(row['着順'])
                            if r_val <= 3:
                                return ['background-color: #d4edda'] * len(row)
                        except:
                            pass
                        return [''] * len(row)
                        
                    st.dataframe(top6_pred.style.apply(highlight_hit, axis=1), hide_index=True)
                
                with c2:
                    st.markdown("🏆 **結果 (3着以内)**")
                    st.dataframe(top3_actual, hide_index=True)
                
                # Hit Check
                top6_ids = set(top6_pred['馬 番'])
                actual_ids = set(top3_actual['馬 番'])
                hits = top6_ids.intersection(actual_ids)
                
                if len(hits) == 3:
                    st.success(f"🎉 パーフェクト的中! ({len(hits)}/3頭推奨)")
                elif len(hits) >= 1:
                    st.info(f"✅ {len(hits)}頭的中 (推奨馬番: {hits})")
                else:
                    st.warning("❌ 的中なし")
                
                st.markdown("---")
