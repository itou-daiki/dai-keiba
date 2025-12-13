import streamlit as pd_st
import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 日本語フォント設定（環境依存するが、MacならHiragino、なければデフォルト）
# Streamlit Cloud等ではIPAexフォントのインストールが必要だが、
# ローカル実行(Mac)前提ならHiraginoが使えるはず。
try:
    plt.rcParams['font.family'] = 'Hiragino Sans'
except:
    plt.rcParams['font.family'] = 'sans-serif'

st.set_page_config(page_title="競馬データ分析ダッシュボード", layout="wide")

st.title("🏇 競馬データ分析ダッシュボード")

# データ読み込み
CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), "JRA_Results_2024_2025.csv")

@st.cache_data
def load_data():
    if not os.path.exists(CSV_FILE_PATH):
        return None
    df = pd.read_csv(CSV_FILE_PATH)
    return df

df = load_data()

if df is None:
    st.error(f"データファイルが見つかりません: {CSV_FILE_PATH}")
    st.info("まずはスクレイピングを実行してデータを収集してください。")
else:
    # データ前処理
    if '日付' in df.columns:
        df['date_obj'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    
    # サイドバー: フィルタ
    st.sidebar.header("フィルタ")
    
    unique_years = sorted(df['date_obj'].dt.year.unique(), reverse=True) if 'date_obj' in df.columns else []
    selected_year = st.sidebar.selectbox("年を選択", ["All"] + list(unique_years))
    
    if selected_year != "All":
        df_display = df[df['date_obj'].dt.year == selected_year]
    else:
        df_display = df

    # KPI
    col1, col2, col3 = st.columns(3)
    col1.metric("総レース数", len(df_display))
    col2.metric("最新データ日付", df_display['date_obj'].max().strftime('%Y-%m-%d') if not df_display.empty else "-")
    col3.metric("開催場数", df_display['会場'].nunique() if '会場' in df_display.columns else 0)

    # グラフエリア
    st.subheader("📊 開催場別レース数")
    if '会場' in df_display.columns:
        venue_counts = df_display['会場'].value_counts()
        st.bar_chart(venue_counts)

    st.subheader("🏆 重賞グレード割合")
    if '重賞' in df_display.columns:
        # G1, G2, G3, 一般(空白)
        grade_counts = df_display['重賞'].fillna('一般').value_counts()
        st.bar_chart(grade_counts)

    # データテーブル
    st.subheader("📋 最新レース結果")
    st.dataframe(df_display.sort_values('date_obj', ascending=False).head(100))
    
    # ダウンロード
    csv = df_display.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="表示データをCSVでダウンロード",
        data=csv,
        file_name='filtered_race_data.csv',
        mime='text/csv',
    )
