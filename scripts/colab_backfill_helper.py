import pandas as pd
import numpy as np
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm.auto import tqdm

# Add project root to path to ensure scraper imports work
# Assumes this script is in 'scripts/' and 'scraper/' is in root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scraper.race_scraper import RaceScraper
except ImportError:
    print("❌ Could not import RaceScraper. Make sure you are running this from the repository root or 'ids' folder structure is correct.")
    # Fallback/Mock for testing if needed, or exit
    sys.exit(1)

def fill_bloodline_data(df_path, mode="JRA"):
    """
    Backfills missing bloodline data (father, mother, bms).
    """
    print(f"\n🐴 Starting Bloodline Backfill for {mode} ({os.path.basename(df_path)})")
    
    if not os.path.exists(df_path):
        print(f"❌ File not found: {df_path}")
        return

    # Load Data
    try:
        if df_path.endswith('.parquet'):
            df = pd.read_parquet(df_path)
        else:
            df = pd.read_csv(df_path, low_memory=False)
            # Ensure IDs are strings
            if 'horse_id' in df.columns:
                df['horse_id'] = df['horse_id'].astype(str).str.replace(r'\.0$', '', regex=True)
            if 'race_id' in df.columns:
                df['race_id'] = df['race_id'].astype(str).str.replace(r'\.0$', '', regex=True)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return

    # Ensure Columns Exist
    for col in ['father', 'mother', 'bms']:
        if col not in df.columns:
            df[col] = None

    # Identify Missing
    # Criteria: 'father' is null/empty AND 'horse_id' is valid
    mask_missing = (df['father'].isna()) | (df['father'] == '') | (df['father'] == 'nan')
    
    if 'horse_id' not in df.columns:
        print("❌ 'horse_id' column missing.")
        return

    target_ids = df.loc[mask_missing, 'horse_id'].dropna().unique()
    target_ids = [hid for hid in target_ids if str(hid).isdigit()] # Filter valid IDs
    
    total_targets = len(target_ids)
    print(f"🎯 Found {total_targets} horses with missing bloodline data.")
    
    if total_targets == 0:
        print("✅ No missing bloodline data found.")
        return

    # Scraper Setup
    scraper = RaceScraper()
    
    # Worker Function
    def fetch_pedigree(hid):
        # random sleep to avoid rate limiting
        time.sleep(0.1) 
        try:
            return (hid, scraper.get_horse_profile(hid))
        except Exception as e:
            return (hid, None)

    # Sequential Execution (No Parallel)
    print(f"🚀 Fetching data for {total_targets} horses (Sequential)...")
    
    # Chunking to save progress
    CHUNK_SIZE = 1000
    
    results = {}
    for i in range(0, total_targets, CHUNK_SIZE):
        chunk = target_ids[i:i+CHUNK_SIZE]
        print(f"  Processing chunk {i}-{i+len(chunk)}...")
        
        # Sequential Loop
        for hid in tqdm(chunk, leave=False):
            try:
                # Random sleep to be gentle
                time.sleep(0.5) 
                data = scraper.get_horse_profile(hid)
                if data:
                    results[hid] = data
            except Exception as e:
                # print(f"Error fetching {hid}: {e}")
                pass
        
        # Apply Logic
        if len(results) > 0:
            print("  Applying updates to DataFrame...")
            # Create Maps
            f_map = {h: d.get('father') for h, d in results.items() if d}
            m_map = {h: d.get('mother') for h, d in results.items() if d}
            b_map = {h: d.get('bms') for h, d in results.items() if d}
            
            # Update only rows that match these IDs
            mask_chunk = df['horse_id'].isin(results.keys())
            
            # Efficient Map Update
            df.loc[mask_chunk, 'father'] = df.loc[mask_chunk, 'horse_id'].map(f_map).fillna(df.loc[mask_chunk, 'father'])
            df.loc[mask_chunk, 'mother'] = df.loc[mask_chunk, 'horse_id'].map(m_map).fillna(df.loc[mask_chunk, 'mother'])
            df.loc[mask_chunk, 'bms'] = df.loc[mask_chunk, 'horse_id'].map(b_map).fillna(df.loc[mask_chunk, 'bms'])
            
            # Clear results buffer
            results = {}
            
            # Save
            print(f"  💾 Saving progress to {df_path}...")
            if df_path.endswith('.parquet'):
                df.to_parquet(df_path, index=False)
            else:
                df.to_csv(df_path, index=False)

    print("✅ Bloodline backfill complete.")


