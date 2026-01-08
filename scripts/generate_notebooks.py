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
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🏇 JRA 全レース取得 (Smart Differential)\n", "設定変数を変更して実行してください。**すでに取得済みで正当性が確認されたレースはスキップ**し、未取得またはデータ不備のあるレースのみ取得します。"]},
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
            "SAVE_DIR = '/content/drive/MyDrive/dai-keiba/data/raw' # 保存先\n",
            "TARGET_CSV = 'database.csv'\n",
            "TARGET_ID_CSV = 'race_ids.csv' # 取得済みレースIDリスト（高速化用）\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": jra_code.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 実行ブロック (Smart Differential Logic)\n",
            "import os\n",
            "import pandas as pd\n",
            "from datetime import date, timedelta\n",
            "import calendar\n",
            "import requests\n",
            "from bs4 import BeautifulSoup\n",
            "import time\n",
            "from tqdm.auto import tqdm\n",
            "import re\n",
            "import gc\n",
            "\n",
            "def check_integrity(df_chunk):\n",
            "    # 必須カラムチェック (馬名、騎手、着順、日付)\n",
            "    # 欠損があれば「不完全」とみなして再取得対象とする\n",
            "    CRITICAL_COLS = ['race_id', 'horse_id', 'horse_name', 'jockey', 'date', 'rank']\n",
            "    if not all(col in df_chunk.columns for col in CRITICAL_COLS):\n",
            "        return False\n",
            "    # Check for NaNs (excl. specific cases like cancelled? For now strict check)\n",
            "    if df_chunk[CRITICAL_COLS].isnull().any().any():\n",
            "        return False\n",
            "    return True\n",
            "\n",
            "if YEAR:\n",
            "    os.makedirs(SAVE_DIR, exist_ok=True)\n",
            "    s_date = date(int(YEAR), int(START_MONTH), 1)\n",
            "    last_day = calendar.monthrange(int(YEAR), int(END_MONTH))[1]\n",
            "    e_date = date(int(YEAR), int(END_MONTH), last_day)\n",
            "    today = date.today()\n",
            "    if e_date > today: e_date = today\n",
            "    \n",
            "    save_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
            "    id_path = os.path.join(SAVE_DIR, TARGET_ID_CSV)\n",
            "    \n",
            "    print(f'{YEAR}年のデータを {s_date} から {e_date} まで取得します(差分更新)...')\n",
            "    print(f'データ: {save_path}')\n",
            "    print(f'ID管理: {id_path}')\n",
            "    \n",
            "    # --- 1. 取得済みリストの初期化 ---\n",
            "    verified_ids = set()\n",
            "    if os.path.exists(id_path):\n",
            "        try:\n",
            "            df_ids = pd.read_csv(id_path, dtype=str)\n",
            "            if 'race_id' in df_ids.columns:\n",
            "                verified_ids = set(df_ids['race_id'].unique())\n",
            "            print(f\"📖 IDリスト読み込み完了: {len(verified_ids)}件\")\n",
            "        except: pass\n",
            "            \n",
            "    # IDリストが無い、または少ない場合、本体DBから復元チェック\n",
            "    if os.path.exists(save_path):\n",
            "        print(\"🔍 既存データの整合性をチェック中...\")\n",
            "        try:\n",
            "            # Chunkで読むと遅いので、型指定して一括で読む（Colabならメモリいける前提、無理ならChunk）\n",
            "            # ここでは安全のためChunk処理はせず、一括でチェック\n",
            "            df_exist = pd.read_csv(save_path, dtype=str)\n",
            "            groups = df_exist.groupby('race_id')\n",
            "            new_valid = []\n",
            "            for rid, group in tqdm(groups, desc='Checking DB'):\n",
            "                if rid in verified_ids: continue\n",
            "                if check_integrity(group):\n",
            "                    verified_ids.add(rid)\n",
            "                    new_valid.append(rid)\n",
            "            \n",
            "            if new_valid:\n",
            "                print(f\"✨ {len(new_valid)}件の有効データをIDリストに追加します\")\n",
            "                mode = 'a' if os.path.exists(id_path) else 'w'\n",
            "                pd.DataFrame({'race_id': new_valid}).to_csv(id_path, mode=mode, header=(not os.path.exists(id_path)), index=False)\n",
            "        except Exception as e:\n",
            "            print(f\"⚠️ 既存データ読み込みエラー: {e} (全件再チェックします)\")\n",
            "\n",
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
            "    # --- 2. スクレイピングループ ---\n",
            "    for m in range(int(START_MONTH), int(END_MONTH) + 1):\n",
            "        m_start = date(int(YEAR), m, 1)\n",
            "        m_last = calendar.monthrange(int(YEAR), m)[1]\n",
            "        m_end = date(int(YEAR), m, m_last)\n",
            "        if m_end < s_date or m_start > e_date: continue\n",
            "        curr_s, curr_e = max(m_start, s_date), min(m_end, e_date)\n",
            "        if curr_s > curr_e: continue\n",
            "        \n",
            "        days = []\n",
            "        c = curr_s\n",
            "        while c <= curr_e:\n",
            "            days.append(c)\n",
            "            c += timedelta(days=1)\n",
            "            \n",
            "        print(f'\\n📅 {YEAR}/{m:02} を処理中...')\n",
            "        for d in tqdm(days, desc=f'  {YEAR}/{m:02}'):\n",
            "            d_str = d.strftime('%Y%m%d')\n",
            "            url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={d_str}'\n",
            "            daily_data_to_save = []\n",
            "            daily_ids_to_save = []\n",
            "            \n",
            "            # --- URL取得 ---\n",
            "            try:\n",
            "                time.sleep(0.5)\n",
            "                headers = {'User-Agent': 'Mozilla/5.0'}\n",
            "                resp = requests.get(url, headers=headers)\n",
            "                resp.encoding = 'EUC-JP'\n",
            "                soup = BeautifulSoup(resp.text, 'html.parser')\n",
            "                links = soup.select('a[href*=\"race/result.html\"]')\n",
            "                \n",
            "                if not links: continue\n",
            "                \n",
            "                unique_urls = []\n",
            "                seen_rids = set()\n",
            "                for link in links:\n",
            "                    href = link.get('href')\n",
            "                    if href.startswith('../'): full_url = f'https://race.netkeiba.com/{href.replace(\"../\", \"\")}'\n",
            "                    elif href.startswith('http'): full_url = href\n",
            "                    else: full_url = f'https://race.netkeiba.com{href}'\n",
            "                    \n",
            "                    rid_match = re.search(r'race_id=(\d+)', full_url)\n",
            "                    if rid_match:\n",
            "                        rid = rid_match.group(1)\n",
            "                        if rid not in seen_rids:\n",
            "                            unique_urls.append((rid, f\"https://db.netkeiba.com/race/{rid}/\"))\n",
            "                            seen_rids.add(rid)\n",
            "                \n",
            "                # --- IDチェック & 取得 ---\n",
            "                for rid, db_url in unique_urls:\n",
            "                    if rid in verified_ids:\n",
            "                        continue # Skip valid race\n",
            "                        \n",
            "                    # Scrape\n",
            "                    try:\n",
            "                        df = scrape_race_rich(db_url, existing_race_ids=None)\n",
            "                        if df is not None and not df.empty:\n",
            "                            # Check Integrity of NEW data\n",
            "                            if check_integrity(df):\n",
            "                                daily_data_to_save.append(df)\n",
            "                                daily_ids_to_save.append(rid)\n",
            "                                verified_ids.add(rid)\n",
            "                        time.sleep(1)\n",
            "                    except Exception: pass\n",
            "                \n",
            "                # --- 保存 ---\n",
            "                if daily_data_to_save:\n",
            "                    df_day = pd.concat(daily_data_to_save, ignore_index=True)\n",
            "                    safe_append_csv(df_day, save_path)\n",
            "                    \n",
            "                    # ID Cache Update\n",
            "                    mode = 'a' if os.path.exists(id_path) else 'w'\n",
            "                    pd.DataFrame({'race_id': daily_ids_to_save}).to_csv(id_path, mode=mode, header=(not os.path.exists(id_path)), index=False)\n",
            "                    \n",
            "                    del daily_data_to_save\n",
            "                    del df_day\n",
            "                    if len(daily_ids_to_save) > 0:\n",
            "                        print(f\"    Saved {len(daily_ids_to_save)} new races.\")\n",
            "                    gc.collect()\n",
            "                    \n",
            "            except Exception as e_day:\n",
            "                print(f'  Err {d}: {e_day}')\n",
            "    print('完了しました。')\n",
            "else:\n",
            "    print('年度が設定されていません。')\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# 一応の最終整理（重複削除）\n",
             "import pandas as pd\n",
             "import os\n",
             "save_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
             "if os.path.exists(save_path):\n",
             "    print('最終整理中...')\n",
             "    try:\n",
             "        df_final = pd.read_csv(save_path, dtype=str)\n",
             "        df_final.drop_duplicates(subset=['race_id', 'horse_id'], keep='last', inplace=True)\n",
             "        df_final.to_csv(save_path, index=False)\n",
             "        print('完了')\n",
             "    except Exception: pass\n"
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
            "    print(f'{csv_path} が見つかりません。')\n"
        ]}
    ]
    return create_notebook(cells)

