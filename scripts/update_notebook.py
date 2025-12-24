import json
import os

NOTEBOOK_PATH = "notebooks/JRA_Scraper.ipynb"

def create_code_cell(source_lines):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source_lines]
    }

def get_fix_columns_code():
    return [
        "# 4.1 データベースカラム名の修正 (重複改善)",
        "import os",
        "import pandas as pd",
        "",
        "def fix_database_columns_notebook():",
        "    # Google Driveパスを使用",
        "    target_file = os.path.join(PROJECT_PATH, 'database.csv')",
        "    ",
        "    if not os.path.exists(target_file):",
        "        print('Database file not found.')",
        "        return",
        "",
        "    print(f'Checking columns in {target_file}...')",
        "    try:",
        "        df = pd.read_csv(target_file, low_memory=False)",
        "        ",
        "        # 表記ゆれ辞書",
        "        columns_to_fix = {",
        "            'コーナー通過順': 'コーナー 通過順',",
        "            '馬体重(増減)': '馬体重 (増減)'",
        "        }",
        "        ",
        "        changed = False",
        "        for bad_col, good_col in columns_to_fix.items():",
        "            if bad_col in df.columns:",
        "                print(f'Merging {bad_col} -> {good_col}...')",
        "                if good_col not in df.columns:",
        "                    df[good_col] = df[bad_col]",
        "                else:",
        "                    df[good_col] = df[good_col].fillna(df[bad_col])",
        "                ",
        "                df.drop(columns=[bad_col], inplace=True)",
        "                changed = True",
        "        ",
        "        if changed:",
        "            df.to_csv(target_file, index=False, encoding='utf-8-sig')",
        "            print('✅ Database columns fixed and saved.')",
        "        else:",
        "            print('No column fixes needed.')",
        "            ",
        "    except Exception as e:",
        "        print(f'Error fixing columns: {e}')",
        "",
        "fix_database_columns_notebook()"
    ]

def get_update_scraper_code():
    # Inject the updated jra_scraper.py logic directly into the notebook
    # This ensures the notebook usage of scrape_jra_race has the new parsing logic
    # We will override the imported function by redefining it or patching it.
    # Since imports are in cell 2/3, we can insert a cell after imports to patch scrape_jra_race.
    
    code = [
        "# 2.1 スクレイパーの修正パッチ (コース詳細・天候取得)",
        "import re",
        "import requests",
        "from bs4 import BeautifulSoup",
        "import pandas as pd",
        "import scraper.jra_scraper",
        "",
        "def patched_scrape_jra_race(url, existing_race_ids=None):",
        "    print(f'Accessing JRA URL (Patched): {url}...')",
        "    headers = {",
        "        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'", 
        "    }",
        "    try:",
        "        response = requests.get(url, headers=headers, timeout=10)",
        "        response.encoding = 'cp932'",
        "        if response.status_code != 200: return None",
        "        soup = BeautifulSoup(response.text, 'html.parser')",
        "        ",
        "        # (Skipping full redundant parse code for brevity in this patch, assuming main logic matches jra_scraper.py)",
        "        # Ideally we should just RELOAD the module if we updated the file in Drive.",
        "        # If the user updates the file in Drive (scraper/jra_scraper.py), they just need to reload.",
        "        # But to be safe, we can force reload.",
        "        pass",
        "    except: pass",
        "    return scraper.jra_scraper.scrape_jra_race(url, existing_race_ids)",
        "",
        "import importlib",
        "importlib.reload(scraper.jra_scraper)",
        "from scraper.jra_scraper import scrape_jra_race, scrape_jra_year, JRA_MONTH_PARAMS",
        "print('✅ Loaded updated scraper/jra_scraper.py from Drive')",
    ]
    return code

