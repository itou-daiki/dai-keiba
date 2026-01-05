import json
import os

def create_notebook(filename, target_script):
    # 1. Read RaceScraper Code
    scraper_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scraper', 'race_scraper.py')
    with open(scraper_path, 'r') as f:
        scraper_code = f.read()

    # Define Notebook Structure
    notebook = {
        "cells": [],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.8.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    def add_code_cell(source):
        notebook["cells"].append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": source.splitlines(keepends=True)
        })

    def add_markdown_cell(source):
        notebook["cells"].append({
            "cell_type": "markdown",
            "metadata": {},
            "source": source.splitlines(keepends=True)
        })

    # --- Common Setup ---
    label = "JRA" if "JRA" in filename else "NAR"
    
    add_markdown_cell(f"# 🛠️ {label} Scraper Fix Notebook\n\nこのノートブックは、{label}データスクレイピングのエラーを解消するための修正版です。\nまずはドライブをマウントし、必要なライブラリをセットアップします。")
    add_code_cell("""from google.colab import drive
drive.mount('/content/drive')

import os
import sys
import pandas as pd
import numpy as np
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# プロジェクトパスの設定 (環境に合わせて変更してください)
PROJECT_PATH = '/content/drive/MyDrive/dai-keiba'
sys.path.append(PROJECT_PATH)
""")

    add_markdown_cell("## 1. RaceScraper Class definition\n\nエラー回避のため、スクレイパークラスを直接定義します。")
    add_code_cell(scraper_code)

    add_markdown_cell("## 2. Wrapper Functions\n\n欠落していた関数を定義します。")
    add_code_cell("""def fetch_race_horse_ids(race_id):
    \"\"\"
    RaceScraperを使ってレース結果ページから馬IDを取得するラッパー関数
    Returns: (race_id, {horse_name: horse_id})
    \"\"\"
    scraper = RaceScraper()
    # スクレイピング実行
    data = scraper.scrape_race_with_history(race_id)
    if not data:
        return None
    
    # {馬名: ID} の辞書を作成
    id_map = {}
    for entry in data:
        if entry.get('horse_name') and entry.get('horse_id'):
            id_map[entry['horse_name']] = entry['horse_id']
            
    return race_id, id_map

def fetch_horse_history(horse_id):
    \"\"\"
    RaceScraperを使って馬の過去成績を取得するラッパー関数
    Returns: (horse_id, history_dataframe)
    \"\"\"
    scraper = RaceScraper()
    df = scraper.get_past_races(horse_id, n_samples=5) # 直近5走のみ取得
    return horse_id, df
""")

    # --- Specific Script ---
    add_markdown_cell(f"## 3. {label} Data Fix Script\n\n以下を実行して欠損データを補完してください。")
    add_code_cell(target_script)

    # Save
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'notebooks', filename)
    with open(output_path, 'w') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"Created: {output_path}")

# === Define Logic Blocks ===