def fill_history_data(df_path, mode="JRA"):
    """
    Backfills missing past race history (past_1_date, etc.).
    Target: Rows where 'past_1_date' is NaN AND race is NOT 'Shinba' (Debut).
    """
    print(f"\n📜 Starting History Backfill for {mode} ({os.path.basename(df_path)})")
    
    if not os.path.exists(df_path):
        print(f"❌ File not found: {df_path}")
        return

    # Load Data
    try:
        if df_path.endswith('.parquet'):
            df = pd.read_parquet(df_path)
        else:
            df = pd.read_csv(df_path, low_memory=False)
            if 'horse_id' in df.columns:
                df['horse_id'] = df['horse_id'].astype(str).str.replace(r'\.0$', '', regex=True)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return

    # Filter Targets
    # 1. Not Shinba
    if 'レース名' in df.columns:
        mask_shinba = df['レース名'].astype(str).str.contains('新馬|メイクデビュー', na=False)
    else:
        mask_shinba = False
        
    # 2. Missing History
    mask_missing = df['past_1_date'].isna() & (~mask_shinba)
    
    target_rows = df[mask_missing]
    target_ids = target_rows['horse_id'].unique()
    target_ids = [hid for hid in target_ids if str(hid).isdigit()]
    
    total_targets = len(target_ids)
    print(f"🎯 Found {len(target_rows)} rows ({total_targets} unique horses) missing history.")
    
    if total_targets == 0:
        print("✅ No missing history found.")
        return

    scraper = RaceScraper()
    history_cache = {}

    # Worker for simple fetch
    def fetch_history(hid):
        time.sleep(0.1)
        try:
            return (hid, scraper.get_past_races(hid, n_samples=None))
        except:
            return (hid, None)
            
    # Process
    print(f"🚀 Fetching history for {total_targets} horses (Sequential)...")
    
    CHUNK_SIZE = 500
    for i in range(0, total_targets, CHUNK_SIZE):
        chunk_ids = target_ids[i:i+CHUNK_SIZE]
        
        # Sequential Loop
        for hid in tqdm(chunk_ids, leave=False, desc=f"Chunk {i//CHUNK_SIZE+1}"):
             try:
                 time.sleep(0.5)
                 hist_df = scraper.get_past_races(hid, n_samples=None)
                 if hist_df is not None and not hist_df.empty:
                     if 'date' in hist_df.columns:
                         hist_df['date_dt'] = pd.to_datetime(hist_df['date'], format='%Y/%m/%d', errors='coerce')
                     history_cache[hid] = hist_df
             except:
                 pass
        
        # Apply to DataFrame iteratively (Complex because depends on Race Date)
        print("  Applying history to missing rows...")
        
        # We need to iterate over the rows in the main DF that correspond to these horses
        # This part is slow if not vectorized, but logic is complex (compare dates).
        # Optimization: Group by horse_id
        
        chunk_mask = df['horse_id'].isin(chunk_ids) & mask_missing
        affected_indices = df[chunk_mask].index
        
        updates = [] # List of (index, col, value)
        
        for idx in tqdm(affected_indices, desc="Updating Rows"):
            row = df.loc[idx]
            hid = row['horse_id']
            race_date_str = str(row['日付']) # YYYY年MM月DD日
            
            if hid not in history_cache: continue
            
            hist_df = history_cache[hid]
            if hist_df is None or hist_df.empty: continue
            
            try:
                # Parse race date
                # Handle 'YYYY年MM月DD日' or 'YYYY/MM/DD'
                race_date_str = race_date_str.replace('年','/').replace('月','/').replace('日','')
                current_date = pd.to_datetime(race_date_str, errors='coerce')
                
                if pd.isna(current_date): continue
                
                # Filter history < current_date
                valid_hist = hist_df[hist_df['date_dt'] < current_date].copy()
                
                if valid_hist.empty: continue
                
                # Take top 5
                valid_hist = valid_hist.sort_values('date_dt', ascending=False).head(5)
                
                # Prepare update dict for this row
                # Columns: past_1_date, past_1_rank, ...
                cols_map = {
                    'date': 'date', 'rank': 'rank', 'time': 'time', 'run_style': 'run_style',
                    'race_name': 'race_name', 'last_3f': 'last_3f', 'horse_weight': 'horse_weight',
                    'jockey': 'jockey', 'condition': 'condition', 'weather': 'weather',
                    'distance': 'distance', 'course_type': 'course_type', 'odds': 'odds'
                }
                
                for n, (_, h_row) in enumerate(valid_hist.iterrows()):
                    if n >= 5: break
                    prefix = f"past_{n+1}_"
                    
                    df.at[idx, prefix + 'date'] = h_row.get('date')
                    df.at[idx, prefix + 'rank'] = h_row.get('rank')
                    df.at[idx, prefix + 'time'] = h_row.get('time')
                    df.at[idx, prefix + 'race_name'] = h_row.get('race_name')
                    # ... Add other columns as needed. For brevity, main ones.
                    # Note: assign directly to avoid huge list overhead
                    
                    for key, val_key in cols_map.items():
                         df.at[idx, prefix + key] = h_row.get(val_key)

            except Exception as e:
                # print(f"Error updating row {idx}: {e}")
                pass

        # Clear cache for this chunk to free memory
        history_cache = {}
        
        # Save
        print(f"  💾 Saving progress to {df_path}...")
        if df_path.endswith('.parquet'):
             df.to_parquet(df_path, index=False)
        else:
             df.to_csv(df_path, index=False)

    print("✅ History backfill complete.")


