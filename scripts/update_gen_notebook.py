import os

target_file = 'scripts/generate_notebooks.py'
start_line = 21
end_line = 226

new_code = r'''def gen_jra_scraping_nb():
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
'''

with open(target_file, 'r') as f:
    lines = f.readlines()

output_lines = lines[:start_line-1] + [new_code + '\n\n'] + lines[end_line:]

with open(target_file, 'w') as f:
    f.writelines(output_lines)
    
print("Successfully replaced content.")
