import streamlit as st
import subprocess
import os
import sys
import pandas as pd
from datetime import date, datetime
import time
import plotly.graph_objects as go

# Add ml to path
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
st.markdown("ここでJRA公式サイトからレースデータを取得し、`database.csv` を更新します。")

# --- Session State for Process Management ---
if 'process' not in st.session_state:
    st.session_state.process = None
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

# --- UI Layout (No Sidebar) ---
st.markdown("### ⚙️ 設定")

col1, col2 = st.columns(2)

with col1:
    year = st.selectbox("対象年", ["2025", "2024"], index=0, disabled=st.session_state.is_running)

with col2:
    default_start = date(int(year), 1, 1)
    default_end = date(int(year), 12, 31)
    
    date_range = st.date_input(
        "取得期間 (開始日 - 終了日)",
        value=(default_start, default_start),
        min_value=date(2020, 1, 1),
        max_value=date(2030, 12, 31),
        disabled=st.session_state.is_running
    )

start_date_str = ""
end_date_str = ""

if isinstance(date_range, tuple):
    if len(date_range) == 2:
        start_d, end_d = date_range
        start_date_str = start_d.strftime("%Y-%m-%d")
        end_date_str = end_d.strftime("%Y-%m-%d")
        st.info(f"選択範囲: {start_date_str} 〜 {end_date_str}")
    elif len(date_range) == 1:
        st.warning("終了日を選択してください。")
else:
    st.warning("日付を選択してください。")

st.markdown("---")

col_btn_1, col_btn_2 = st.columns([1, 1])

with col_btn_1:
    if st.button("🚀 スクレイピング開始", type="primary", disabled=st.session_state.is_running):
        if not start_date_str or not end_date_str:
            st.error("有効な期間を選択してください。")
        else:
            st.session_state.is_running = True
            st.session_state.logs = []
            
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cmd = [
                sys.executable, "-u", "scraper/auto_scraper.py", 
                "--start", start_date_str,
                "--end", end_date_str
            ]
            
            try:
                # Use Popen
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=project_root
                )
                st.session_state.process = p
                st.rerun()
                
            except Exception as e:
                st.error(f"実行エラー: {e}")
                st.session_state.is_running = False

with col_btn_2:
    if st.button("🛑 停止", type="secondary", disabled=not st.session_state.is_running):
        if st.session_state.process:
            st.session_state.process.terminate()
            st.session_state.process = None
        st.session_state.is_running = False
        st.error("処理を停止しました。")
        st.rerun()

# --- Log Streaming Area ---
st.markdown("### 📜 実行ログ")
log_container = st.empty()

if st.session_state.is_running and st.session_state.process:
    p = st.session_state.process
    # Read output non-blocking? logic in Streamlit loop is tricky.
    # We loop here reading one line at a time then rerun? No, that hangs UI.
    # Streamlit runs top-down. We can read available lines.
    
    import fcntl
    
    # Set non-blocking
    fd = p.stdout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    try:
        # Read all available
        chunk = p.stdout.read()
        if chunk:
            for line in chunk.splitlines():
                if line:
                    st.session_state.logs.append(line)
    except Exception:
        pass
        
    # Check if finished
    if p.poll() is not None:
        st.session_state.is_running = False
        st.session_state.process = None
        st.success("処理が完了しました！")
        st.rerun()
    else:
        # Rerun to keep updating logs
        time.sleep(0.5)
        st.rerun()

# Display logs
if st.session_state.logs:
    log_text = "\n".join(st.session_state.logs[-20:])
    log_container.code(log_text)

# --- Data Preview ---
st.markdown("### 📊 データベースのプレビュー")
csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.csv")

col_prev_1, col_prev_2 = st.columns([1, 4])
with col_prev_1:
    if st.button("🔄 最新データを読み込む"):
        st.rerun()

if os.path.exists(csv_path):
    try:
        df = pd.read_csv(csv_path)
        st.metric("総データ数 (行)", len(df))
        st.dataframe(df,use_container_width=True)
    except Exception as e:
        st.error(f"database.csv を読み込めませんでした: {e}")
else:
    st.warning("database.csv が見つかりません。")

st.markdown("---")
st.caption("使い方: データ取得後、必ず git で変更をコミット＆プッシュして公開サイトに反映させてください。")

# --- ML Management Section ---
st.markdown("---")
st.markdown("## 🤖 機械学習モデルの管理 (MLOps)")

# MLflow Instructions
with st.expander("ℹ️ MLflow (実験管理) の使い方"):
    st.markdown("""
    実験の履歴（パラメータ、精度、モデル）は **MLflow** で自動記録されています。
    詳細を確認するには、ターミナルで以下のコマンドを実行し、ブラウザで開いてください。
    ```bash
    mlflow ui
    ```
    (デフォルトポート: http://127.0.0.1:5000)
    """)

tab_ml, tab_upload = st.tabs(["🧠 モデル学習 & チューニング", "📤 リポジトリ更新"])

