import streamlit as st
import subprocess
import os
import sys
import pandas as pd
from datetime import date, datetime
import time


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
