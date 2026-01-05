
import pandas as pd
import sys
import os
import re
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add project root to sys.path
sys.path.append(os.getcwd())

try:
    from tqdm.auto import tqdm
except ImportError:
    print("Installing tqdm...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm.auto import tqdm

try:
    from scraper.race_scraper import RaceScraper
except ImportError:
    print("Error: Could not import RaceScraper. Make sure you are in the project root.")
    sys.exit(1)

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
                match = re.search(r'/horse/(\d+)', href)
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

def main():
    csv_path = os.path.join(PROJECT_PATH, 'data/raw/database.csv')
    if not os.path.exists(csv_path):
        # Try root
        csv_path = os.path.join(PROJECT_PATH, 'database.csv')
    
    if not os.path.exists(csv_path):
        print(f'Error: database.csv not found in {PROJECT_PATH} or data/raw/')
        return

    print(f'Reading {csv_path}...')
    df = pd.read_csv(csv_path, low_memory=False)

    if '日付' in df.columns:
        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    else:
        print('Error: 日付 column not found.')
        return

    if 'horse_id' not in df.columns:
        df['horse_id'] = None

    # 1. Fill Missing Horse IDs
    if 'race_id' in df.columns:
        missing_mask = df['horse_id'].isna() | (df['horse_id'] == '')
        if missing_mask.any():
            races_to_update = df.loc[missing_mask, 'race_id'].astype(str).unique()
            print(f'Need to fetch IDs for {len(races_to_update)} races...')
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(fetch_race_horse_ids, rid): rid for rid in races_to_update}
                
                for future in tqdm(as_completed(futures), total=len(races_to_update), desc="Fetching IDs"):
                    result = future.result()
                    if result:
                        rid, horse_map = result
                        if horse_map:
                            mask = df['race_id'].astype(str) == str(rid)
                            for h_name, h_id in horse_map.items():
                                h_mask = mask & (df['馬名'] == h_name)
                                if h_mask.any():
                                    df.loc[h_mask, 'horse_id'] = h_id
            
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print('Saved updated IDs.')
        else:
            print('All Horse IDs present.')

    # 2. Fill Past History
    fields_map = {
        'date': 'date', 'rank': 'rank', 'time': 'time', 'run_style': 'run_style',
        'race_name': 'race_name', 'last_3f': 'last_3f', 'horse_weight': 'horse_weight',
        'jockey': 'jockey', 'condition': 'condition', 'odds': 'odds',
        'weather': 'weather', 'distance': 'distance', 'course_type': 'course_type'
    }

    unique_horses = df['horse_id'].dropna().astype(str).unique()
    
    new_cols = []
    for k in fields_map.keys():
        for i in range(1, 6):
            col = f'past_{i}_{k}'
            if col not in df.columns:
                new_cols.append(col)
    
    if new_cols:
        df_new = pd.DataFrame(None, index=df.index, columns=new_cols, dtype='object')
        df = pd.concat([df, df_new], axis=1)

    print(f'Found {len(unique_horses)} unique horses. Fetching history...')
    history_store = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_horse_history, hid): hid for hid in unique_horses}
        
        for future in tqdm(as_completed(futures), total=len(unique_horses), desc="Fetching History"):
            hid, hist_df = future.result()
            if not hist_df.empty:
                history_store[str(hid)] = hist_df

    print('Applying history data...')
    
    for hid in history_store:
        if 'date' in history_store[hid]:
            history_store[hid]['date_obj'] = pd.to_datetime(history_store[hid]['date'], errors='coerce')

    valid_rows = df.dropna(subset=['horse_id', 'date_dt'])
    
    for idx, row in tqdm(valid_rows.iterrows(), total=len(valid_rows), desc="Applying History"):
        hid = str(row['horse_id'])
        current_date = row['date_dt']
        
        if hid in history_store:
            hist_df = history_store[hid]
            if hist_df.empty or 'date_obj' not in hist_df.columns: continue
            
            past_races = hist_df[hist_df['date_obj'] < current_date].sort_values('date_obj', ascending=False).head(5)
            
            for i, (p_idx, p_row) in enumerate(past_races.iterrows()):
                n = i + 1
                for k, v in fields_map.items():
                    df.at[idx, f'past_{n}_{k}'] = p_row.get(v)

    if 'date_dt' in df.columns: df.drop(columns=['date_dt'], inplace=True)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print('Done filling past data.')

    # 3. Fill Blood/Pedigree Data
    # ---------------------------
    print('Checking Pedigree Data...')
    ped_cols = ['father', 'mother', 'bms']
    new_ped_cols = [c for c in ped_cols if c not in df.columns]
    if new_ped_cols:
         df_ped = pd.DataFrame(None, index=df.index, columns=new_ped_cols, dtype='object')
         df = pd.concat([df, df_ped], axis=1)

    unique_horses_df = df[['horse_id', 'father']].drop_duplicates('horse_id')
    missing_horses = unique_horses_df[unique_horses_df['father'].isna() | (unique_horses_df['father'] == '')]['horse_id'].dropna().astype(str).unique()
    
    if len(missing_horses) > 0:
        print(f'Found {len(missing_horses)} horses with missing pedigree. Fetching...')
        ped_map = {}
        
        def fetch_ped_entry(hid):
            scr = RaceScraper()
            return (hid, scr.get_horse_profile(hid))
            
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_ped_entry, hid): hid for hid in missing_horses}
            for future in tqdm(as_completed(futures), total=len(missing_horses), desc="Fetching Pedigree"):
                try:
                    hid, p_data = future.result()
                    if p_data:
                        ped_map[str(hid)] = p_data
                except: pass
        
        print('Applying pedigree data...')
        f_map = {h: d.get('father') for h, d in ped_map.items()}
        m_map = {h: d.get('mother') for h, d in ped_map.items()}
        b_map = {h: d.get('bms') for h, d in ped_map.items()}
        
        df['horse_id_str'] = df['horse_id'].astype(str)
        mask = df['horse_id_str'].isin(ped_map.keys())
        df.loc[mask, 'father'] = df.loc[mask, 'horse_id_str'].map(f_map).fillna(df.loc[mask, 'father'])
        df.loc[mask, 'mother'] = df.loc[mask, 'horse_id_str'].map(m_map).fillna(df.loc[mask, 'mother'])
        df.loc[mask, 'bms'] = df.loc[mask, 'horse_id_str'].map(b_map).fillna(df.loc[mask, 'bms'])
        
        df.drop(columns=['horse_id_str'], inplace=True, errors='ignore')
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print('Done filling pedigree.')

    # 4. Backfill Missing Metadata (Course, Distance, Weather)
    # ------------------------------------------------------
    print('Checking Metadata (Course, Distance, Weather)...')
    meta_cols = ['コースタイプ', '距離', '天候', '馬場状態']
    for c in meta_cols:
        if c not in df.columns: df[c] = None

    missing_meta_mask = (df['コースタイプ'].isna()) | (df['コースタイプ'] == '')
    if 'race_id' in df.columns:
         rids_missing = df.loc[missing_meta_mask, 'race_id'].astype(str).unique()
    else:
         rids_missing = []

    if len(rids_missing) > 0:
        print(f'Found {len(rids_missing)} races with missing metadata. Fetching...')
        meta_results = {}
        
        def fetch_meta_entry(rid):
            scr = RaceScraper()
            return scr.get_race_metadata(rid)
            
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_meta_entry, rid): rid for rid in rids_missing}
            
            for future in tqdm(as_completed(futures), total=len(rids_missing), desc="Fetching Metadata"):
                try:
                    data = future.result()
                    if data and data.get('course_type'):
                        meta_results[str(data['race_id'])] = data
                except: pass
        
        print('Applying metadata...')
        c_map = {rid: d['course_type'] for rid, d in meta_results.items()}
        d_map = {rid: d['distance'] for rid, d in meta_results.items()}
        w_map = {rid: d['weather'] for rid, d in meta_results.items()}
        cond_map = {rid: d['condition'] for rid, d in meta_results.items()}
        
        df['race_id_str'] = df['race_id'].astype(str)
        mask = df['race_id_str'].isin(meta_results.keys())
        
        df.loc[mask, 'コースタイプ'] = df.loc[mask, 'race_id_str'].map(c_map).fillna(df.loc[mask, 'コースタイプ'])
        df.loc[mask, '距離'] = df.loc[mask, 'race_id_str'].map(d_map).fillna(df.loc[mask, '距離'])
        df.loc[mask, '天候'] = df.loc[mask, 'race_id_str'].map(w_map).fillna(df.loc[mask, '天候'])
        df.loc[mask, '馬場状態'] = df.loc[mask, 'race_id_str'].map(cond_map).fillna(df.loc[mask, '馬場状態'])
        
        df.drop(columns=['race_id_str'], inplace=True, errors='ignore')

        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print('Done filling metadata.')
    else:
        print('All metadata present.')

if __name__ == "__main__":
    main()
