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
                "--jra_year", year,
                "--jra_date_start", start_date_str,
                "--jra_date_end", end_date_str
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
        st.dataframe(df.tail(20), use_container_width=True)
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

tab_train, tab_tune, tab_upload = st.tabs(["🧠 モデル学習", "🧪 パラメータチューニング (Optuna)", "📤 リポジトリ更新"])

# --- Tab 1: Training ---
with tab_train:
    st.markdown("### モデル学習")
    
    # Use best params if available
    use_best_params = False
    if 'best_params' in st.session_state:
        st.success("✅ チューニングされた最適パラメータが利用可能です。")
        use_best_params = st.checkbox("最適パラメータを使用して学習する", value=True)
        if use_best_params:
            st.json(st.session_state['best_params'])
    
    if st.button("🧠 モデルを学習する", type="primary"):
        with st.spinner("学習中..."):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(project_root, "ml", "processed_data.csv")
            model_dir = os.path.join(project_root, "ml", "models")
            os.makedirs(model_dir, exist_ok=True)
            model_path = os.path.join(model_dir, "lgbm_model.pkl")
            
            params = st.session_state['best_params'] if use_best_params else None
            
            if not os.path.exists(data_path):
                st.error(f"データが見つかりません: {data_path}")
            else:
                try:
                    results = train_model.train_and_save_model(data_path, model_path, params=params)
                    if results:
                        st.success("学習完了！")
                        st.session_state['ml_results'] = results
                    else:
                        st.error("学習に失敗しました（データ不足など）。")
                except Exception as e:
                    st.error(f"学習中にエラーが発生しました: {e}")

    if 'ml_results' in st.session_state:
        res = st.session_state['ml_results']
        
        # Metrics
        st.markdown("#### 学習結果")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Accuracy", f"{res['accuracy']:.4f}")
        m_col2.metric("AUC", f"{res['auc']:.4f}")
        m_col3.metric("Positive Rate", f"{res['positive_rate']:.2%}")
        
        # Plots
        st.markdown("#### 詳細分析")
        p_col1, p_col2 = st.columns(2)
        
        with p_col1:
            # Learning Curve
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
                    st.info("学習履歴データがありません。")
            else:
                st.info("学習履歴がありません。")

        with p_col2:
            # Feature Importance
            if 'feature_importance' in res:
                fi = pd.DataFrame(res['feature_importance'])
                if not fi.empty:
                    fig_fi = go.Figure(go.Bar(
                        x=fi['Value'],
                        y=fi['Feature'],
                        orientation='h'
                    ))
                    fig_fi.update_layout(
                        title="特徴量重要度 (Top 20)",
                        yaxis=dict(autorange="reversed"),
                        xaxis_title="Importance (Gain)"
                    )
                    st.plotly_chart(fig_fi, use_container_width=True)
                else:
                    st.info("特徴量重要度がありません。")

# --- Tab 2: Tuning ---
with tab_tune:
    st.markdown("### ハイパーパラメータの自動探索 (Optuna)")
    st.info("AIが様々な設定を試して、精度(AUC)が最も高くなるパラメータを見つけます。")
    
    n_trials = st.slider("試行回数 (多いほど高精度ですが時間がかかります)", 5, 100, 20)
    
    if st.button("🧪 チューニングを開始する"):
        with st.spinner(f"最適化中... {n_trials}回の試行を行います。"):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(project_root, "ml", "processed_data.csv")
            
            try:
                opt_res = train_model.optimize_hyperparameters(data_path, n_trials=n_trials)
                if opt_res:
                    st.success(f"最適化完了！ Best AUC: {opt_res['best_auc']:.4f}")
                    st.session_state['best_params'] = opt_res['best_params']
                    st.json(opt_res['best_params'])
                    st.markdown("👉 **「モデル学習」タブに戻って、このパラメータで再学習してください。**")
                else:
                    st.error("最適化に失敗しました。")
            except Exception as e:
                st.error(f"最適化中にエラーが発生しました: {e}")

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

