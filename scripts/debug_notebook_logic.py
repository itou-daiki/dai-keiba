
import pandas as pd
import sys
import os
import re
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Mock TQDM
def tqdm(iterable, total=None, desc=""):
    print(f"Start: {desc} (Total: {total})")
    for i, item in enumerate(iterable):
        yield item
        if i % 10 == 0:
            print(f".", end="", flush=True)
    print(" Done.")

# Ensure scraper path
sys.path.append(os.getcwd())
from scraper.race_scraper import RaceScraper

PROJECT_PATH = os.getcwd()

def fetch_race_horse_ids(rid):
    scraper = RaceScraper()
    try:
        url = f'https://race.netkeiba.com/race/result.html?race_id={rid}'
        soup = scraper._get_soup(url)
        if not soup: return None
        
        table = soup.find('table', id='All_Result_Table')
        if not table: return None
        
        horse_map = {}
        rows = table.find_all('tr', class_='HorseList')
        for row in rows:
            name_tag = row.select_one('.Horse_Name a')
            if name_tag:
                h_name = name_tag.text.strip()
                href = name_tag.get('href', '')
                match = re.search(r'/horse/(\\d+)', href)
                if match:
                    horse_map[h_name] = match.group(1)
        return (rid, horse_map)
    except Exception as e:
        return None

def fetch_horse_history(horse_id):
    scraper = RaceScraper()
    try:
        df = scraper.get_past_races(str(horse_id), n_samples=None)
        return (horse_id, df)
    except Exception as e:
        return (horse_id, pd.DataFrame())

def fill_missing_past_data_notebook():
    csv_path = os.path.join(PROJECT_PATH, 'data/raw/database.csv') # Adjusted path for script run
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found.')
        return

    print(f'Reading {csv_path}...')
    # === FROM NOTEBOOK ===
    df = pd.read_csv(csv_path, low_memory=False, dtype={'race_id': str, 'horse_id': str})
    def clean_id_str(x):
        if pd.isna(x) or x == '': return None
        s = str(x)
        if s.endswith('.0'): return s[:-2]
        return s
    if 'race_id' in df.columns:
        df['race_id'] = df['race_id'].apply(clean_id_str)
    if 'horse_id' in df.columns:
        df['horse_id'] = df['horse_id'].apply(clean_id_str)
    # =====================

    if '日付' in df.columns:
        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    else:
        print('Error: 日付 column not found.')
        return

    if 'horse_id' not in df.columns:
        df['horse_id'] = None

    # === 4. Fill Metadata (Course, Dist, Weather) ===
    # Focusing on this part as user complained about metadata
    print('Checking Metadata (Course, Distance, Weather)...')
    meta_cols = ['コースタイプ', '距離', '天候', '馬場状態']
    for c in meta_cols:
        if c not in df.columns: df[c] = None

    missing_meta_mask = (df['コースタイプ'].isna()) | (df['コースタイプ'] == '')
    if 'race_id' in df.columns:
         rids_missing = df.loc[missing_meta_mask, 'race_id'].astype(str).unique()
    else:
         rids_missing = []

    print(f"Missing races count: {len(rids_missing)}")
    # Simplify: just try 5 races to test
    if len(rids_missing) > 5:
        print("Trimming to 5 races for debug test.")
        rids_missing = rids_missing[:5]

    if len(rids_missing) > 0:
        print(f'Fetching metadata for {rids_missing}...')
        meta_results = {}
        
        def fetch_meta_entry(rid):
            scr = RaceScraper()
            return scr.get_race_metadata(rid)
            
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_meta_entry, rid): rid for rid in rids_missing}
            
            for future in tqdm(as_completed(futures), total=len(rids_missing), desc="Fetching Metadata"):
                try:
                    data = future.result()
                    if data and data.get('course_type'):
                        meta_results[str(data['race_id'])] = data
                except: pass
        
        print(f'Applying metadata... Got {len(meta_results)} results.')
        c_map = {rid: d['course_type'] for rid, d in meta_results.items()}
        d_map = {rid: d['distance'] for rid, d in meta_results.items()}
        w_map = {rid: d['weather'] for rid, d in meta_results.items()}
        cond_map = {rid: d['condition'] for rid, d in meta_results.items()}
        
        df['race_id_str'] = df['race_id'].astype(str)
        mask = df['race_id_str'].isin(meta_results.keys())
        
        print(f"Rows matched before update: {mask.sum()}")
        
        df.loc[mask, 'コースタイプ'] = df.loc[mask, 'race_id_str'].map(c_map).fillna(df.loc[mask, 'コースタイプ'])
        df.loc[mask, '距離'] = df.loc[mask, 'race_id_str'].map(d_map).fillna(df.loc[mask, '距離'])
        df.loc[mask, '天候'] = df.loc[mask, 'race_id_str'].map(w_map).fillna(df.loc[mask, '天候'])
        df.loc[mask, '馬場状態'] = df.loc[mask, 'race_id_str'].map(cond_map).fillna(df.loc[mask, '馬場状態'])
        
        # Check if updated using a temp check
        print("Updated values sample:")
        print(df.loc[mask, ['race_id', 'コースタイプ', '距離']].head())

        # Don't save for now, just verifying
        # df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print('Debug finished.')
    else:
        print('All metadata present.')

if __name__ == "__main__":
    fill_missing_past_data_notebook()
