
import pandas as pd
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **kwargs): return x

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from scraper.race_scraper import RaceScraper

def backfill_metadata(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(PROJECT_ROOT, "data", "raw", "database.csv")
        
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path, dtype={'race_id': str})
    
    # Robust ID cleaning
    def clean_id(x):
        if pd.isna(x) or x == '': return None
        s = str(x)
        if s.endswith('.0'): return s[:-2]
        return s
    
    if 'race_id' in df.columns:
        df['race_id'] = df['race_id'].apply(clean_id)
    
    # Identify missing rows
    target_cols = ['コースタイプ', '距離', '天候', '馬場状態']
    for c in target_cols:
        if c not in df.columns:
            df[c] = None
    
    missing_mask = (df['コースタイプ'].isna()) | (df['コースタイプ'] == '') | \
                   (df['距離'].isna()) | (df['距離'] == '')
                   
    target_race_ids = df.loc[missing_mask, 'race_id'].unique()
    
    if len(target_race_ids) == 0:
        print("No missing metadata found.")
        return

    print(f"Found {len(target_race_ids)} races with missing metadata.")
    print("Starting backfill (Parallel)...")
    
    scraper = RaceScraper()
    results = {}
    
    def fetch_meta(rid):
        return scraper.get_race_metadata(rid)
        
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_meta, rid): rid for rid in target_race_ids}
        
        last_save = 0
        save_interval = 200 # Save every 200 results
        
        for future in tqdm(as_completed(futures), total=len(target_race_ids), desc="Backfilling"):
            data = future.result()
            if data and data.get('course_type'):
                results[data['race_id']] = data
            
            # Incremental Save
            if len(results) - last_save >= save_interval:
                print(f"  Saving progress... ({len(results)} fetched)")
                
                # Apply results collected so far to the DataFrame in memory
                current_keys = list(results.keys())
                mask = df['race_id'].isin(current_keys)
                
                c_map = {rid: d['course_type'] for rid, d in results.items() if d.get('course_type')}
                d_map = {rid: d['distance'] for rid, d in results.items() if d.get('distance')}
                w_map = {rid: d['weather'] for rid, d in results.items() if d.get('weather')}
                cond_map = {rid: d['condition'] for rid, d in results.items() if d.get('condition')}
                
                df.loc[mask, 'コースタイプ'] = df.loc[mask, 'race_id'].map(c_map).fillna(df.loc[mask, 'コースタイプ'])
                df.loc[mask, '距離'] = df.loc[mask, 'race_id'].map(d_map).fillna(df.loc[mask, '距離'])
                df.loc[mask, '天候'] = df.loc[mask, 'race_id'].map(w_map).fillna(df.loc[mask, '天候'])
                df.loc[mask, '馬場状態'] = df.loc[mask, 'race_id'].map(cond_map).fillna(df.loc[mask, '馬場状態'])
                
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                last_save = len(results)
    
    print(f"Successfully fetched metadata for {len(results)} races.")
    print("Final update DataFrame...")
    
    # Final Apply
    mask = df['race_id'].isin(results.keys())
    c_map = {rid: d['course_type'] for rid, d in results.items() if d.get('course_type')}
    d_map = {rid: d['distance'] for rid, d in results.items() if d.get('distance')}
    w_map = {rid: d['weather'] for rid, d in results.items() if d.get('weather')}
    cond_map = {rid: d['condition'] for rid, d in results.items() if d.get('condition')}
    
    df.loc[mask, 'コースタイプ'] = df.loc[mask, 'race_id'].map(c_map).fillna(df.loc[mask, 'コースタイプ'])
    df.loc[mask, '距離'] = df.loc[mask, 'race_id'].map(d_map).fillna(df.loc[mask, '距離'])
    df.loc[mask, '天候'] = df.loc[mask, 'race_id'].map(w_map).fillna(df.loc[mask, '天候'])
    df.loc[mask, '馬場状態'] = df.loc[mask, 'race_id'].map(cond_map).fillna(df.loc[mask, '馬場状態'])
    
    print("Saving to CSV...")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print("Done!")

if __name__ == "__main__":
    backfill_metadata()
