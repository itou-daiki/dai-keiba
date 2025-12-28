
import pandas as pd
import os
import sys

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.feature_engineering import process_data

def verify_structure():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/raw/database.csv")
    if not os.path.exists(db_path):
        print("DB not found")
        return

    print("Loading DB...")
    df = pd.read_csv(db_path, nrows=500) # Use small subset for speed checking structure
    
    print("Processing...")
    # Mock minimal cols if needed? process_data handles missing cols gracefully usually
    _, stats = process_data(df, use_venue_features=False, return_stats=True)
    
    # Inspect Stable
    print("\n--- Stable Stats ---")
    if 'stable' in stats:
        s_stats = stats['stable']
        print(f"Type: {type(s_stats)}")
        print(f"Keys: {list(s_stats.keys())[:5]}")
        print(f"Len: {len(s_stats)}")
        
        if 'win_rate' in s_stats:
            print("  Has 'win_rate' key")
            print(f"  win_rate type: {type(s_stats['win_rate'])}")
        else:
             print("  MISSING 'win_rate' key")
    else:
        print("Missing 'stable' key in stats")

    # Inspect Jockey
    print("\n--- Jockey Stats ---")
    if 'jockey' in stats:
        j_stats = stats['jockey']
        print(f"Type: {type(j_stats)}")
        print(f"Keys: {list(j_stats.keys())[:5]}")
        print(f"Len: {len(j_stats)}")
    else:
        print("Missing 'jockey' key")

if __name__ == "__main__":
    verify_structure()
