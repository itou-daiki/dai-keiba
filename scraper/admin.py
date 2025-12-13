import streamlit as st
import pandas as pd
import os
import sys
import time
from datetime import datetime

# Add scraper directory to path so we can import auto_scraper
sys.path.append(os.path.dirname(__file__))
import auto_scraper

st.set_page_config(page_title="競馬データ管理者ダッシュボード", layout="wide")

st.title("🛠️ 競馬データ管理者ダッシュボード")

# Database Path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")

def get_db_info():
    if not os.path.exists(DB_PATH):
        return None, 0, "ファイルなし"
    
    try:
        df = pd.read_csv(DB_PATH)
        if '日付' in df.columns:
            df['date_obj'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
            last_date = df['date_obj'].max()
            records = len(df)
            return last_date, records, "正常"
    except Exception as e:
        return None, 0, f"エラー: {e}"
    return None, 0, "データなし"

# --- Status Section ---
st.subheader("現在のデータ状態")
last_date, count, status = get_db_info()

col1, col2, col3 = st.columns(3)
col1.metric("総レコード数", f"{count} 件")
col2.metric("最終データ日時", last_date.strftime('%Y-%m-%d') if last_date else "-")
col3.metric("ステータス", status)

if last_date:
    st.info(f"最終更新データ: {last_date.strftime('%Y年%m月%d日')} のレースまで取得済みです。")

# --- Update Section ---
st.subheader("データ更新")
st.write("netkeiba.comから最新データを取得し、データベースを更新します。")

if st.button("スクレイピングを実行して更新", type="primary"):
    status_area = st.empty()
    log_area = st.empty()
    
    # Capture stdout to show logs in Streamlit
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        # Run scraper
        with st.spinner("スクレイピング実行中..."):
            try:
                # auto_scraper.main() calls sys.exit() or runs indefinitely? 
                # We need to make sure it doesn't kill streamlit.
                # Modified auto_scraper to be importable.
                
                # We can call main() but we need to ensure it doesn't handle args if called directly,
                # or we can pass args manually if modified to accept them.
                # Currently auto_scraper.main() calls get_start_params() which parses sys.argv.
                # We should clear sys.argv to avoid streamlit args interfering.
                old_argv = sys.argv
                sys.argv = ["auto_scraper.py"] # Reset args
                
                auto_scraper.main()
                
                sys.argv = old_argv # Restore
                
                st.success("更新完了！")
            except Exception as e:
                st.error(f"実行中にエラーが発生しました: {e}")
                
    # Show logs
    logs = f.getvalue()
    log_area.code(logs)
    
    # Reload info
    time.sleep(1)
    st.rerun()

# --- Preview Section ---
if count > 0:
    st.subheader("データベースプレビュー (最新20件)")
    df = pd.read_csv(DB_PATH)
    if '日付' in df.columns:
         df['date_obj'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
         st.dataframe(df.sort_values('date_obj', ascending=False).head(20))
    else:
        st.dataframe(df.tail(20))