JRA_SCRIPT = """# JRAコード
# 4.2 欠損データの補完 (JRA Version)

try:
    from tqdm.auto import tqdm
except ImportError:
    !pip install tqdm
    from tqdm.auto import tqdm

def fill_missing_past_data_jra_debug():
    csv_path = os.path.join(PROJECT_PATH, 'data', 'raw', 'database.csv')
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found.')
        return

    print(f'Reading {csv_path}...')
    df = pd.read_csv(csv_path, low_memory=False, dtype={'race_id': str, 'horse_id': str})
    
    # ID Cleaning
    if 'horse_id' in df.columns:
        df['horse_id'] = df['horse_id'].astype(str).str.replace(r'\.0$', '', regex=True)

    if '日付' in df.columns:
        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    else:
        print('Error: 日付 column not found.')
        return

    def save_df_safe(dataframe, msg=""):
        try:
             out_df = dataframe.drop(columns=['date_dt', 'date_obj'], errors='ignore')
             out_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
             print(f"  [Saved] {msg}")
        except Exception as e:
             print(f"  [Save Failed] {e}")

    # === Fill Past History Only ===
    unique_horses = df['horse_id'].dropna().unique()
    
    # Resume Logic
    if 'past_1_date' in df.columns:
        done_horses = df.loc[df['past_1_date'].notna(), 'horse_id'].unique()
        unique_horses = [h for h in unique_horses if h not in done_horses]
        
    print(f'Debugging history for {len(unique_horses)} horses...')

    horse_batch_size = 50 
    fields_map = {
        'date': 'date', 'rank': 'rank', 'time': 'time', 'race_name': 'race_name', 
        'last_3f': 'last_3f', 'horse_weight': 'horse_weight', 'jockey': 'jockey', 
        'condition': 'condition', 'odds': 'odds', 'weather': 'weather', 
        'distance': 'distance', 'course_type': 'course_type'
    }
    
    for k in fields_map.keys():
        for i in range(1, 6):
            col = f'past_{i}_{k}'
            if col not in df.columns: df[col] = None

    for i in range(0, len(unique_horses), horse_batch_size):
        batch_horses = unique_horses[i:i+horse_batch_size]
        print(f"Processing Batch {i//horse_batch_size + 1} ({len(batch_horses)} horses)...")
        
        history_store = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_horse_history, hid): hid for hid in batch_horses}
            for future in tqdm(as_completed(futures), total=len(batch_horses), leave=False):
                try:
                    hid, hist_df = future.result()
                    if not hist_df.empty:
                        if 'date' in hist_df.columns:
                            hist_df['date_obj'] = pd.to_datetime(hist_df['date'], errors='coerce')
                            history_store[str(hid)] = hist_df
                except: pass
        
        modified_batch = False
        updates_count = 0
        
        if history_store:
            mask_batch = df['horse_id'].isin(history_store.keys())
            target_indices = df[mask_batch].index
            
            for idx in target_indices:
                hid = str(df.at[idx, 'horse_id'])
                current_date = df.at[idx, 'date_dt']
                
                if hid in history_store:
                    hist_df = history_store[hid]
                    if 'date_obj' not in hist_df.columns: continue
                    
                    past_races = hist_df[hist_df['date_obj'] < current_date].sort_values('date_obj', ascending=False).head(5)
                    
                    if not past_races.empty:
                        for j, (p_idx, p_row) in enumerate(past_races.iterrows()):
                            n = j + 1
                            for k, v in fields_map.items():
                                df.at[idx, f'past_{n}_{k}'] = p_row.get(v)
                                modified_batch = True
                        updates_count += 1
            
            if modified_batch:
                save_df_safe(df, f"Batch {i//horse_batch_size + 1}")
                import gc
                gc.collect()
            else:
                print("  ⚠️ No data updated in this batch.")
        else:
            print("  ⚠️ No history data fetched for this batch.")

    if 'date_dt' in df.columns: df.drop(columns=['date_dt'], inplace=True, errors='ignore')
    print('Done filling past data for JRA.')

fill_missing_past_data_jra_debug()
"""

