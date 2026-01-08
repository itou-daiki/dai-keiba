import json
import os

def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def create_notebook(cells):
    return json.dumps({
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"codemirror_mode": {"name": "ipython", "version": 3}, "file_extension": ".py", "mimetype": "text/x-python", "name": "python", "nbconvert_exporter": "python", "pygments_lexer": "ipython3", "version": "3.8.10"}
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }, indent=1, ensure_ascii=False)

def gen_jra_scraping_nb():
    jra_code = read_file('scripts/scraping_logic_v2.py')
    
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🏇 JRA 全レース取得 (2020-2026)\n", "以下の設定変数を変更して実行してください。**Netkeiba.com** から指定した期間のデータを取得し、`TARGET_CSV` に保存します。"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Driveをマウントする場合のみ実行してください\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 設定 (ここを変更してください)\n",
            "YEAR = 2025          # 対象年度 (例: 2024)\n",
            "START_MONTH = 1      # 開始月 (1-12)\n",
            "END_MONTH = 12       # 終了月 (1-12)\n",
            "SAVE_DIR = '/content/drive/MyDrive/dai-keiba/data/raw' # 保存先フォルダ\n",
            "TARGET_CSV = 'database.csv'\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": jra_code.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 実行ブロック\n",
            "import os\n",
            "import pandas as pd\n",
            "from datetime import date, timedelta\n",
            "import calendar\n",
            "import requests\n",
            "from bs4 import BeautifulSoup\n",
            "import time\n",
            "from tqdm.auto import tqdm\n",
            "import re\n",
            "\n",
            "if YEAR:\n",
            "    # Saveディレクトリの作成\n",
            "    os.makedirs(SAVE_DIR, exist_ok=True)\n",
            "    \n",
            "    s_date = date(int(YEAR), int(START_MONTH), 1)\n",
            "    last_day = calendar.monthrange(int(YEAR), int(END_MONTH))[1]\n",
            "    e_date = date(int(YEAR), int(END_MONTH), last_day)\n",
            "    \n",
            "    # 未来の日付は検索しないように制限\n",
            "    today = date.today()\n",
            "    if e_date > today:\n",
            "        e_date = today\n",
            "    \n",
            "    save_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
            "    print(f'{YEAR}年のデータを {s_date} から {e_date} まで取得します(Netkeiba参照)...')\n",
            "    print(f'保存先: {save_path}')\n",
            "    \n",
            "    # 安全な追記関数\n",
            "    def safe_append_csv(df_chunk, path):\n",
            "        if not os.path.exists(path):\n",
            "            df_chunk.to_csv(path, index=False)\n",
            "        else:\n",
            "            try:\n",
            "                existing_cols = pd.read_csv(path, nrows=0).columns.tolist()\n",
            "                df_aligned = df_chunk.reindex(columns=existing_cols)\n",
            "                df_aligned.to_csv(path, mode='a', header=False, index=False)\n",
            "            except Exception as e:\n",
            "                print(f\"Save Error: {e}\")\n",
            "\n",
            "    # 月ごとにループ\n",
            "    for m in range(int(START_MONTH), int(END_MONTH) + 1):\n",
            "        m_start = date(int(YEAR), m, 1)\n",
            "        m_last = calendar.monthrange(int(YEAR), m)[1]\n",
            "        m_end = date(int(YEAR), m, m_last)\n",
            "        \n",
            "        if m_end < s_date or m_start > e_date:\n",
            "            continue\n",
            "            \n",
            "        curr_s = max(m_start, s_date)\n",
            "        curr_e = min(m_end, e_date)\n",
            "        if curr_s > curr_e: continue\n",
            "        \n",
            "        days = []\n",
            "        c = curr_s\n",
            "        while c <= curr_e:\n",
            "            days.append(c)\n",
            "            c += timedelta(days=1)\n",
            "            \n",
            "        print(f'\\n📅 {YEAR}/{m:02} を取得中...')\n",
            "        print(f'  {len(days)} 日分の日付対象')\n",
            "\n",
            "        for d in tqdm(days, desc=f'  {YEAR}/{m:02}'):\n",
            "            d_str = d.strftime('%Y%m%d')\n",
            "            # JRA (Netkeiba) URL\n",
            "            url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={d_str}'\n",
            "            daily_data = []\n",
            "            try:\n",
            "                time.sleep(0.5)\n",
            "                headers = {'User-Agent': 'Mozilla/5.0'}\n",
            "                resp = requests.get(url, headers=headers)\n",
            "                resp.encoding = 'EUC-JP'\n",
            "                soup = BeautifulSoup(resp.text, 'html.parser')\n",
            "                \n",
            "                links = soup.select('a[href*=\"race/result.html\"]')\n",
            "                if links:\n",
            "                    for link in links:\n",
            "                        href = link.get('href')\n",
            "                        if href.startswith('../'):\n",
            "                             full_url = f'https://race.netkeiba.com/{href.replace(\"../\", \"\")}'\n",
            "                        elif href.startswith('http'):\n",
            "                             full_url = href\n",
            "                        else:\n",
            "                             full_url = f'https://race.netkeiba.com{href}'\n",
            "\n",
            "                        rid_match = re.search(r'race_id=(\d+)', full_url)\n",
            "                        if rid_match:\n",
            "                            rid = rid_match.group(1)\n",
            "                            # JRA race IDs are 12 digits (YYYYJJRRDDNN) same as Netkeiba DB\n",
            "                            db_url = f\"https://db.netkeiba.com/race/{rid}/\"\n",
            "                            try:\n",
            "                                df = scrape_race_rich(db_url, existing_race_ids=None)\n",
            "                                if df is not None and not df.empty:\n",
            "                                    daily_data.append(df)\n",
            "                                time.sleep(1)\n",
            "                            except Exception as e_race:\n",
            "                                pass\n",
            "\n",
            "                if daily_data:\n",
            "                    df_day = pd.concat(daily_data, ignore_index=True)\n",
            "                    safe_append_csv(df_day, save_path)\n",
            "                    del daily_data\n",
            "                    del df_day\n",
            "                    import gc\n",
            "                    gc.collect()\n",
            "            \n",
            "            except Exception as e_day:\n",
            "                print(f'  日付処理エラー {d}: {e_day}')\n",
            "\n",
            "    print('完了しました。')\n",
            "else:\n",
            "    print('年度が設定されていません。')\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# データ整理・重複削除・カラム順序保証\n",
             "import pandas as pd\n",
             "import os\n",
             "\n",
             "save_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
             "if os.path.exists(save_path):\n",
             "    print('データの整理を行っています...')\n",
             "    try:\n",
             "        # 全カラムを文字列として読み込み（型ずれ防止）\n",
             "        df_final = pd.read_csv(save_path, dtype=str)\n",
             "        before_len = len(df_final)\n",
             "        if 'race_id' in df_final.columns and 'horse_id' in df_final.columns:\n",
             "            df_final.drop_duplicates(subset=['race_id', 'horse_id'], keep='last', inplace=True)\n",
             "        after_len = len(df_final)\n",
             "        print(f'重複削除: {before_len} -> {after_len} ({before_len - after_len}件削除)')\n",
             "        df_final.to_csv(save_path, index=False)\n",
             "        print('完了: データの整合性を確認し保存しました。')\n",
             "    except Exception as e:\n",
             "        print(f'データ整理中にエラーが発生しました: {e}')\n"
        ]}
    ]
    return create_notebook(cells)

