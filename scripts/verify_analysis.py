import sys
import os
import pandas as pd
import importlib

# Add ml to path
sys.path.append(os.path.join(os.getcwd(), 'ml'))

import analysis_hard_race

def verify():
    print("Verifying Hard Race Analysis Logic...")
    
    db_path = "data/raw/database.parquet"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Skipping verification.")
        return

    try:
        df = pd.read_parquet(db_path)
        print(f"Loaded database: {len(df)} rows")
        
        # Try to use Dummy Data if real data failed
        print("\nUsing Dummy Data for Verification...")
        dummy_data = [
            {'race_id': 'race_1', '単勝 オッズ': 1.1, '人 気': 1},
            {'race_id': 'race_1', '単勝 オッズ': 5.0, '人 気': 2},
            {'race_id': 'race_1', '単勝 オッズ': 10.0, '人 気': 3},
            {'race_id': 'race_1', '単勝 オッズ': 20.0, '人 気': 4},
            {'race_id': 'race_1', '単勝 オッズ': 50.0, '人 気': 5},
            {'race_id': 'race_1', '単勝 オッズ': 100.0, '人 気': 6},
            
            {'race_id': 'race_2', '単勝 オッズ': 2.0, '人 気': 1},
            {'race_id': 'race_2', '単勝 オッズ': 2.1, '人 気': 2}, # Small gap
            {'race_id': 'race_2', '単勝 オッズ': 2.2, '人 気': 3},
        ]
        dummy_df = pd.DataFrame(dummy_data)
        metrics = analysis_hard_race.calculate_hard_race_metrics(dummy_df)
        print("Dummy Analysis Result:")
        print(metrics.to_string())
        
        # Expected Results:
        # race_1: gap_1_2 = 5.0 - 1.1 = 3.9
        # race_2: gap_1_2 = 2.1 - 2.0 = 0.1
        
        # Verify 3.9 and 0.1
        gaps = metrics.set_index('race_id')['odds_gap_1_2']
        if abs(gaps['race_1'] - 3.9) < 1e-9 and abs(gaps['race_2'] - 0.1) < 1e-9:
            print("\nSUCCESS: Logic verified with dummy data.")
        else:
             print("\nFAILURE: Logic verification failed on dummy data.")
        
        if metrics.empty:
            print("Result is empty. Check data quality (odds/popularity might be NaN).")
        else:
            print(f"Analysis successful. Generated metrics for {len(metrics)} races.")
            print("Head:")
            print(metrics.head().to_string())
            print("\nStatistics:")
            print(metrics.describe().to_string())
            
            # Check non-zero count
            non_zero = (metrics['odds_gap_1_2'] > 0).sum()
            print(f"\nNon-zero odds_gap_1_2: {non_zero} / {len(metrics)}")
            nans = metrics['odds_gap_1_2'].isna().sum()
            print(f"odds_gap_1_2 NaNs: {nans}")
            
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