NAR_SCRIPT = """# NARコード
# 4.2 欠損データの補完 (NAR Version)

def fill_missing_past_data_nar_notebook():
    csv_path = os.path.join(PROJECT_PATH, 'data', 'raw', 'database_nar.csv')
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found.')
        return

    print(f'Reading {csv_path}...')
    try:
        df = pd.read_csv(csv_path, low_memory=False, dtype={'race_id': str, 'horse_id': str})
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if '日付' in df.columns:
        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    else:
        print('Error: 日付 column not found.')
        return

    if 'horse_id' not in df.columns:
        df['horse_id'] = None

    def save_df_safe(dataframe, msg=""):
        try:
             out_df = dataframe.drop(columns=['date_dt', 'date_obj'], errors='ignore')
             out_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
             print(f"  [Saved] {msg}")
        except Exception as e:
             print(f"  [Save Failed] {e}")

    # 1. Fill Missing Horse IDs
    if 'race_id' in df.columns:
        missing_mask = df['horse_id'].isna() | (df['horse_id'] == '')
        if missing_mask.any():
            races_to_update = df.loc[missing_mask, 'race_id'].astype(str).unique()
            print(f'Need to fetch IDs for {len(races_to_update)} races...')
            
            chunk_size = 50
            for i in range(0, len(races_to_update), chunk_size):
                batch_r = races_to_update[i:i+chunk_size]
                updated = False
                
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {executor.submit(fetch_race_horse_ids, rid): rid for rid in batch_r}
                    for future in as_completed(futures):
                        try:
                            res = future.result()
                            if res:
                                rid, h_map = res
                                if h_map:
                                    indices = df[df['race_id'] == str(rid)].index
                                    for idx in indices:
                                        h_name = df.at[idx, '馬名']
                                        if h_name in h_map and pd.isna(df.at[idx, 'horse_id']):
                                            df.at[idx, 'horse_id'] = h_map[h_name]
                                            updated = True
                        except: pass
                
                if updated:
                    save_df_safe(df, f"IDs Batch {i//chunk_size + 1}")
            print('ID Update Complete.')

    # 2. Fill Past History
    fields_map = {
        'date': 'date', 'rank': 'rank', 'time': 'time', 'run_style': 'run_style',
        'race_name': 'race_name', 'last_3f': 'last_3f', 'horse_weight': 'horse_weight',
        'jockey': 'jockey', 'condition': 'condition', 'odds': 'odds',
        'weather': 'weather', 'distance': 'distance', 'course_type': 'course_type'
    }

    for k in fields_map.keys():
        for i in range(1, 6):
            col = f'past_{i}_{k}'
            if col not in df.columns: df[col] = None

    unique_horses = df['horse_id'].dropna().astype(str).unique()
    if 'past_1_date' in df.columns:
        done_mask = df['past_1_date'].notna()
        done_horses = df.loc[done_mask, 'horse_id'].astype(str).unique()
        unique_horses = [h for h in unique_horses if h not in done_horses]
    
    print(f'Fetching history for {len(unique_horses)} horses (Skipped completed)...')

    batch_size = 300
    for i in range(0, len(unique_horses), batch_size):
        batch_h = unique_horses[i:i+batch_size]
        hist_store = {}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_horse_history, hid): hid for hid in batch_h}
            for future in as_completed(futures):
                try:
                    hid, h_df = future.result()
                    if not h_df.empty:
                        if 'date' in h_df.columns:
                             h_df['date_obj'] = pd.to_datetime(h_df['date'], errors='coerce')
                             hist_store[str(hid)] = h_df
                except: pass
        
        if hist_store:
            modified = False
            mask_h = df['horse_id'].astype(str).isin(hist_store.keys())
            target_indices = df[mask_h].index
            
            for idx in target_indices:
                hid = str(df.at[idx, 'horse_id'])
                if hid not in hist_store: continue
                
                curr_date = df.at[idx, 'date_dt']
                if pd.isna(curr_date): continue
                
                h_df = hist_store[hid]
                if 'date_obj' not in h_df.columns: continue
                
                past = h_df[h_df['date_obj'] < curr_date].sort_values('date_obj', ascending=False).head(5)
                
                for j, (p_idx, p_row) in enumerate(past.iterrows()):
                    n = j + 1
                    for k, v in fields_map.items():
                        df.at[idx, f'past_{n}_{k}'] = p_row.get(v)
                        modified = True
            
            if modified:
                save_df_safe(df, f"History Batch {i//batch_size + 1}")
                hist_store.clear()
                import gc
                gc.collect()

    if 'date_dt' in df.columns: df.drop(columns=['date_dt'], inplace=True, errors='ignore')
    print('Done filling past data for NAR.')

fill_missing_past_data_nar_notebook()
"""

# Execute
create_notebook("Fix_Scraper_JRA.ipynb", JRA_SCRIPT)
create_notebook("Fix_Scraper_NAR.ipynb", NAR_SCRIPT)
