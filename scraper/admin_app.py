import streamlit as st
import subprocess
import os
import sys
import pandas as pd
from datetime import date, datetime

# Set page config
st.set_page_config(page_title="JRA データ管理パネル", layout="wide")

st.title("🏇 JRA スクレイピング管理パネル")
st.markdown("ここでJRA公式サイトからレースデータを取得し、`database.csv` を更新します。")

# --- UI Layout (No Sidebar) ---
st.markdown("### ⚙️ 設定")

col1, col2 = st.columns(2)

with col1:
    year = st.selectbox("対象年", ["2025", "2024"], index=0)

with col2:
    # Date Input
    # Default to today's year range or just generic default
    default_start = date(int(year), 1, 1)
    default_end = date(int(year), 12, 31)
    
    date_range = st.date_input(
        "取得期間 (開始日 - 終了日)",
        value=(default_start, default_start), # Default to single day start for safety or reset
        min_value=date(2020, 1, 1),
        max_value=date(2030, 12, 31)
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

if st.button("🚀 スクレイピング開始 (データ取得)", type="primary"):
    if not start_date_str or not end_date_str:
        st.error("有効な期間を選択してください。")
    else:
        st.info(f"{year}年 {start_date_str} 〜 {end_date_str} のデータ取得を開始します...")
        
        # Placeholder for logs
        log_area = st.empty()
        logs = []
        
        # Command execution
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        cmd = [
            sys.executable, "-u", "scraper/auto_scraper.py", 
            "--jra_year", year,
            "--jra_date_start", start_date_str,
            "--jra_date_end", end_date_str
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=project_root
            )
            
            # Stream logs
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    logs.append(line.strip())
                    # Keep last 20 lines
                    log_text = "\n".join(logs[-20:]) 
                    log_area.code(log_text, language="text")
                    
            if process.returncode == 0:
                st.success("✅ データ取得が完了しました！")
                st.snow()
            else:
                st.error("❌ データ取得に失敗しました。")
                
        except Exception as e:
            st.error(f"実行エラー: {e}")

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
