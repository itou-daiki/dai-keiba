import pandas as pd
import os
import sys
import time
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.race_scraper import RaceScraper

def backfill_pedigree(csv_path="data/raw/database.csv", save_interval=100):
    """
    database.csvの空の血統データ（father, mother, bms）を補完するスクリプト
    """
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    print(f"Loading {csv_path}...")
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Ensure columns exist
    for col in ['father', 'mother', 'bms']:
        if col not in df.columns:
            df[col] = None

    # Identify horses with missing data
    # We prioritize horses that appear most recently? Or just all unique horses?
    # Unique horse_ids
    if 'horse_id' not in df.columns:
        print("Error: 'horse_id' column missing.")
        return

    # Convert to string just in case
    df['horse_id'] = df['horse_id'].astype(str)

    # Find unique horses with missing father OR mother
    # We assume if father is missing, we check.
    # Group by horse_id and take first valid? Or distribute?
    # Actually, we should build a map of horse_id -> pedigree from existing data first (if any)
    
    existing_pedigree = df.dropna(subset=['father', 'mother']).drop_duplicates('horse_id')[['horse_id', 'father', 'mother', 'bms']]
    pedigree_map = existing_pedigree.set_index('horse_id').to_dict('index')

    # Fill from internal consistency first
    print("Internal fill...")
    update_count = 0
    for idx, row in df.iterrows():
        hid = row['horse_id']
        if pd.isna(row['father']) and hid in pedigree_map:
            df.at[idx, 'father'] = pedigree_map[hid]['father']
            df.at[idx, 'mother'] = pedigree_map[hid]['mother']
            df.at[idx, 'bms'] = pedigree_map[hid]['bms']
            update_count += 1
            
    print(f"Filled {update_count} rows from existing internal data.")

    # Now identify remaining missing unique horses
    missing_mask = df['father'].isna() | (df['father'] == '')
    missing_horses = df[missing_mask]['horse_id'].unique()
    
    print(f"Found {len(missing_horses)} unique horses with missing pedigree.")
    
    if len(missing_horses) == 0:
        print("All Done!")
        return

    scraper = RaceScraper()
    
    # Process
    processed_count = 0
    updated_rows_total = 0
    
    print("Starting scraping...")
    
    try:
        for i, horse_id in enumerate(tqdm(missing_horses)):
            # Normalize ID
            horse_id = str(horse_id).replace('.0', '')
            if not horse_id or horse_id == 'nan':
                continue
                
            # Scrape
            profile = scraper.get_horse_profile(horse_id)
            if profile and profile.get('father'):
                # Update all rows for this horse
                # Using vectorized update for speed
                mask = (df['horse_id'] == horse_id) | (df['horse_id'] == str(float(horse_id)) if horse_id.isdigit() else False)
                
                df.loc[mask, 'father'] = profile['father']
                df.loc[mask, 'mother'] = profile['mother']
                df.loc[mask, 'bms'] = profile['bms']
                
                updated_rows_total += mask.sum()
                
            processed_count += 1
            
            # Save incrementally
            if processed_count % save_interval == 0:
                print(f"Saving progress... ({processed_count}/{len(missing_horses)})")
                df.to_csv(csv_path, index=False)
                
            # Be polite
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nInterrupted by user. Saving current progress...")
    except Exception as e:
        print(f"\nError: {e}")
        pass
    finally:
        print("Saving final state...")
        df.to_csv(csv_path, index=False)
        print(f"Done. Updated rows roughly: {updated_rows_total}")

if __name__ == "__main__":
    backfill_pedigree()