def gen_jra_backfill_nb():
    cleanup_code = read_file('scripts/colab_backfill_helper.py')
    race_scraper_code = read_file('scraper/race_scraper.py')
    
    helper_lines = cleanup_code.splitlines()
    filtered_helper = []
    for line in helper_lines:
        if "from scraper.race_scraper import RaceScraper" in line:
            filtered_helper.append("    pass # Replaced import")
            continue
        if "sys.path.append" in line: continue
        filtered_helper.append(line)
        
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🛠️ JRA データ補完ツール\n", "欠損している血統情報および過去走履歴を補完します。"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Driveをマウントする場合のみ実行してください\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": race_scraper_code.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [l + "\n" for l in filtered_helper]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 設定\n",
            "DATA_DIR = '/content/drive/MyDrive/dai-keiba/data/raw' # CSVがあるフォルダ\n",
            "\n",
            "# 実行ブロック\n",
            "csv_path = os.path.join(DATA_DIR, 'database.csv')\n",
            "if os.path.exists(csv_path):\n",
            "    print(f'処理対象: {csv_path}')\n",
            "    fill_bloodline_data(csv_path, mode='JRA')\n",
            "    fill_history_data(csv_path, mode='JRA')\n",
            "    fill_race_metadata(csv_path, mode='JRA')\n",
            "else:\n",
            "    print(f'{csv_path} が見つかりません。')\n",
            "    print(f'現在のディレクトリ: {os.getcwd()}')\n",
            "    if os.path.exists(DATA_DIR):\n",
            "        print(f'{DATA_DIR} の中身: {os.listdir(DATA_DIR)}')\n",
            "    else:\n",
            "        print(f'{DATA_DIR} ディレクトリ自体が存在しません。')"
        ]}
    ]
    return create_notebook(cells)

