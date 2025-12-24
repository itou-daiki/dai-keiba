
import pandas as pd
import sys
import os
import re
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add Scraper directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
from race_scraper import RaceScraper

# Global lock for dataframe update
df_lock = threading.Lock()

def fetch_race_horse_ids(rid):
    """
    Worker function to fetch horse IDs for a single race.
    Returns (race_id, {horse_name: horse_id}) or None
    """
    scraper = RaceScraper()
    try:
        url = f"https://race.netkeiba.com/race/result.html?race_id={rid}"
        soup = scraper._get_soup(url)
        if not soup: return None
        
        table = soup.find("table", id="All_Result_Table")
        if not table: return None
        
        horse_map = {}
        rows = table.find_all("tr", class_="HorseList")
        for row in rows:
            name_tag = row.select_one(".Horse_Name a")
            if name_tag:
                h_name = name_tag.text.strip()
                href = name_tag.get('href', '')
                match = re.search(r'/horse/(\d+)', href)
                if match:
                    horse_map[h_name] = match.group(1)
        return (rid, horse_map)
    except Exception as e:
        print(f"Error fetching race {rid}: {e}")
        return None

def fetch_horse_history(horse_id):
    """
    Worker to fetch history for a single horse.
    Returns (horse_id, history_df)
    """
    scraper = RaceScraper()
    try:
        # We need ONE instance per thread ideally, or simple requests
        # RaceScraper is lightweight
        df = scraper.get_past_races(str(horse_id), n_samples=None)
        return (horse_id, df)
    except Exception as e:
        print(f"Error fetching horse {horse_id}: {e}")
        return (horse_id, pd.DataFrame())

def fill_missing_past_data(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw', 'database.csv')
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)

    # Ensure date column is datetime for comparison
    if '日付' in df.columns:
        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    else:
        print("Error: '日付' column not found.")
        return

    if 'horse_id' not in df.columns:
        df['horse_id'] = None

    # ==================================================
    # 1. Fill Missing Horse IDs (Parallel)
    # ==================================================
    if 'race_id' in df.columns:
        # Check masks
        missing_mask = df['horse_id'].isna() | (df['horse_id'] == '')
        
        if missing_mask.any():
            races_to_update = df.loc[missing_mask, 'race_id'].unique()
            print(f"Need to fetch IDs for {len(races_to_update)} races via Parallel Scraping...")
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(fetch_race_horse_ids, rid): rid for rid in races_to_update}
                
                completed_count = 0
                total = len(races_to_update)
                
                for future in as_completed(futures):
                    result = future.result()
                    completed_count += 1
                    if completed_count % 10 == 0:
                        print(f"  [IDs] Progress: {completed_count}/{total}")
                        
                    if result:
                        rid, horse_map = result
                        if horse_map:
                            # Update DF safely (main thread update is safe if we collect results here)
                            # Actually we are in main thread loop here.
                            race_indices = df[df['race_id'] == rid].index
                            for idx in race_indices:
                                h_name = df.at[idx, '馬名']
                                if h_name in horse_map:
                                    df.at[idx, 'horse_id'] = horse_map[h_name]
            
            print("Saving updated IDs to database.csv...")
            df.to_csv(csv_path, index=False)
        else:
            print("All Horse IDs present.")

    # ==================================================
    # 2. Fill Past History (Parallel)
    # ==================================================
    
    # Fields to populate
    fields_map = {
        'date': 'date',
        'rank': 'rank',
        'time': 'time',
        'run_style': 'run_style',
        'race_name': 'race_name',
        'last_3f': 'last_3f',
        'horse_weight': 'horse_weight',
        'jockey': 'jockey',
        'condition': 'condition',
        'odds': 'odds',
        'weather': 'weather',
        'distance': 'distance',
        'course_type': 'course_type'
    }

    unique_horses = df['horse_id'].dropna().unique()
    print(f"Found {len(unique_horses)} unique horses. Fetching history in parallel...")
    
    # We only need to fetch history for unique horses
    # Then populate the DF rows
    
    # Store history in a local dict first
    history_store = {}
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_horse_history, hid): hid for hid in unique_horses}
        
        completed_count = 0
        total = len(unique_horses)
        
        for future in as_completed(futures):
            hid, hist_df = future.result()
            history_store[hid] = hist_df
            
            completed_count += 1
            if completed_count % 50 == 0:
                print(f"  [History] Progress: {completed_count}/{total}")

    print("Applying history data to DataFrame...")
    
    # Apply to DF
    # Iterating DF rows is fast.
    for idx, row in df.iterrows():
        hid = row.get('horse_id')
        current_date = row.get('date_dt')
        
        if pd.notna(hid) and hid in history_store:
            hist_df = history_store[hid]
            if hist_df.empty: continue
            
            # Ensure date obj
            if 'date_obj' not in hist_df.columns and 'date' in hist_df.columns:
                 hist_df['date_obj'] = pd.to_datetime(hist_df['date'], format='%Y/%m/%d', errors='coerce')
            
            if 'date_obj' not in hist_df.columns: continue

            if pd.isna(current_date): continue
            
            # Filter
            past_races = hist_df[hist_df['date_obj'] < current_date].sort_values('date_obj', ascending=False).head(5)
            
            for i, (p_idx, p_row) in enumerate(past_races.iterrows()):
                 n = i + 1
                 if n > 5: break
                 
                 for field_key, field_col in fields_map.items():
                     val = p_row.get(field_col)
                     df.at[idx, f"past_{n}_{field_key}"] = val

    # Drop temp column
    if 'date_dt' in df.columns:
        df.drop(columns=['date_dt'], inplace=True)

    print(f"Saving final result to {csv_path}...")
    df.to_csv(csv_path, index=False)
    print("Done!")

if __name__ == "__main__":
    fill_missing_past_data()
