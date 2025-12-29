
import pickle
import pandas as pd
import sys
import os

def check_jockey_stats():
    stats_path = "ml/models/feature_stats_nar.pkl"
    if not os.path.exists(stats_path):
        print(f"Stats file not found: {stats_path}")
        return

    print(f"Loading {stats_path}...")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    
    if 'jockey' not in stats:
        print("'jockey' key missing in stats!")
        print("Keys found:", stats.keys())
        return

    j_stats = stats['jockey']
    print(f"Jockey Stats Keys: {list(j_stats.keys())[:20]}")
    
    # Check 'win_rate' map inside
    if 'win_rate' in j_stats:
        print(f"Win Rate sample: {list(j_stats['win_rate'].items())[:5]}")
    else:
        print("'win_rate' missing in jockey stats")

    # Load raw data to compare names
    nar_csv = "data/raw/database_nar.csv"
    if os.path.exists(nar_csv):
        df = pd.read_csv(nar_csv, nrows=100)
        if '騎手' in df.columns:
            print("\nRaw CSV Jockey Names (first 10):")
            print(df['騎手'].unique()[:10])

if __name__ == "__main__":
    check_jockey_stats()