def gen_nar_scraping_nb():
    # Similar to JRA, but using NAR logic and separate saving logic
    # We will reuse the code style
    
    race_scraper_code = read_file('scraper/race_scraper.py')
    jra_code = read_file('scripts/scraping_logic_v2.py') # Use V2 for NAR too
    
    # We define run_nar_scraping with month support
    nar_execution_logic = """
def run_nar_scraping(year, start_month=1, end_month=12, save_dir='data/raw', target_csv='database_nar.csv'):
    # This function is now embedded in the notebook directly in the NAR execution cell below
    pass
""" 

    # Since we can't easily inline the full logic without a clean file, 
    # and previous step used a placeholder, I will update the placeholder 
    # to accept the month inputs and print them, or use the iter logic previously defined but bounded.
    
    cells = [
         {"cell_type": "markdown", "metadata": {}, "source": ["# 🏇 NAR 全レース取得\n", "以下の設定変数を変更して実行してください。NAR（地方競馬）のデータを日付順に取得します。"]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# Google Driveをマウントする場合のみ実行してください\n",
             "from google.colab import drive\n",
             "drive.mount('/content/drive')"
         ]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 設定 (ここを変更してください)\n",
            "YEAR = 2025          # 対象年度\n",
            "START_MONTH = 1      # 開始月\n",
            "END_MONTH = 12       # 終了月\n",
            "SAVE_DIR = '/content/drive/MyDrive/dai-keiba/data/raw' # 保存先フォルダ\n",
            "TARGET_CSV = 'database_nar.csv'\n"
         ]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": race_scraper_code.splitlines(keepends=True)},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": jra_code.splitlines(keepends=True)},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# NAR スクレイピングロジック\n",
             "import requests\n",
             "from bs4 import BeautifulSoup\n",
             "import pandas as pd\n",
             "import re\n",
             "from datetime import date, timedelta\n",
             "import calendar\n",
             "import time\n",
             "import os\n",
             "\n",
             "def run_nar_scraping(year, start_month=1, end_month=12, save_dir='data/raw', target_csv='database_nar.csv'):\n",
             "    from tqdm.auto import tqdm\n",
             "    \n",
             "    s_date = date(int(year), int(start_month), 1)\n",
             "    last_day_e = calendar.monthrange(int(year), int(end_month))[1]\n",
             "    e_date = date(int(year), int(end_month), last_day_e)\n",
             "    \n",
             "    today = date.today()\n",
             "    if e_date > today: e_date = today\n",
             "    \n",
             "    print(f'NARデータを {s_date} から {e_date} まで取得します...')\n",
             "    print(f'保存先: {os.path.join(save_dir, target_csv)}')\n",
             "    \n",
             "    # 月ごとにループ\n",
             "    for m in range(int(start_month), int(end_month) + 1):\n",
             "        # その月の日付範囲を決定\n",
             "        m_start = date(int(year), m, 1)\n",
             "        m_last = calendar.monthrange(int(year), m)[1]\n",
             "        m_end = date(int(year), m, m_last)\n",
             "        \n",
             "        # 範囲外ならスキップ\n",
             "        if m_end < s_date or m_start > e_date:\n",
             "            continue\n",
             "            \n",
             "        # 実際の開始・終了（クランプ）\n",
             "        curr_s = max(m_start, s_date)\n",
             "        curr_e = min(m_end, e_date)\n",
             "        \n",
             "        if curr_s > curr_e: continue\n",
             "        \n",
             "        # 日付リスト作成\n",
             "        days = []\n",
             "        c = curr_s\n",
             "        while c <= curr_e:\n",
             "            days.append(c)\n",
             "            c += timedelta(days=1)\n",
             "            \n",
             "        print(f'\\n📅 {year}/{m:02} を取得中...')\n",
             "        print(f'  {len(days)} 日分の日付対象')\n",
             "        \n",
             "        for d in tqdm(days, desc=f'  {year}/{m:02}'):\n",
             "            d_str = d.strftime('%Y%m%d')\n",
             "            url = f'https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date={d_str}'\n",
             "            \n",
             "            daily_data = [] # 1日分のデータを貯める\n",
             "            \n",
             "            try:\n",
             "                 time.sleep(0.5)\n",
             "                 headers = {'User-Agent': 'Mozilla/5.0'}\n",
             "                 resp = requests.get(url, headers=headers)\n",
             "                 resp.encoding = 'EUC-JP'\n",
             "                 soup = BeautifulSoup(resp.text, 'html.parser')\n",
             "                 links = soup.select('a[href*=\"race/result.html\"]')\n",
             "                 \n",
             "                 if links:\n",
             "                     # print(f'  {d}: {len(links)} レース') # ログ過多防止のためコメントアウト\n",
             "                     for link in links:\n",
             "                         href = link.get('href')\n",
             "                         if href.startswith('../'):\n",
             "                             full_url = f'https://nar.netkeiba.com/{href.replace(\"../\", \"\")}'\n",
             "                         elif href.startswith('http'):\n",
             "                             full_url = href\n",
             "                         else:\n",
             "                             full_url = f'https://nar.netkeiba.com{href}'\n",
             "                         \n",
             "                         try:\n",
             "                             df = scrape_race_rich(full_url, existing_race_ids=None)\n",
             "                             if df is not None and not df.empty:\n",
             "                                 daily_data.append(df)\n",
             "                             time.sleep(1)\n",
             "                         except Exception as e_race:\n",
             "                             pass # エラーは無視して次へ\n",
             "                 \n",
             "                 # 1日分のループ終了後、まとめて保存\n",
             "                 if daily_data:\n",
             "                     os.makedirs(save_dir, exist_ok=True)\n",
             "                     csv_file = os.path.join(save_dir, target_csv)\n",
             "                     try:\n",
             "                         df_day = pd.concat(daily_data, ignore_index=True)\n",
             "                         \n",
             "                         if not os.path.exists(csv_file):\n",
             "                             df_day.to_csv(csv_file, index=False)\n",
             "                         else:\n",
             "                             existing_cols = pd.read_csv(csv_file, nrows=0).columns.tolist()\n",
             "                             df_aligned = df_day.reindex(columns=existing_cols)\n",
             "                             df_aligned.to_csv(csv_file, mode='a', header=False, index=False)\n",
             "                     except Exception as e_save:\n",
             "                          print(f\"  保存エラー ({d}): {e_save}\")\n",
             "                     \n",
             "                     # メモリ解放\n",
             "                     del daily_data\n",
             "                     import gc\n",
             "                     gc.collect()\n",
             "            \n",
             "            except Exception as e_day:\n",
             "                print(f'  日付処理エラー {d}: {e_day}')\n",
             "    \n",
             "    print('完了しました。')\n"
         ]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# 実行ブロック\n",
             "if YEAR:\n",
             "    # ディレクトリ作成\n",
             "    os.makedirs(SAVE_DIR, exist_ok=True)\n",
             "    run_nar_scraping(YEAR, START_MONTH, END_MONTH, save_dir=SAVE_DIR, target_csv=TARGET_CSV)\n"
         ]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# データ整理・重複削除・カラム順序保証 (NAR)\n",
             "import pandas as pd\n",
             "import os\n",
             "\n",
             "csv_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
             "if os.path.exists(csv_path):\n",
             "    print('データの整理を行っています...')\n",
             "    try:\n",
             "        # 全カラムを文字列として読み込み（型ずれ防止）\n",
             "        df_final = pd.read_csv(csv_path, dtype=str)\n",
             "        before_len = len(df_final)\n",
             "        if 'race_id' in df_final.columns and 'horse_id' in df_final.columns:\n",
             "            df_final.drop_duplicates(subset=['race_id', 'horse_id'], keep='last', inplace=True)\n",
             "        after_len = len(df_final)\n",
             "        print(f'重複削除: {before_len} -> {after_len} ({before_len - after_len}件削除)')\n",
             "        df_final.to_csv(save_path, index=False)\n",
             "        print('完了: データの整合性を確認し保存しました。')\n",
             "    except Exception as e:\n",
             "        print(f'データ整理中にエラーが発生しました: {e}')\n"
         ]}
    ]
    return create_notebook(cells)

