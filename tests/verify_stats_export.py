
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.feature_engineering import process_data

def verify_stats():
    print("Loading database.csv...")
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/raw/database.csv")
    if not os.path.exists(db_path):
        print("Database not found, skipping.")
        return

    df = pd.read_csv(db_path)
    
    # Use a subset for speed
    df_small = df.tail(5000).copy()
    
    print("Processing data with return_stats=True...")
    _, stats = process_data(df_small, use_venue_features=True, return_stats=True)
    
    print("\n--- Verifying Stats Keys ---")
    required_keys = [
        'jockey', 'stable', 'hj_compatibility', 'tj_compatibility',
        'horse_turf', 'horse_dirt', 
        'horse_good', 'horse_heavy',
        'horse_dist_Sprint', 'horse_dist_Mile'
    ]
    
    all_ok = True
    for key in required_keys:
        if key in stats:
            count = len(stats[key])
            print(f"[OK] {key}: {count} items")
        else:
            print(f"[FAIL] {key} missing from stats!")
            all_ok = False
            
    if all_ok:
        print("\nAll keys present. Checking sample values...")
        # Check a sample horse
        sample_h_key = list(stats['horse_turf'].keys())[0] if stats['horse_turf'] else None
        if sample_h_key:
            print(f"Sample Horse Key: {sample_h_key}")
            print(f"  Turf Avg Rank: {stats['horse_turf'].get(sample_h_key)}")
            print(f"  Dirt Avg Rank: {stats.get('horse_dirt', {}).get(sample_h_key, 'N/A')}")
            
    print("\nVerification Complete.")

if __name__ == "__main__":
    verify_stats()
