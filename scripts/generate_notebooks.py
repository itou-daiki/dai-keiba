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
    # Read scraping logic class
    with open('scripts/scraping_logic_v2.py', 'r') as f:
        scraping_code = f.read()

    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🏇 JRA 差分スクレイピング (Master ID Based)\n", 
                                                           "このノートブックは `race_ids.csv` (マスターリスト) と `database.csv` (既存データ) を比較し、\n",
                                                           "**まだ取得していないレースのみ** をピンポイントで高速に取得します。\n",
                                                           "事前に `Colab_ID_Fetcher.ipynb` を実行してマスターリストを更新してください。"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Drive Mount\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Settings\n",
            "SAVE_DIR = '/content/drive/MyDrive/dai-keiba/data/raw'\n",
            "TARGET_CSV = 'database.csv'     # Existing Data\n",
            "MASTER_ID_CSV = 'race_ids.csv'  # Master List from ID Fetcher\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": scraping_code.splitlines(keepends=True)}, 
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Differential Scraping Execution\n",
            "import os\n",
            "import pandas as pd\n",
            "from tqdm.auto import tqdm\n",
            "import time\n",
            "import gc\n",
            "\n",
            "def run_differential_scraping():\n",
            "    # 1. Load Paths\n",
            "    csv_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
            "    id_path = os.path.join(SAVE_DIR, MASTER_ID_CSV)\n",
            "    \n",
            "    # 2. Check Master List\n",
            "    if not os.path.exists(id_path):\n",
            "        print(f\"❌ マスターリストが見つかりません: {id_path}\\n先に Colab_ID_Fetcher.ipynb を実行してください。\")\n",
            "        return\n",
            "    \n",
            "    try:\n",
            "        master_df = pd.read_csv(id_path, dtype=str)\n",
            "        if 'race_id' not in master_df.columns:\n",
            "            print(\"❌ マスターリストに race_id カラムがありません。\")\n",
            "            return\n",
            "        master_ids = set(master_df['race_id'].dropna().unique())\n",
            "        print(f\"📋 マスターリスト全件: {len(master_ids)} レース\")\n",
            "    except Exception as e:\n",
            "        print(f\"❌ マスターリスト読み込みエラー: {e}\")\n",
            "        return\n",
            "\n",
            "    # 3. Check Existing DB\n",
            "    existing_ids = set()\n",
            "    if os.path.exists(csv_path):\n",
            "        try:\n",
            "            existing_df = pd.read_csv(csv_path, dtype=str, usecols=['race_id'])\n",
            "            if 'race_id' in existing_df.columns:\n",
            "                existing_ids = set(existing_df['race_id'].dropna().unique())\n",
            "            print(f\"💾 既存取得済み: {len(existing_ids)} レース\")\n",
            "        except Exception as e:\n",
            "            print(f\"⚠️ 既存CSV読み込みエラー (初回とみなします): {e}\")\n",
            "    \n",
            "    # 4. Calculate Diff\n",
            "    # target = master - existing\n",
            "    target_ids = sorted(list(master_ids - existing_ids))\n",
            "    print(f\"🚀 今回スクレイピング対象: {len(target_ids)} レース\")\n",
            "    \n",
            "    if not target_ids:\n",
            "        print(\"✅ 全て取得済みです。終了します。\")\n",
            "        return\n",
            "\n",
            "    # 5. Scrape Loop\n",
            "    # scraping_logic_v2.py defines RaceScraper class and scrape_race_rich function\n",
            "    \n",
            "    chunk_size = 50\n",
            "    total = len(target_ids)\n",
            "    \n",
            "    # Helper to append\n",
            "    def safe_append_csv(df_chunk, path):\n",
            "        if not os.path.exists(path):\n",
            "            df_chunk.to_csv(path, index=False)\n",
            "        else:\n",
            "            try:\n",
            "                # Align columns\n",
            "                headers = pd.read_csv(path, nrows=0).columns.tolist()\n",
            "                df_aligned = df_chunk.reindex(columns=headers)\n",
            "                df_aligned.to_csv(path, mode='a', header=False, index=False)\n",
            "            except:\n",
            "                # Fallback if alignment fails\n",
            "                df_chunk.to_csv(path, mode='a', header=False, index=False)\n",
            "\n",
            "    print(\"\\n開始します...\")\n",
            "    \n",
            "    buffer = []\n",
            "    \n",
            "    for i, rid in enumerate(tqdm(target_ids)):\n",
            "        # Construct URL (JRA)\n",
            "        # https://race.netkeiba.com/race/result.html?race_id=202506010101\n",
            "        url = f\"https://race.netkeiba.com/race/result.html?race_id={rid}\"\n",
            "        \n",
            "        try:\n",
            "            time.sleep(1) # Gentle scraping\n",
            "            # scrape_race_rich auto-fetches history too\n",
            "            df = scrape_race_rich(url, force_race_id=rid)\n",
            "            \n",
            "            if df is not None and not df.empty:\n",
            "                buffer.append(df)\n",
            "        except Exception as e:\n",
            "            print(f\"  Error scraping {rid}: {e}\")\n",
            "            \n",
            "        # Save Chunk\n",
            "        if len(buffer) >= chunk_size or (i == total - 1 and buffer):\n",
            "            try:\n",
            "                df_chunk = pd.concat(buffer, ignore_index=True)\n",
            "                safe_append_csv(df_chunk, csv_path)\n",
            "                print(f\"  Saved {len(buffer)} races.\")\n",
            "                buffer = []\n",
            "                gc.collect()\n",
            "            except Exception as e:\n",
            "                print(f\"  Save Error: {e}\")\n",
            "    \n",
            "    print(\"✅ スクレイピング完了\")\n",
            "    \n",
            "    # Final Deduplication\n",
            "    if os.path.exists(csv_path):\n",
            "        print('最終整理中...')\n",
            "        try:\n",
            "            df_final = pd.read_csv(csv_path, dtype=str, low_memory=False)\n",
            "            if 'race_id' in df_final.columns and 'horse_id' in df_final.columns:\n",
            "                before = len(df_final)\n",
            "                df_final.drop_duplicates(subset=['race_id', 'horse_id'], keep='last', inplace=True)\n",
            "                after = len(df_final)\n",
            "                if before != after:\n",
            "                    df_final.to_csv(csv_path, index=False)\n",
            "                    print(f'  重複削除: {before} -> {after} rows')\n",
            "        except Exception: pass\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Run\n",
            "run_differential_scraping()\n"
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
    # Read scraping logic class
    with open('scripts/scraping_logic_v2.py', 'r') as f:
        scraping_code = f.read()

    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🏇 NAR 差分スクレイピング (Master ID Based)\n", 
                                                           "このノートブックは `race_ids_nar.csv` (マスターリスト) と `database_nar.csv` (既存データ) を比較し、\n",
                                                           "**まだ取得していないレースのみ** をピンポイントで高速に取得します。\n",
                                                           "事前に `Colab_ID_Fetcher.ipynb` を実行してマスターリストを更新してください。"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Drive Mount\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Settings\n",
            "SAVE_DIR = '/content/drive/MyDrive/dai-keiba/data/raw'\n",
            "TARGET_CSV = 'database_nar.csv'         # Existing Data\n",
            "MASTER_ID_CSV = 'race_ids_nar.csv'      # Master List from ID Fetcher\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": scraping_code.splitlines(keepends=True)}, 
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Differential Scraping Execution\n",
            "import os\n",
            "import pandas as pd\n",
            "from tqdm.auto import tqdm\n",
            "import time\n",
            "import gc\n",
            "\n",
            "def run_differential_scraping():\n",
            "    # 1. Load Paths\n",
            "    csv_path = os.path.join(SAVE_DIR, TARGET_CSV)\n",
            "    id_path = os.path.join(SAVE_DIR, MASTER_ID_CSV)\n",
            "    \n",
            "    # 2. Check Master List\n",
            "    if not os.path.exists(id_path):\n",
            "        print(f\"❌ マスターリストが見つかりません: {id_path}\\n先に Colab_ID_Fetcher.ipynb を実行してください。\")\n",
            "        return\n",
            "    \n",
            "    try:\n",
            "        master_df = pd.read_csv(id_path, dtype=str)\n",
            "        if 'race_id' not in master_df.columns:\n",
            "            print(\"❌ マスターリストに race_id カラムがありません。\")\n",
            "            return\n",
            "        master_ids = set(master_df['race_id'].dropna().unique())\n",
            "        print(f\"📋 マスターリスト全件: {len(master_ids)} レース\")\n",
            "    except Exception as e:\n",
            "        print(f\"❌ マスターリスト読み込みエラー: {e}\")\n",
            "        return\n",
            "\n",
            "    # 3. Check Existing DB\n",
            "    existing_ids = set()\n",
            "    if os.path.exists(csv_path):\n",
            "        try:\n",
            "            existing_df = pd.read_csv(csv_path, dtype=str, usecols=['race_id'])\n",
            "            if 'race_id' in existing_df.columns:\n",
            "                existing_ids = set(existing_df['race_id'].dropna().unique())\n",
            "            print(f\"💾 既存取得済み: {len(existing_ids)} レース\")\n",
            "        except Exception as e:\n",
            "            print(f\"⚠️ 既存CSV読み込みエラー (初回とみなします): {e}\")\n",
            "    \n",
            "    # 4. Calculate Diff\n",
            "    target_ids = sorted(list(master_ids - existing_ids))\n",
            "    print(f\"🚀 今回スクレイピング対象: {len(target_ids)} レース\")\n",
            "    \n",
            "    if not target_ids:\n",
            "        print(\"✅ 全て取得済みです。終了します。\")\n",
            "        return\n",
            "\n",
            "    # 5. Scrape Loop\n",
            "    chunk_size = 50\n",
            "    total = len(target_ids)\n",
            "    \n",
            "    # Helper to append\n",
            "    def safe_append_csv(df_chunk, path):\n",
            "        if not os.path.exists(path):\n",
            "            df_chunk.to_csv(path, index=False)\n",
            "        else:\n",
            "            try:\n",
            "                headers = pd.read_csv(path, nrows=0).columns.tolist()\n",
            "                df_aligned = df_chunk.reindex(columns=headers)\n",
            "                df_aligned.to_csv(path, mode='a', header=False, index=False)\n",
            "            except:\n",
            "                df_chunk.to_csv(path, mode='a', header=False, index=False)\n",
            "\n",
            "    print(\"\\n開始します...\")\n",
            "    \n",
            "    buffer = []\n",
            "    \n",
            "    for i, rid in enumerate(tqdm(target_ids)):\n",
            "        # Construct URL (NAR)\n",
            "        # https://nar.netkeiba.com/race/result.html?race_id=202506010101\n",
            "        url = f\"https://nar.netkeiba.com/race/result.html?race_id={rid}\"\n",
            "        \n",
            "        try:\n",
            "            time.sleep(1)\n",
            "            # NAR: force_race_id ensures correct ID (parsing NAR headers can be unreliable)\n",
            "            df = scrape_race_rich(url, force_race_id=rid)\n",
            "            \n",
            "            if df is not None and not df.empty:\n",
            "                buffer.append(df)\n",
            "        except Exception as e:\n",
            "            print(f\"  Error scraping {rid}: {e}\")\n",
            "            \n",
            "        # Save Chunk\n",
            "        if len(buffer) >= chunk_size or (i == total - 1 and buffer):\n",
            "            try:\n",
            "                df_chunk = pd.concat(buffer, ignore_index=True)\n",
            "                safe_append_csv(df_chunk, csv_path)\n",
            "                print(f\"  Saved {len(buffer)} races.\")\n",
            "                buffer = []\n",
            "                gc.collect()\n",
            "            except Exception as e:\n",
            "                print(f\"  Save Error: {e}\")\n",
            "    \n",
            "    print(\"✅ スクレイピング完了\")\n",
            "    \n",
            "    # Final Deduplication\n",
            "    if os.path.exists(csv_path):\n",
            "        print('最終整理中...')\n",
            "        try:\n",
            "            df_final = pd.read_csv(csv_path, dtype=str, low_memory=False)\n",
            "            if 'race_id' in df_final.columns and 'horse_id' in df_final.columns:\n",
            "                before = len(df_final)\n",
            "                df_final.drop_duplicates(subset=['race_id', 'horse_id'], keep='last', inplace=True)\n",
            "                after = len(df_final)\n",
            "                if before != after:\n",
            "                    df_final.to_csv(csv_path, index=False)\n",
            "                    print(f'  重複削除: {before} -> {after} rows')\n",
            "        except Exception: pass\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Run\n",
            "run_differential_scraping()\n"
        ]}
    ]
    return create_notebook(cells)