def get_fill_past_data_code():
    # Read the actual script content to ensure we get the full logic
    # But we need to adapt paths.
    # It's safer to embed a slightly adapted version explicitly here.
    
    code = [
        "# 4.2 欠損データの補完 (HorseID & 過去走)",
        "import pandas as pd",
        "import sys",
        "import os",
        "import re",
        "from datetime import datetime",
        "import time",
        "from concurrent.futures import ThreadPoolExecutor, as_completed",
        "import threading",
        "",
        "# Ensure scraper path",
        "sys.path.append(os.path.join(PROJECT_PATH, 'scraper'))",
        "from scraper.race_scraper import RaceScraper",
        "",
        "# Global lock for dataframe update",
        "df_lock = threading.Lock()",
        "",
        "def fetch_race_horse_ids(rid):",
        "    scraper = RaceScraper()",
        "    try:",
        "        url = f'https://race.netkeiba.com/race/result.html?race_id={rid}'",
        "        soup = scraper._get_soup(url)",
        "        if not soup: return None",
        "        ",
        "        table = soup.find('table', id='All_Result_Table')",
        "        if not table: return None",
        "        ",
        "        horse_map = {}",
        "        rows = table.find_all('tr', class_='HorseList')",
        "        for row in rows:",
        "            name_tag = row.select_one('.Horse_Name a')",
        "            if name_tag:",
        "                h_name = name_tag.text.strip()",
        "                href = name_tag.get('href', '')",
        "                match = re.search(r'/horse/(\d+)', href)",
        "                if match:",
        "                    horse_map[h_name] = match.group(1)",
        "        return (rid, horse_map)",
        "    except Exception as e:",
        "        print(f'Error fetching race {rid}: {e}')",
        "        return None",
        "",
        "def fetch_horse_history(horse_id):",
        "    scraper = RaceScraper()",
        "    try:",
        "        df = scraper.get_past_races(str(horse_id), n_samples=None)",
        "        return (horse_id, df)",
        "    except Exception as e:",
        "        print(f'Error fetching horse {horse_id}: {e}')",
        "        return (horse_id, pd.DataFrame())",
        "",
        "def fill_missing_past_data_notebook():",
        "    csv_path = os.path.join(PROJECT_PATH, 'database.csv')",
        "    if not os.path.exists(csv_path):",
        "        print(f'Error: {csv_path} not found.')",
        "        return",
        "",
        "    print(f'Reading {csv_path}...')",
        "    df = pd.read_csv(csv_path)",
        "",
        "    if '日付' in df.columns:",
        "        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')",
        "    else:",
        "        print('Error: 日付 column not found.')",
        "        return",
        "",
        "    if 'horse_id' not in df.columns:",
        "        df['horse_id'] = None",
        "",
        "    # 1. Fill Missing Horse IDs",
        "    if 'race_id' in df.columns:",
        "        missing_mask = df['horse_id'].isna() | (df['horse_id'] == '')",
        "        if missing_mask.any():",
        "            races_to_update = df.loc[missing_mask, 'race_id'].unique()",
        "            print(f'Need to fetch IDs for {len(races_to_update)} races...')",
        "            ",
        "            with ThreadPoolExecutor(max_workers=5) as executor:",
        "                futures = {executor.submit(fetch_race_horse_ids, rid): rid for rid in races_to_update}",
        "                completed = 0",
        "                for future in as_completed(futures):",
        "                    completed += 1",
        "                    if completed % 10 == 0: print(f'  [IDs] {completed}/{len(races_to_update)}')",
        "                    result = future.result()",
        "                    if result:",
        "                        rid, horse_map = result",
        "                        if horse_map:",
        "                            indices = df[df['race_id'] == rid].index",
        "                            for idx in indices:",
        "                                h_name = df.at[idx, '馬名']",
        "                                if h_name in horse_map:",
        "                                    df.at[idx, 'horse_id'] = horse_map[h_name]",
        "            ",
        "            df.to_csv(csv_path, index=False, encoding='utf-8-sig')",
        "            print('Saved updated IDs.')",
        "        else:",
        "            print('All Horse IDs present.')",
        "",
        "    # 2. Fill Past History",
        "    fields_map = {",
        "        'date': 'date', 'rank': 'rank', 'time': 'time', 'run_style': 'run_style',",
        "        'race_name': 'race_name', 'last_3f': 'last_3f', 'horse_weight': 'horse_weight',",
        "        'jockey': 'jockey', 'condition': 'condition', 'odds': 'odds',",
        "        'weather': 'weather', 'distance': 'distance', 'course_type': 'course_type'",
        "    }",
        "",
        "    unique_horses = df['horse_id'].dropna().unique()",
        "    # Simplification: Only fetch for horses missing past data to save time?",
        "    # For now, let's keep full logic but maybe we should check if columns exist",
        "    # If columns don't exist, create them",
        "    for k in fields_map.keys():",
        "        for i in range(1, 6):",
        "            col = f'past_{i}_{k}'",
        "            if col not in df.columns:",
        "                df[col] = None",
        "",
        "    print(f'Found {len(unique_horses)} unique horses. Fetching history...')",
        "    history_store = {}",
        "",
        "    with ThreadPoolExecutor(max_workers=5) as executor:",
        "        futures = {executor.submit(fetch_horse_history, hid): hid for hid in unique_horses}",
        "        completed = 0",
        "        for future in as_completed(futures):",
        "            completed += 1",
        "            if completed % 50 == 0: print(f'  [History] {completed}/{len(unique_horses)}')",
        "            hid, hist_df = future.result()",
        "            history_store[hid] = hist_df",
        "",
        "    print('Applying history data...')",
        "    for idx, row in df.iterrows():",
        "        hid = row.get('horse_id')",
        "        current_date = row.get('date_dt')",
        "        if pd.notna(hid) and hid in history_store:",
        "            hist_df = history_store[hid]",
        "            if hist_df.empty: continue",
        "            ",
        "            if 'date' in hist_df.columns:",
        "                # Fix Date format in hist_df if needed (YYYY/MM/DD)",
        "                hist_df['date_obj'] = pd.to_datetime(hist_df['date'], errors='coerce')",
        "            ",
        "            if 'date_obj' not in hist_df.columns: continue",
        "            if pd.isna(current_date): continue",
        "            ",
        "            past_races = hist_df[hist_df['date_obj'] < current_date].sort_values('date_obj', ascending=False).head(5)",
        "            ",
        "            for i, (p_idx, p_row) in enumerate(past_races.iterrows()):",
        "                n = i + 1",
        "                if n > 5: break",
        "                for k, v in fields_map.items():",
        "                    df.at[idx, f'past_{n}_{k}'] = p_row.get(v)",
        "",
        "    if 'date_dt' in df.columns: df.drop(columns=['date_dt'], inplace=True)",
        "    df.to_csv(csv_path, index=False, encoding='utf-8-sig')",
        "    print('Done filling past data.')",
        "",
        "fill_missing_past_data_notebook()"
    ]
    return code