def gen_nar_backfill_nb():
    # Similar to JRA backfill but NAR file
    cleanup_code = read_file('scripts/colab_backfill_helper.py')
    race_scraper_code = read_file('scraper/race_scraper.py')
    
    helper_lines = cleanup_code.splitlines()
    filtered_helper = []
    for line in helper_lines:
        if "from scraper.race_scraper import RaceScraper" in line:
            filtered_helper.append("    pass # Replaced import")
            continue
        if "sys.path.append" in line: continue
        filtered_helper.append(line)
        
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🛠️ NAR データ補完ツール"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Driveをマウントする場合のみ実行してください\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": race_scraper_code.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [l + "\n" for l in filtered_helper]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 設定\n",
            "DATA_DIR = '/content/drive/MyDrive/dai-keiba/data/raw' # CSVがあるフォルダ\n",
            "\n",
            "# 実行ブロック\n",
            "csv_path = os.path.join(DATA_DIR, 'database_nar.csv')\n",
            "if os.path.exists(csv_path):\n",
            "    print(f'処理対象: {csv_path}')\n",
            "    fill_bloodline_data(csv_path, mode='NAR')\n",
            "    fill_history_data(csv_path, mode='NAR')\n",
            "    fill_race_metadata(csv_path, mode='NAR')\n",
            "else:\n",
            "    print(f'{csv_path} が見つかりません。')\n",
            "    print(f'現在のディレクトリ: {os.getcwd()}')\n",
            "    if os.path.exists(DATA_DIR):\n",
            "        print(f'{DATA_DIR} の中身: {os.listdir(DATA_DIR)}')\n",
            "    else:\n",
            "        print(f'{DATA_DIR} ディレクトリ自体が存在しません。')"
        ]}
    ]
    return create_notebook(cells)

if __name__ == "__main__":
    os.makedirs('notebooks', exist_ok=True)
    
    with open('notebooks/Colab_JRA_Scraping.ipynb', 'w') as f:
        f.write(gen_jra_scraping_nb())
        
    with open('notebooks/Colab_JRA_Backfill.ipynb', 'w') as f:
        f.write(gen_jra_backfill_nb())
        
    with open('notebooks/Colab_NAR_Backfill.ipynb', 'w') as f:
        f.write(gen_nar_backfill_nb())
        
    # NAR Scraping logic reuse
    with open('notebooks/Colab_NAR_Scraping.ipynb', 'w') as f:
        f.write(gen_nar_scraping_nb())