def fill_race_metadata(df_path, mode="JRA"):
    """
    Backfills missing race metadata (course_type, distance, weather, condition).
    """
    print(f"\n🏟️ Starting Race Metadata Backfill for {mode} ({os.path.basename(df_path)})")
    
    if not os.path.exists(df_path):
        print(f"❌ File not found: {df_path}")
        return

    # Load Data
    try:
        if df_path.endswith('.parquet'):
            df = pd.read_parquet(df_path)
        else:
            df = pd.read_csv(df_path, low_memory=False)
            if 'race_id' in df.columns:
                df['race_id'] = df['race_id'].astype(str).str.replace(r'\.0$', '', regex=True)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return

    # Identify missing rows
    target_cols = ['コースタイプ', '距離', '天候', '馬場状態']
    for c in target_cols:
        if c not in df.columns:
            df[c] = None
    
    missing_mask = (df['コースタイプ'].isna()) | (df['コースタイプ'] == '') | \
                   (df['距離'].isna()) | (df['距離'] == '') | \
                   (df['天候'].isna()) | (df['天候'] == '')
                   
    target_race_ids = df.loc[missing_mask, 'race_id'].unique()
    target_race_ids = [rid for rid in target_race_ids if str(rid).isdigit()]
    
    total_targets = len(target_race_ids)
    print(f"🎯 Found {total_targets} races with missing metadata.")
    
    if total_targets == 0:
        print("✅ No missing metadata found.")
        return

    scraper = RaceScraper()
    results = {}
    
    # Sequential Execution
    print(f"🚀 Fetching metadata for {total_targets} races (Sequential)...")
    
    CHUNK_SIZE = 200
    for i in range(0, total_targets, CHUNK_SIZE):
        chunk = target_race_ids[i:i+CHUNK_SIZE]
        
        for rid in tqdm(chunk, leave=False):
            try:
                time.sleep(0.5)
                data = scraper.get_race_metadata(rid)
                if data and data.get('course_type'):
                    results[rid] = data
            except:
                pass
        
        # Save Progress
        if len(results) > 0:
            print("  Applying metadata updates...")
            mask = df['race_id'].isin(results.keys())
            
            c_map = {rid: d['course_type'] for rid, d in results.items() if d.get('course_type')}
            d_map = {rid: d['distance'] for rid, d in results.items() if d.get('distance')}
            w_map = {rid: d['weather'] for rid, d in results.items() if d.get('weather')}
            cond_map = {rid: d['condition'] for rid, d in results.items() if d.get('condition')}
            
            df.loc[mask, 'コースタイプ'] = df.loc[mask, 'race_id'].map(c_map).fillna(df.loc[mask, 'コースタイプ'])
            df.loc[mask, '距離'] = df.loc[mask, 'race_id'].map(d_map).fillna(df.loc[mask, '距離'])
            df.loc[mask, '天候'] = df.loc[mask, 'race_id'].map(w_map).fillna(df.loc[mask, '天候'])
            df.loc[mask, '馬場状態'] = df.loc[mask, 'race_id'].map(cond_map).fillna(df.loc[mask, '馬場状態'])
            
            results = {} # Clear buffer
            
            print(f"  💾 Saving progress to {df_path}...")
            if df_path.endswith('.parquet'):
                df.to_parquet(df_path, index=False)
            else:
                df.to_csv(df_path, index=False)

    print("✅ Race metadata backfill complete.")


# if __name__ == "__main__":
#     # Example Usage
#     print("Usage: Select mode to run.")
#     # Uncomment based on need
#     # fill_bloodline_data('data/raw/database.csv', mode="JRA")
#     # fill_history_data('data/raw/database.csv', mode="JRA")
    
#     # fill_bloodline_data('data/raw/database_nar.csv', mode="NAR")
#     # fill_history_data('data/raw/database_nar.csv', mode="NAR")

