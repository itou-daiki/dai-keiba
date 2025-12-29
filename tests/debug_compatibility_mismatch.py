import pandas as pd
import pickle
import sys
import os
import re

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml.feature_engineering import clean_jockey, clean_stable_name

def load_stats(mode='JRA'):
    path = f'ml/models/feature_stats.pkl' if mode == 'JRA' else 'ml/models/feature_stats_nar.pkl'
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    print(f"File not found: {path} (cwd: {os.getcwd()})")
    return None

def debug_mismatch(mode='JRA'):
    print(f"\n========== Debugging {mode} Compatibility Keys ==========")
    stats = load_stats(mode)
    if not stats:
        print(f"Stats file for {mode} not found.")
        return

    hj_stats = stats.get('hj_compatibility', {})
    tj_stats = stats.get('tj_compatibility', {}) # Corrected key name

    print(f"Loaded Stats: HJ Keys={len(hj_stats)}, TJ Keys={len(tj_stats)}")
    
    # Check key name in stats dict (stats export might iterate over tj_compatibility but store as ?)
    # In feature_engineering.py: stats_data['trainer_jockey_compatibility'] = ...
    # Wait, earlier I wrote `df['trainer_jockey_compatibility']` logic.
    # Let's verify what keys are actually IN the pickle.
    print(f"Stats Top Level Keys: {list(stats.keys())}")
    
    # Load Sample Data
    csv_path = 'data/raw/database.csv' if mode == 'JRA' else 'data/raw/database_nar.csv'
    if not os.path.exists(csv_path):
        print(f"Data file {csv_path} not found.")
        return

    df = pd.read_csv(csv_path, nrows=500) # Check recent 500 rows
    print(f"Loaded 500 rows from {csv_path}")

    # Simulate Key Generation
    df['jockey_clean'] = df['騎手'].astype(str).apply(clean_jockey)
    
    if 'horse_id' in df.columns:
        df['h_key'] = df['horse_id'].astype(str).apply(lambda x: str(int(float(x))) if x.replace('.','',1).isdigit() else str(x))
    else:
        df['h_key'] = "UNKNOWN"

    if '厩舎' in df.columns:
        df['t_key'] = df['厩舎'].astype(str).apply(clean_stable_name)
    else:
        df['t_key'] = ""

    df['hj_key'] = df['h_key'] + '_' + df['jockey_clean']
    df['tj_key'] = df['t_key'] + '_' + df['jockey_clean']

    # Check Matches
    hj_matches = 0
    tj_matches = 0
    
    mismatches = []
    
    sample_hj_values = []
    sample_tj_values = []

    for i, row in df.iterrows():
        h_key = row['hj_key']
        t_key = row['tj_key']
        
        h_match = h_key in hj_stats
        t_match = t_key in tj_stats
        
        if h_match: hj_matches += 1
        if t_match: tj_matches += 1
        
        if not h_match and not t_match:
            # Check if jockey or stable exists separately?
            # Just print sample mismatches
            if len(mismatches) < 5:
                mismatches.append(f"Row {i}: HJ='{h_key}'(Found={h_match}), TJ='{t_key}'(Found={t_match})")
        
        # Collect sample values
        if h_match and len(sample_hj_values) < 5:
            sample_hj_values.append(f"{h_key}: {hj_stats[h_key]}")
        if t_match and len(sample_tj_values) < 5:
            sample_tj_values.append(f"{t_key}: {tj_stats[t_key]}")

    print(f"HJ Match Rate: {hj_matches}/{len(df)} ({hj_matches/len(df):.1%})")
    print(f"TJ Match Rate: {tj_matches}/{len(df)} ({tj_matches/len(df):.1%})")
    
    print("\n--- Sample Values (HJ) ---")
    for v in sample_hj_values: print(v)
    print("\n--- Sample Values (TJ) ---")
    for v in sample_tj_values: print(v)

    
    if mismatches:
        print("\nSample Mismatches (Neither found):")
        for m in mismatches:
            print(m)
            
    # Inspect a few Keys from Stats to see format
    print("\n--- Sample Keys from Stats (HJ) ---")
    print(list(hj_stats.keys())[:5])
    print("\n--- Sample Keys from Stats (TJ) ---")
    print(list(tj_stats.keys())[:5])

if __name__ == "__main__":
    debug_mismatch('JRA')
    debug_mismatch('NAR')
