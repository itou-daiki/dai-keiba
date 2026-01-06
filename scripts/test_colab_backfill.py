import pandas as pd
import shutil
import os
import sys

# Add scripts path
sys.path.append('scripts')
from colab_backfill_helper import fill_bloodline_data, fill_history_data

def test_backfill():
    print("🧪 Creating Test Data Subset...")
    
    # Load Real Data
    df = pd.read_csv('data/raw/database.csv', low_memory=False)
    
    # 1. Test Bloodline (Find 5 rows with missing father)
    miss_ped = df[df['father'].isna()].head(3).copy()
    if miss_ped.empty:
        print("Skipping Bloodline Test (No missing data).")
    else:
        # Save as test_ped.csv
        test_ped_path = 'data/temp/test_ped.csv'
        miss_ped.to_csv(test_ped_path, index=False)
        
        print("\n--- Testing Bloodline Backfill ---")
        fill_bloodline_data(test_ped_path, mode="JRA")
        
        # Verify
        res = pd.read_csv(test_ped_path)
        print("Updated Bloodline Data:")
        print(res[['horse_id', 'father', 'mother']].to_markdown())

    # 2. Test History (Find 3 rows with missing history)
    miss_hist = df[df['past_1_date'].isna() & (~df['レース名'].str.contains('新馬', na=False))].head(2).copy()
    if miss_hist.empty:
        print("Skipping History Test (No missing data).")
    else:
        # Save as test_hist.csv
        test_hist_path = 'data/temp/test_hist.csv'
        miss_hist.to_csv(test_hist_path, index=False)
        
        print("\n--- Testing History Backfill ---")
        fill_history_data(test_hist_path, mode="JRA")
        
        # Verify
        res = pd.read_csv(test_hist_path)
        print("Updated History Data:")
        cols = ['horse_id', 'past_1_date', 'past_1_race_name', 'past_1_rank']
        print(res[[c for c in cols if c in res.columns]].to_markdown())

if __name__ == "__main__":
    test_backfill()
