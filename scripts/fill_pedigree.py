import pandas as pd
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from scraper.race_scraper import RaceScraper

def fill_pedigree(csv_path):
    if not os.path.exists(csv_path):
        print(f"Skipping {csv_path} (Not found)")
        return

    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path, dtype={'horse_id': str})

    # Ensure columns exist
    for col in ['father', 'mother', 'bms']:
        if col not in df.columns:
            df[col] = None

    # Identify horses with missing pedigree
    # We check if father is missing.
    # We group by horse_id to minimize requests
    unique_horses = df[['horse_id', 'father']].drop_duplicates('horse_id')
    
    # Filter for those with missing 'father' (assuming if father missing, all missing)
    missing_horses = unique_horses[unique_horses['father'].isna() | (unique_horses['father'] == '')]['horse_id'].dropna().unique()
    
    if len(missing_horses) == 0:
        print("No missing pedigree data found.")
        return

    print(f"Found {len(missing_horses)} horses with missing pedigree. Fetching...")
    
    scraper = RaceScraper()
    pedigree_map = {}

    def fetch_ped(hid):
        return (hid, scraper.get_horse_profile(hid))

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_ped, hid): hid for hid in missing_horses}
        completed = 0
        total = len(missing_horses)
        
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0:
                print(f"  [Pedigree] {completed}/{total}")
            
            try:
                hid, data = future.result()
                if data:
                    pedigree_map[hid] = data
            except Exception as e:
                # print(f"Error {hid}: {e}")
                pass

    print(f"Fetched pedigree for {len(pedigree_map)} horses. Applying...")

    # Update DataFrame
    # Using map is faster
    # Create valid maps
    father_map = {h: d.get('father') for h, d in pedigree_map.items()}
    mother_map = {h: d.get('mother') for h, d in pedigree_map.items()}
    bms_map = {h: d.get('bms') for h, d in pedigree_map.items()}

    # Update only rows where currently missing (or verify)
    # We map all matching horse_ids
    
    # Efficient update
    mask = df['horse_id'].isin(pedigree_map.keys())
    
    # We use combine_first or update, but straight assignment with map is easier if we target the rows
    # df.loc[mask, 'father'] = df.loc[mask, 'horse_id'].map(father_map) # This might overwrite with Nan if map missing? No, we filtered map.
    
    # But wait, map returns NaN for keys not in map.
    # So we should only update where we have data.
    
    # Better: iterate columns and use apply or map, filling NA with original?
    # Or just loop. Vectorized map is fine.
    
    df.loc[mask, 'father'] = df.loc[mask, 'horse_id'].map(father_map).fillna(df.loc[mask, 'father'])
    df.loc[mask, 'mother'] = df.loc[mask, 'horse_id'].map(mother_map).fillna(df.loc[mask, 'mother'])
    df.loc[mask, 'bms'] = df.loc[mask, 'horse_id'].map(bms_map).fillna(df.loc[mask, 'bms'])

    print("Saving to CSV...")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print("Done.")

if __name__ == "__main__":
    print("--- Checking JRA ---")
    fill_pedigree(os.path.join(PROJECT_ROOT, "data", "raw", "database.csv"))
    print("\n--- Checking NAR ---")
    fill_pedigree(os.path.join(PROJECT_ROOT, "data", "raw", "database_nar.csv"))