def main():
    if not os.path.exists(NOTEBOOK_PATH):
        print(f"Notebook not found at {NOTEBOOK_PATH}")
        return

    with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Validate structure
    if "cells" not in nb:
        print("Invalid notebook format")
        return

    # Find insertion point
    # We want to insert AFTER the scraping cell (Cell 4 in 0-indexed list? No, Cell index 4 is the Run Parameters cell)
    # Cell 0: Markdown
    # Cell 1: Mount Drive
    # Cell 2: Imports
    # Cell 3: Def Scrape Exec
    # Cell 4: Run Parameters & Execution (TARGET_YEAR...)
    # Cell 5: Feature Engineering
    
    # We want to insert AFTER Cell 4 (Run Parameters) and BEFORE Cell 5 (Feature Eng).
    
    insert_idx = 5
    
    # Create cells
    cell_fix = create_code_cell(get_fix_columns_code())
    cell_fill = create_code_cell(get_fill_past_data_code())
    cell_patch = create_code_cell(get_update_scraper_code())
    
    # Check existence
    has_fix = any("fix_database_columns_notebook" in "".join(c.get("source", [])) for c in nb['cells'])
    has_fill = any("fill_missing_past_data_notebook" in "".join(c.get("source", [])) for c in nb['cells'])
    has_patch = any("patched_scrape_jra_race" in "".join(c.get("source", [])) for c in nb['cells'])

    inserted_count = 0

    # 1. Insert Patch (Early, index 3)
    if not has_patch:
        # Re-calc index: 3 is standard
        nb['cells'].insert(3, cell_patch)
        print("Inserted Scraper Patch cell.")
        inserted_count += 1
    else:
        print("Scraper Patch cell already exists.")

    # 2. Insert Fill & Fix (Late, after Run cell)
    # Finding current position of "Run Parameters" cell (TARGET_YEAR = ...)
    # Usually it's around index 4 or 5 depending on previous insertions.
    # We search for it dynamically for safety.
    run_cell_idx = -1
    for i, c in enumerate(nb['cells']):
        if "TARGET_YEAR =" in "".join(c.get("source", [])):
            run_cell_idx = i
            break
    
    insert_base = run_cell_idx + 1 if run_cell_idx >= 0 else 6
    
    # We insert in reverse order to keep them pushing down?
    # Or just insert at base.
    
    if not has_fill:
        nb['cells'].insert(insert_base, cell_fill)
        print("Inserted Fill Past Data cell.")
        inserted_count += 1
        # If we insert at base, next one should be base+1? 
        # Actually if we insert at base, it pushes everything down.
        # So next insert at base+1 puts it AFTER this one.
        # But let's just use insert_base for both if we want them reversed, or increment.
        insert_base += 1 
    else:
        print("Fill Past Data cell already exists.")

    if not has_fix:
        nb['cells'].insert(insert_base, cell_fix)
        print("Inserted Fix Columns cell.")
        inserted_count += 1
    else:
        print("Fix Columns cell already exists.")
    
    if inserted_count > 0:
        with open(NOTEBOOK_PATH, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Notebook updated with {inserted_count} new cells.")
    else:
        print("Notebook is already up to date.")

if __name__ == "__main__":
    main()
