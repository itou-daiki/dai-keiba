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
st.write("取得対象期間を指定してください。指定しない場合は自動で続きから取得します。")

# Default dates
default_start = last_date.date() + pd.Timedelta(days=1) if last_date else datetime(2025, 12, 1).date()
default_end = datetime.now().date()

col_d1, col_d2 = st.columns(2)
start_date = col_d1.date_input("開始日", value=default_start)
end_date = col_d2.date_input("終了日", value=default_end)

if st.button("スクレイピングを実行して更新", type="primary"):
    status_area = st.empty()
    log_area = st.empty()
    
    # Capture stdout to show logs in Streamlit
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        # Run scraper
        with st.spinner(f"スクレイピング実行中... ({start_date} ~ {end_date})"):
            try:
                # auto_scraper.main() now accepts arguments
                
                # We do NOT need to hack sys.argv anymore because we refactored auto_scraper
                # But to be safe, we pass arg list to main
                
                # Call main with explicit dates
                # Convert date objects to datetime for auto_scraper compatibility if needed
                # auto_scraper expects datetime objects or strings
                
                # Define callback
                def progress_update(msg):
                    status_area.text(f"【進捗】 {msg}")
                
                auto_scraper.main(
                    start_date_arg=datetime.combine(start_date, datetime.min.time()),
                    end_date_arg=datetime.combine(end_date, datetime.min.time()),
                    progress_callback=progress_update
                )
                
                st.success("更新完了！")
            except Exception as e:
                st.error(f"実行中にエラーが発生しました: {e}")
                # Print stacktrace for debugging
                import traceback
                traceback.print_exc()
                
    # Show logs
    logs = f.getvalue()
    log_area.code(logs)
    
    # Reload info
    time.sleep(1)
    st.rerun()

# --- Today's Races Section ---
st.subheader("今日のレース情報 (GitHub Pages用)")
st.write("今日の出馬表とオッズを取得し、Webアプリ用のJSONを作成します。")
if st.button("今日のレース情報を更新", type="secondary"):
    with st.spinner("取得中..."):
        success, msg = auto_scraper.scrape_todays_schedule()
        if success:
            st.success(f"完了: {msg}")
        else:
            st.error(f"エラー: {msg}")

# --- Preview Section ---
if count > 0:
    st.subheader("データベースプレビュー (最新20件)")
    df = pd.read_csv(DB_PATH)
    if '日付' in df.columns:
         df['date_obj'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
         st.dataframe(df.sort_values('date_obj', ascending=False).head(20))
    else:
        st.dataframe(df.tail(20))