def gen_nar_scraping_nb():
    race_scraper_code = read_file('scraper/race_scraper.py')
    jra_code = read_file('scripts/scraping_logic_v2.py') # Use V2 for NAR too
    
    cells = [
         {"cell_type": "markdown", "metadata": {}, "source": ["# 🏇 NAR 全レース取得 (Smart Differential)\n", "設定変数を変更して実行してください。**すでに取得済みで正当性が確認されたレースはスキップ**し、未取得またはデータ不備のあるレースのみ取得します。"]},
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
            "SAVE_DIR = '/content/drive/MyDrive/dai-keiba/data/raw' # 保存先\n",
            "TARGET_CSV = 'database_nar.csv'\n",
            "TARGET_ID_CSV = 'race_ids_nar.csv' # 取得済みレースIDリスト\n"
         ]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": race_scraper_code.splitlines(keepends=True)},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": jra_code.splitlines(keepends=True)},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# NAR スクレイピングロジック (Smart Differential)\n",
             "import requests\n",
             "from bs4 import BeautifulSoup\n",
             "import pandas as pd\n",
             "import re\n",
             "from datetime import date, timedelta\n",
             "import calendar\n",
             "import time\n",
             "import os\n",
             "import gc\n",
             "\n",
             "def check_integrity(df_chunk):\n",
             "    CRITICAL_COLS = ['race_id', 'horse_id', 'horse_name', 'jockey', 'date', 'rank']\n",
             "    if not all(col in df_chunk.columns for col in CRITICAL_COLS):\n",
             "        return False\n",
             "    if df_chunk[CRITICAL_COLS].isnull().any().any():\n",
             "        return False\n",
             "    return True\n",
             "\n",
             "def run_nar_scraping(year, start_month=1, end_month=12, save_dir='data/raw', target_csv='database_nar.csv', target_id_csv='race_ids_nar.csv'):\n",
             "    from tqdm.auto import tqdm\n",
             "    \n",
             "    s_date = date(int(year), int(start_month), 1)\n",
             "    last_day_e = calendar.monthrange(int(year), int(end_month))[1]\n",
             "    e_date = date(int(year), int(end_month), last_day_e)\n",
             "    today = date.today()\n",
             "    if e_date > today: e_date = today\n",
             "    \n",
             "    save_path = os.path.join(save_dir, target_csv)\n",
             "    id_path = os.path.join(save_dir, target_id_csv)\n",
             "    \n",
             "    print(f'{year}年のNARデータを {s_date} から {e_date} まで取得します(差分更新)...')\n",
             "    print(f'データ: {save_path}')\n",
             "    print(f'ID管理: {id_path}')\n",
             "    \n",
             "    # --- IDリスト初期化 ---\n",
             "    verified_ids = set()\n",
             "    if os.path.exists(id_path):\n",
             "        try:\n",
             "            df_ids = pd.read_csv(id_path, dtype=str)\n",
             "            if 'race_id' in df_ids.columns:\n",
             "                verified_ids = set(df_ids['race_id'].unique())\n",
             "            print(f\"📖 IDリスト読み込み完了: {len(verified_ids)}件\")\n",
             "        except: pass\n",
             "        \n",
             "    if os.path.exists(save_path):\n",
             "        print(\"🔍 既存データの整合性をチェック中...\")\n",
             "        try:\n",
             "            # Chunk/All read\n",
             "            df_exist = pd.read_csv(save_path, dtype=str)\n",
             "            groups = df_exist.groupby('race_id')\n",
             "            new_valid = []\n",
             "            for rid, group in tqdm(groups, desc='Checking DB'):\n",
             "                if rid in verified_ids: continue\n",
             "                if check_integrity(group):\n",
             "                    verified_ids.add(rid)\n",
             "                    new_valid.append(rid)\n",
             "            \n",
             "            if new_valid:\n",
             "                print(f\"✨ {len(new_valid)}件の有効データをIDリストに追加します\")\n",
             "                mode = 'a' if os.path.exists(id_path) else 'w'\n",
             "                pd.DataFrame({'race_id': new_valid}).to_csv(id_path, mode=mode, header=(not os.path.exists(id_path)), index=False)\n",
             "        except Exception as e:\n",
             "            print(f\"Warn read DB: {e}\")\n",
             "            \n",
             "    # --- Main Loop ---\n",
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
             "    \n",
             "    for m in range(int(start_month), int(end_month) + 1):\n",
             "        m_start = date(int(year), m, 1)\n",
             "        m_last = calendar.monthrange(int(year), m)[1]\n",
             "        m_end = date(int(year), m, m_last)\n",
             "        if m_end < s_date or m_start > e_date: continue\n",
             "        curr_s, curr_e = max(m_start, s_date), min(m_end, e_date)\n",
             "        if curr_s > curr_e: continue\n",
             "        \n",
             "        days = []\n",
             "        c = curr_s\n",
             "        while c <= curr_e:\n",
             "            days.append(c)\n",
             "            c += timedelta(days=1)\n",
             "        \n",
             "        print(f'\\n📅 {year}/{m:02} を処理中...')\n",
             "        for d in tqdm(days, desc=f'  {year}/{m:02}'):\n",
             "            d_str = d.strftime('%Y%m%d')\n",
             "            url = f'https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date={d_str}'\n",
             "            daily_data_to_save = []\n",
             "            daily_ids_to_save = []\n",
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
             "                     for link in links:\n",
             "                         href = link.get('href')\n",
             "                         if href.startswith('../'): full_url = f'https://nar.netkeiba.com/{href.replace(\"../\", \"\")}'\n",
             "                         elif href.startswith('http'): full_url = href\n",
             "                         else: full_url = f'https://nar.netkeiba.com{href}'\n",
             "                         \n",
             "                         # Extract ID? NAR IDs usually in URL?\n",
             "                         # NAR URL format often: race_id=xxxxxxxxxxxx\n",
             "                         rid_match = re.search(r'race_id=(\d+)', full_url)\n",
             "                         if rid_match:\n",
             "                             rid = rid_match.group(1)\n",
             "                             if rid in verified_ids:\n",
             "                                 continue\n",
             "                             \n",
             "                             # Scrape\n",
             "                             try:\n",
             "                                 df = scrape_race_rich(full_url, existing_race_ids=None)\n",
             "                                 if df is not None and not df.empty:\n",
             "                                     if check_integrity(df):\n",
             "                                         daily_data_to_save.append(df)\n",
             "                                         daily_ids_to_save.append(rid)\n",
             "                                         verified_ids.add(rid)\n",
             "                                 time.sleep(1)\n",
             "                             except: pass\n",
             "                 \n",
             "                 if daily_data_to_save:\n",
             "                     df_day = pd.concat(daily_data_to_save, ignore_index=True)\n",
             "                     safe_append_csv(df_day, save_path)\n",
             "                     \n",
             "                     mode = 'a' if os.path.exists(id_path) else 'w'\n",
             "                     pd.DataFrame({'race_id': daily_ids_to_save}).to_csv(id_path, mode=mode, header=(not os.path.exists(id_path)), index=False)\n",
             "                     \n",
             "                     if len(daily_ids_to_save) > 0:\n",
             "                         print(f\"    Saved {len(daily_ids_to_save)} new races.\")\n",
             "                     \n",
             "                     del daily_data_to_save\n",
             "                     del df_day\n",
             "                     gc.collect()\n",
             "            \n",
             "            except Exception as e_day:\n",
             "                print(f'  Err {d}: {e_day}')\n",
             "    \n",
             "    print('完了しました。')\n"
         ]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# 実行ブロック\n",
             "if YEAR:\n",
             "    os.makedirs(SAVE_DIR, exist_ok=True)\n",
             "    run_nar_scraping(YEAR, START_MONTH, END_MONTH, save_dir=SAVE_DIR, target_csv=TARGET_CSV, target_id_csv=TARGET_ID_CSV)\n"
         ]},
         {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
             "# 最終整理\n",
             "import pandas as pd\n",
             "import os\n",
             "csv_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
             "if os.path.exists(csv_path):\n",
             "    try:\n",
             "        df_final = pd.read_csv(csv_path, dtype=str)\n",
             "        if 'race_id' in df_final.columns and 'horse_id' in df_final.columns:\n",
             "            df_final.drop_duplicates(subset=['race_id', 'horse_id'], keep='last', inplace=True)\n",
             "        df_final.to_csv(save_path, index=False)\n",
             "        print('完了')\n",
             "    except Exception: pass\n"
         ]}
    ]
    return create_notebook(cells)

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
            "    print(f'{csv_path} が見つかりません。')\n"
        ]}
    ]
    return create_notebook(cells)

    return create_notebook(cells)