# --- Tab 1: ML (Training & Tuning) ---
with tab_ml:
    st.markdown("### モデル学習の設定")
    
    col_conf_1, col_conf_2 = st.columns(2)
    
    with col_conf_1:
        is_tuning = st.checkbox("ハイパーパラメータ自動チューニング (Optuna) を実行する", value=False)
        
        n_trials = 20
        if is_tuning:
            st.info("AIが最適な設定を探索してから学習を行います。")
            n_trials = st.slider("試行回数", 5, 100, 20)
        else:
            if 'best_params' in st.session_state:
                st.success("✅ 前回チューニングされた最適パラメータを使用して学習します。")
                if st.checkbox("最適パラメータを破棄してデフォルトに戻す"):
                    del st.session_state['best_params']
                    st.rerun()
            else:
                st.info("デフォルト設定で学習します。")

    with col_conf_2:
        st.markdown(f"""
        **実行内容:**
        1. データ前処理 (最新データの反映)
        2. {'チューニング (最適化)' if is_tuning else '設定の確認'}
        3. モデル学習 (LightGBM)
        """)
        
        btn_label = "🧪 チューニング ＆ 学習開始" if is_tuning else "🧠 学習開始"
        start_process = st.button(btn_label, type="primary")

    if start_process:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_path = os.path.join(project_root, "ml", "processed_data.csv")
        db_path = os.path.join(project_root, "database.csv")
        model_dir = os.path.join(project_root, "ml", "models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "lgbm_model.pkl")

        # 1. Preprocess
        with st.spinner("1/3 データ前処理中..."):
            if os.path.exists(db_path):
               feature_engineering.calculate_features(db_path, data_path)
            else:
               st.error("database.csvが見つかりません。")
               st.stop()
        
        # 2. Tuning (if selected)
        if is_tuning:
            with st.spinner(f"2/3 パラメータチューニング中 ({n_trials} trials)..."):
                try:
                    opt_res = train_model.optimize_hyperparameters(data_path, n_trials=n_trials)
                    if opt_res:
                        st.success(f"最適化完了！ Best AUC: {opt_res['best_auc']:.4f}")
                        st.session_state['best_params'] = opt_res['best_params']
                    else:
                        st.error("最適化に失敗しました。デフォルト設定で学習を続行します。")
                except Exception as e:
                     st.error(f"最適化中にエラー: {e}")
        
        # 3. Training
        step_label = "3/3" if is_tuning else "2/2"
        with st.spinner(f"{step_label} モデル学習中..."):
            params = st.session_state.get('best_params', None)
            
            try:
                results = train_model.train_and_save_model(data_path, model_path, params=params)
                if results:
                    st.success("学習完了！")
                    st.session_state['ml_results'] = results
                else:
                    st.error("学習に失敗しました。")
            except Exception as e:
                st.error(f"学習中にエラー: {e}")

    # Display Results
    if 'ml_results' in st.session_state:
        st.markdown("---")
        res = st.session_state['ml_results']
        
        st.markdown("#### 📊 学習結果レポート")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Accuracy", f"{res['accuracy']:.4f}")
        m_col2.metric("AUC", f"{res['auc']:.4f}")
        m_col3.metric("Positive Rate", f"{res['positive_rate']:.2%}")
        
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            if 'evals_result' in res and res['evals_result']:
                evals = res['evals_result']
                if 'train' in evals and 'auc' in evals['train']:
                    fig_lc = go.Figure()
                    fig_lc.add_trace(go.Scatter(y=evals['train']['auc'], mode='lines', name='Train AUC'))
                    if 'valid' in evals and 'auc' in evals['valid']:
                        fig_lc.add_trace(go.Scatter(y=evals['valid']['auc'], mode='lines', name='Valid AUC'))
                    fig_lc.update_layout(title="学習曲線 (AUC)", xaxis_title="Rounds", yaxis_title="AUC")
                    st.plotly_chart(fig_lc, use_container_width=True)
            else:
                st.info("学習履歴なし")

        with p_col2:
            if 'feature_importance' in res:
                fi = pd.DataFrame(res['feature_importance'])
                if not fi.empty:
                    fig_fi = go.Figure(go.Bar(
                        x=fi['Value'], y=fi['Feature'], orientation='h'
                    ))
                    fig_fi.update_layout(
                        title="特徴量重要度 (Top 20)",
                        yaxis=dict(autorange="reversed"),
                        xaxis_title="Importance (Gain)"
                    )
                    st.plotly_chart(fig_fi, use_container_width=True)
            else:
                st.info("特徴量重要度なし")



# --- Tab 3: Upload ---
with tab_upload:
    st.markdown("### リポジトリへアップロード")
    st.warning("⚠️ Gitの設定（SSH鍵など）がサーバー上で正しく行われている必要があります。")
    
    commit_msg = st.text_input("コミットメッセージ", value=f"Update model: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    if st.button("📤 モデルをアップロード (Git Push)"):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path_rel = "ml/models/lgbm_model.pkl" # Relative to root
        
        cmds = [
            ["git", "add", model_path_rel],
            ["git", "commit", "-m", commit_msg],
            ["git", "push", "origin", "main"] # Start with main
        ]
        
        st.markdown("#### 実行ログ")
        status_area = st.empty()
        
        all_success = True
        for cmd in cmds:
            try:
                result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
                if result.returncode == 0:
                    status_area.success(f"OK: {' '.join(cmd)}")
                else:
                    # git commit returns 1 if nothing to commit, which is fine-ish but we should warn
                    if "nothing to commit" in result.stdout:
                         status_area.info(f"Info: {result.stdout}")
                    else:
                        status_area.error(f"Error: {' '.join(cmd)}\n{result.stderr}")
                        all_success = False
                        break
            except Exception as e:
                status_area.error(f"Command failed: {e}")
                all_success = False
                break
        
        if all_success:
            st.success("✅ アップロード完了！")

