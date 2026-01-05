import json
import os

def create_safe_notebook():
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

    # --- Setup ---
    label = "JRA (Safe Mode)"
    add_markdown_cell(f"# 🛡️ {label} Scraper Fix Notebook\n\n**重要:** スクレイピングが途中で停止する（データが取れない）現象は、アクセス頻度過多による**IP制限（ブロック）**が原因と考えられます。\nこのノートブックでは、以下の対策を行った「セーフモード」で実行します。\n\n1. **並列処理の廃止**: `ThreadPoolExecutor` を使わず、1件ずつ順番に処理します。\n2. **待機時間の増加**: 各リクエスト間に `time.sleep(3)` を入れます。\n3. **エラー詳細表示**: 429 Error (Too Many Requests) などの詳細を表示します。\n\n※ 処理速度は遅くなりますが、確実にデータを取得するための措置です。")
    add_code_cell("""from google.colab import drive
drive.mount('/content/drive')

import os
import sys
import pandas as pd
import numpy as np
import time
import re
from datetime import datetime

# プロジェクトパスの設定 (環境に合わせて変更してください)
PROJECT_PATH = '/content/drive/MyDrive/dai-keiba'
sys.path.append(PROJECT_PATH)
""")

    # --- RaceScraper with Debug Override ---
    add_markdown_cell("## 1. RaceScraper Class (Debug Enhanced)\n\nエラー原因を特定するため、ステータスコードを表示するように `_get_soup` メソッドをオーバーライドします。")
    
    # Custom Scraper Setup in Notebook
    add_code_cell("""import requests
from bs4 import BeautifulSoup
import io

class SafeRaceScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _get_soup(self, url):
        try:
            time.sleep(3) # Heavy delay for safety
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ HTTP Error {response.status_code} for {url}")
                return None
                
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    # ... Include minimal methods needed ...
    # Simplified get_past_races logic
    def get_past_races(self, horse_id, n_samples=5):
        url = f"https://db.netkeiba.com/horse/result/{horse_id}/"
        soup = self._get_soup(url)
        if not soup:
            return pd.DataFrame()

        table = soup.select_one("table.db_h_race_results")
        if not table:
            # Fallback
            tables = soup.find_all("table")
            for t in tables:
                if "着順" in t.text:
                    table = t
                    break
        
        if not table:
             return pd.DataFrame()

        try:
            df = pd.read_html(io.StringIO(str(table)))[0]
            df = df.dropna(how='all')
            
            # Clean Columns
            df.columns = df.columns.astype(str).str.replace(r'\\s+', '', regex=True)

            if '日付' in df.columns:
                df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
                df = df.dropna(subset=['date_obj'])
                df = df.sort_values('date_obj', ascending=False)
                
            if n_samples:
                df = df.head(n_samples)
            
            # Simplified Run Style
            if '通過' in df.columns:
                 # Simple heuristic
                 df['run_style_val'] = 3 

            # Map
            column_map = {
                '日付': 'date', '開催': 'venue', '天気': 'weather', 'レース名': 'race_name',
                '着順': 'rank', '枠番': 'waku', '馬番': 'umaban', '騎手': 'jockey',
                '斤量': 'weight_carried', '馬場': 'condition', 'タイム': 'time',
                '着差': 'margin', '上り': 'last_3f', '通過': 'passing',
                '馬体重': 'horse_weight', 'run_style_val': 'run_style',
                '単勝': 'odds', 'オッズ': 'odds', '距離': 'raw_distance'
            }
            df.rename(columns=column_map, inplace=True)
            
            # Parse Distance
            if 'raw_distance' in df.columns:
                def parse_dist(x):
                    if not isinstance(x, str): return None, None
                    surf = '芝' if '芝' in x else 'ダ' if 'ダ' in x else '障' if '障' in x else None
                    match = re.search(r'(\\d+)', x)
                    dist = int(match.group(1)) if match else None
                    return surf, dist
                
                parsed = df['raw_distance'].apply(parse_dist)
                df['course_type'] = parsed.apply(lambda x: x[0])
                df['distance'] = parsed.apply(lambda x: x[1])
            else:
                df['course_type'] = None
                df['distance'] = None

            # Coerce
            if 'rank' in df.columns: df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
            if 'odds' in df.columns: df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
            
            # Fill missing
            for col in list(column_map.values()) + ['course_type', 'distance']:
                if col not in df.columns: df[col] = None
                
            return df
        except Exception as e:
            print(f"Error parse: {e}")
            return pd.DataFrame()
""")

    # --- Wrapper Functions ---
    add_code_cell("""def fetch_horse_history_safe(horse_id):
    scraper = SafeRaceScraper()
    df = scraper.get_past_races(horse_id, n_samples=5)
    return horse_id, df
""")

    # --- Script ---
    add_markdown_cell("## 2. JRA Data Fix Script (Safe Mode)\n\n直列処理（シングルスレッド）で実行します。")
    add_code_cell("""# JRAコード (Safe Single-Threaded)
try:
    from tqdm.auto import tqdm
except ImportError:
    !pip install tqdm
    from tqdm.auto import tqdm

def fill_missing_past_data_jra_safe():
    csv_path = os.path.join(PROJECT_PATH, 'data', 'raw', 'database.csv')
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found.')
        return

    print(f'Reading {csv_path}...')
    df = pd.read_csv(csv_path, low_memory=False, dtype={'race_id': str, 'horse_id': str})
    
    if 'horse_id' in df.columns:
        df['horse_id'] = df['horse_id'].astype(str).str.replace(r'\\.0$', '', regex=True)

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

    # === Fill Past History ===
    unique_horses = df['horse_id'].dropna().unique()
    
    # Resume Logic
    if 'past_1_date' in df.columns:
        done_horses = df.loc[df['past_1_date'].notna(), 'horse_id'].unique()
        unique_horses = [h for h in unique_horses if h not in done_horses]
        
    print(f'Processing {len(unique_horses)} horses (Safe Mode: Single Threaded)...')

    # Smaller batch for save frequency
    horse_batch_size = 20 
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

    history_store = {}
    
    # Loop one by one
    for i, hid in enumerate(tqdm(unique_horses)):
        
        # Fetch
        _, hist_df = fetch_horse_history_safe(str(hid))
        
        if not hist_df.empty:
            if 'date' in hist_df.columns:
                hist_df['date_obj'] = pd.to_datetime(hist_df['date'], errors='coerce')
                history_store[str(hid)] = hist_df
        
        # Batch Save Logic
        if (i + 1) % horse_batch_size == 0 or (i + 1) == len(unique_horses):
            
            modified_batch = False
            updates_count = 0
            
            if history_store:
                mask_batch = df['horse_id'].isin(history_store.keys()) # Only current batch keys
                target_indices = df[mask_batch].index
                
                for idx in target_indices:
                    h_id = str(df.at[idx, 'horse_id'])
                    current_date = df.at[idx, 'date_dt']
                    
                    if h_id in history_store:
                        hist_df = history_store[h_id]
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
                batch_num = (i // horse_batch_size) + 1
                save_df_safe(df, f"Batch {batch_num} (Updates: {updates_count})")
                import gc
                gc.collect()
            
            # Clear store
            history_store = {}

    if 'date_dt' in df.columns: df.drop(columns=['date_dt'], inplace=True, errors='ignore')
    print('Done filling past data for JRA.')

fill_missing_past_data_jra_safe()
""")

    # Save
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'notebooks', 'Fix_Scraper_JRA_Safe.ipynb')
    with open(output_path, 'w') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"Created: {output_path}")

try:
    create_safe_notebook()
except Exception as e:
    print(f"Failed: {e}")
