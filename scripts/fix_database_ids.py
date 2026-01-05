
import pandas as pd
import os
import sys

def fix_database_ids():
    csv_path = 'data/raw/database.csv'
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    print(f"Reading {csv_path}...")
    try:
        # Read without dtype spec first to let pandas handle mixed types, then clean
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print(f"Original shape: {df.shape}")
    
    # Function to clean ID columns
    def clean_id(val):
        if pd.isna(val) or val == '':
            return None
        s = str(val)
        if s.endswith('.0'):
            return s[:-2]
        return s

    cols_to_fix = ['race_id', 'horse_id']
    changed = False

    for col in cols_to_fix:
        if col in df.columns:
            print(f"Cleaning column: {col}...")
            # Check if any look like floats
            # We can just apply the cleaning blindly to be safe
            original = df[col].copy()
            df[col] = df[col].apply(clean_id)
            
            # Simple check if anything changed
            # (Comparing series with NaNs is tricky, just assume if we ran it, it's good)
            # But let's check a sample
            print(f"  Sample after clean: {df[col].dropna().iloc[0] if not df[col].dropna().empty else 'N/A'}")
            changed = True
        else:
            print(f"Warning: Column {col} not found.")

    if changed:
        print("Saving cleaned CSV...")
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print("Done.")
    else:
        print("No changes made.")

if __name__ == "__main__":
    fix_database_ids()