def gen_id_generator_nb():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🆔 IDキャッシュ生成ツール\n", "既存の `database.csv` (JRA) および `database_nar.csv` (NAR) をスキャンし、正しく取得されているレースIDを抽出してキャッシュファイルを作成します。\n", "**これを実行することで、次回のスクレイピング時にこれら全てのレースをスキップ（高速化）できます。**"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Driveをマウントする場合のみ実行してください\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 設定\n",
            "DATA_DIR = '/content/drive/MyDrive/dai-keiba/data/raw' # データがあるフォルダ\n",
            "JRA_CSV = 'database.csv'\n",
            "JRA_ID_CSV = 'race_ids.csv'\n",
            "NAR_CSV = 'database_nar.csv'\n",
            "NAR_ID_CSV = 'race_ids_nar.csv'\n",
            "\n",
            "# 対象期間 (この期間外のレースIDはキャッシュに含まれません)\n",
            "START_YEAR = 2020\n",
            "END_YEAR = 2026\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "import os\n",
            "import pandas as pd\n",
            "from tqdm.auto import tqdm\n",
            "\n",
            "def check_integrity(df_chunk):\n",
            "    # 必須カラムチェック\n",
            "    CRITICAL_COLS = ['race_id', 'horse_id', 'horse_name', 'jockey', 'date', 'rank']\n",
            "    if not all(col in df_chunk.columns for col in CRITICAL_COLS):\n",
            "        return False\n",
            "    # 欠損値チェック\n",
            "    if df_chunk[CRITICAL_COLS].isnull().any().any():\n",
            "        return False\n",
            "    return True\n",
            "\n",
            "def generate_id_cache(target_csv, id_csv, name='JRA'):\n",
            "    csv_path = os.path.join(DATA_DIR, target_csv)\n",
            "    id_path = os.path.join(DATA_DIR, id_csv)\n",
            "    \n",
            "    if not os.path.exists(csv_path):\n",
            "        print(f\"⚠️ {name}: {csv_path} が見つかりません。スキップします。\")\n",
            "        return\n",
            "        \n",
            "    print(f\"🔍 {name}: {csv_path} をスキャン中...\")\n",
            "    try:\n",
            "        # Chunk読み込み等はせず、シンプルに実装\n",
            "        df = pd.read_csv(csv_path, dtype=str)\n",
            "        \n",
            "        if 'race_id' not in df.columns:\n",
            "            print(f\"❌ {name}: race_idカラムがありません。\")\n",
            "            return\n",
            "            \n",
            "        # Year Filter\n",
            "        # race_id (JRA/NAR) starts with YYYY\n",
            "        df['year'] = df['race_id'].astype(str).str[:4].astype(int)\n",
            "        original_count = df['race_id'].nunique()\n",
            "        \n",
            "        df = df[(df['year'] >= START_YEAR) & (df['year'] <= END_YEAR)]\n",
            "        target_count = df['race_id'].nunique()\n",
            "        \n",
            "        print(f\"  期間フィルタ: {original_count} -> {target_count} レース ({START_YEAR}-{END_YEAR})\")\n",
            "            \n",
            "        valid_ids = []\n",
            "        groups = df.groupby('race_id')\n",
            "        \n",
            "        for rid, group in tqdm(groups, desc=f'{name} Validating'):\n",
            "            if check_integrity(group):\n",
            "                valid_ids.append(rid)\n",
            "        \n",
            "        print(f\"✨ {name}: {len(valid_ids)}件の有効なレースIDが見つかりました/全{target_count}件中。\")\n",
            "        \n",
            "        if len(valid_ids) < target_count:\n",
            "             print(f\"  ⚠️ {target_count - len(valid_ids)} 件のレースはデータ不備のためキャッシュされませんでした。\")\n",
            "        \n",
            "        if valid_ids:\n",
            "            pd.DataFrame({'race_id': valid_ids}).to_csv(id_path, index=False)\n",
            "            print(f\"✅ {id_path} に保存しました。\")\n",
            "        else:\n",
            "            print(f\"⚠️ 有効なレースが1件もありませんでした。\")\n",
            "\n",
            "    except Exception as e:\n",
            "        print(f\"❌ {name} 処理エラー: {e}\")\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 実行\n",
            "if os.path.exists(DATA_DIR):\n",
            "    generate_id_cache(JRA_CSV, JRA_ID_CSV, name='JRA')\n",
            "    print('-'*30)\n",
            "    generate_id_cache(NAR_CSV, NAR_ID_CSV, name='NAR')\n",
            "else:\n",
            "    print(f\"❌ ディレクトリが見つかりません: {DATA_DIR}\")\n"
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
    with open('notebooks/Colab_NAR_Scraping.ipynb', 'w') as f:
        f.write(gen_nar_scraping_nb())
    with open('notebooks/Colab_ID_Generator.ipynb', 'w') as f:
        f.write(gen_id_generator_nb())