def gen_nar_backfill_nb():
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
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🛠️ NAR データ補完ツール\n", "欠損している血統情報および過去走履歴を補完します。"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Driveをマウントする場合のみ実行してください\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": race_scraper_code.splitlines(keepends=True)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [l + "\n" for l in filtered_helper]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 設定\n",
            "DATA_DIR = '/content/drive/MyDrive/dai-keiba/data/raw'\n",
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

def gen_id_fetcher_nb():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# 🆔 マスターIDリスト取得ツール (Web Crawler)\n", "Netkeibaの開催カレンダーを巡回し、指定期間内の**全てのレースID**を取得して `race_ids.csv` (JRA) / `race_ids_nar.csv` (NAR) を作成します。\n", "これらが「マスターリスト」となり、スクレイピングツールはこのリストにあるが手元のCSVにないデータのみを取得するようになります。"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# Google Driveをマウント\n",
            "from google.colab import drive\n",
            "drive.mount('/content/drive')"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 設定\n",
            "DATA_DIR = '/content/drive/MyDrive/dai-keiba/data/raw'\n",
            "JRA_ID_CSV = 'race_ids.csv'\n",
            "NAR_ID_CSV = 'race_ids_nar.csv'\n",
            "\n",
            "START_YEAR = 2020\n",
            "END_YEAR = 2026\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "import requests\n",
            "from bs4 import BeautifulSoup\n",
            "import pandas as pd\n",
            "import re\n",
            "import time\n",
            "import os\n",
            "from tqdm.auto import tqdm\n",
            "from datetime import date, timedelta\n",
            "\n",
            "def fetch_race_ids(mode='JRA', start_year=2020, end_year=2026):\n",
            "    print(f\"\\n🚀 {mode} Race ID Fetching ({start_year}-{end_year})...\")\n",
            "    \n",
            "    # Base URLs\n",
            "    # JRA: race.netkeiba.com\n",
            "    # NAR: nar.netkeiba.com\n",
            "    base_domain = \"race.netkeiba.com\" if mode == 'JRA' else \"nar.netkeiba.com\"\n",
            "    save_csv = JRA_ID_CSV if mode == 'JRA' else NAR_ID_CSV\n",
            "    save_path = os.path.join(DATA_DIR, save_csv)\n",
            "    \n",
            "    all_ids = set()\n",
            "    \n",
            "    # If file exists, load it first to append/update? \n",
            "    # User request implies \"Master List\", so maybe overwrite or merge?\n",
            "    # Let's load existing to avoid duplicates, but crawling should be authoritative.\n",
            "    if os.path.exists(save_path):\n",
            "        try:\n",
            "            existing_df = pd.read_csv(save_path, dtype=str)\n",
            "            if 'race_id' in existing_df.columns:\n",
            "                all_ids = set(existing_df['race_id'].unique())\n",
            "                print(f\"  Loaded {len(all_ids)} existing IDs from {save_csv}\")\n",
            "        except: pass\n",
            "\n",
            "    session = requests.Session()\n",
            "    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}\n",
            "    \n",
            "    for year in range(start_year, end_year + 1):\n",
            "        print(f\"  📅 Processing {year}...\")\n",
            "        for month in range(1, 13):\n",
            "            # Calendar Page\n",
            "            # https://race.netkeiba.com/top/calendar.html?year=2025&month=1\n",
            "            cal_url = f\"https://{base_domain}/top/calendar.html?year={year}&month={month}\"\n",
            "            try:\n",
            "                time.sleep(0.5)\n",
            "                resp = session.get(cal_url, headers=headers, timeout=10)\n",
            "                resp.encoding = 'EUC-JP'\n",
            "                soup = BeautifulSoup(resp.text, 'html.parser')\n",
            "                \n",
            "                # Find days with links\n",
            "                # Output format: <td class=\"RaceCell\"><a href=\"../top/race_list.html?kaisai_date=20250105\">...</a></td>\n",
            "                # Links: ../top/race_list.html?kaisai_date=YYYYMMDD\n",
            "                day_links = soup.select('a[href*=\"race_list.html?kaisai_date=\"]')\n",
            "                dates = []\n",
            "                for link in day_links:\n",
            "                    href = link.get('href')\n",
            "                    m = re.search(r'kaisai_date=(\\d{8})', href)\n",
            "                    if m:\n",
            "                        dates.append(m.group(1))\n",
            "                \n",
            "                dates = sorted(list(set(dates)))\n",
            "                if not dates: continue\n",
            "                \n",
            "                # Iterate Days\n",
            "                for d_str in tqdm(dates, desc=f\"{year}/{month:02}\", leave=False):\n",
            "                    # Race List Page\n",
            "                    # https://race.netkeiba.com/top/race_list.html?kaisai_date=20250105\n",
            "                    list_url = f\"https://{base_domain}/top/race_list.html?kaisai_date={d_str}\"\n",
            "                    try:\n",
            "                        time.sleep(0.3)\n",
            "                        r_resp = session.get(list_url, headers=headers, timeout=10)\n",
            "                        r_resp.encoding = 'EUC-JP'\n",
            "                        r_soup = BeautifulSoup(r_resp.text, 'html.parser')\n",
            "                        \n",
            "                        # Find Race Links\n",
            "                        # <a href=\"../race/result.html?race_id=202506010101\">...</a>\n",
            "                        # or shutuba.html (if future)\n",
            "                        race_links = r_soup.select('a[href*=\"race_id=\"]')\n",
            "                        \n",
            "                        day_ids = set()\n",
            "                        for r_link in race_links:\n",
            "                            r_href = r_link.get('href')\n",
            "                            rm = re.search(r'race_id=(\\d+)', r_href)\n",
            "                            if rm:\n",
            "                                rid = rm.group(1)\n",
            "                                # JRA IDs usually 12 digits. NAR can be 12?\n",
            "                                # Validate length just in case? \n",
            "                                # Netkeiba unified ID is usually 12 digits (YYYY PP KK DD RR)\n",
            "                                if len(rid) == 12:\n",
            "                                    day_ids.add(rid)\n",
            "                        \n",
            "                        all_ids.update(day_ids)\n",
            "                        \n",
            "                    except Exception as e:\n",
            "                         print(f\"    Error fetching day {d_str}: {e}\")\n",
            "                         \n",
            "            except Exception as e:\n",
            "                print(f\"    Error fetching calendar {year}/{month}: {e}\")\n",
            "    \n",
            "    # Save\n",
            "    print(f\"\\n💾 Saving {len(all_ids)} IDs to {save_path}...\")\n",
            "    df_out = pd.DataFrame({'race_id': sorted(list(all_ids))})\n",
            "    df_out.to_csv(save_path, index=False)\n",
            "    print(\"✅ Done.\")\n",
            "\n"
        ]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "# 実行\n",
            "if os.path.exists(DATA_DIR):\n",
            "    try:\n",
            "        fetch_race_ids(mode='JRA', start_year=START_YEAR, end_year=END_YEAR)\n",
            "    except Exception as e: print(f\"JRA Error: {e}\")\n",
            "    \n",
            "    try:\n",
            "        fetch_race_ids(mode='NAR', start_year=START_YEAR, end_year=END_YEAR)\n",
            "    except Exception as e: print(f\"NAR Error: {e}\")\n",
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
    with open('notebooks/Colab_ID_Fetcher.ipynb', 'w') as f:
        f.write(gen_id_fetcher_nb())
