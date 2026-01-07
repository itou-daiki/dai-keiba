
import pandas as pd
import os
import shutil
from datetime import datetime

def clean_csv(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"Cleaning {filepath}...")
    
    # 1. Backup
    backup_path = filepath + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"  Backup created: {backup_path}")

    # 2. Load Data (try low_memory=False)
    # Use on_bad_lines='skip' just in case, but we want to load and filter logic
    try:
        df = pd.read_csv(filepath, low_memory=False)
        original_len = len(df)
        print(f"  Original rows: {original_len}")
    except Exception as e:
        print(f"  Error reading file: {e}")
        return

    # 3. Identify Bad Rows
    bad_indices = []

    # Criteria 1: '日付' is NaN or doesn't look like a date/year
    if '日付' in df.columns:
        # Valid if contains '年' or '/'
        is_valid_date = df['日付'].astype(str).str.contains(r'[年/]', na=False)
        bad_indices.extend(df[~is_valid_date].index.tolist())

    # Criteria 2: '馬名' is Numeric
    if '馬名' in df.columns:
        # Coerce to numeric; non-NaN results are likely bad (since names shouldn't be numbers)
        # Note: Some horses might have number-like names? Very rare. 
        # But looking at the user's error "3", "6", "5", these are single digits (ranks/frames).
        # Real horse names are usually longer or katakana.
        numeric_names = pd.to_numeric(df['馬名'], errors='coerce')
        # Filter where numeric conversion succeeded AND original wasn't empty
        bad_name_rows = df[numeric_names.notna() & df['馬名'].notna()]
        bad_indices.extend(bad_name_rows.index.tolist())

    # Criteria 3: Remove duplicate indices
    bad_indices = sorted(list(set(bad_indices)))
    
    if bad_indices:
        print(f"  Found {len(bad_indices)} corrupted rows.")
        # Drop
        df_clean = df.drop(index=bad_indices)
        print(f"  Rows after cleaning: {len(df_clean)}")
        
        # 4. Save
        df_clean.to_csv(filepath, index=False)
        print(f"  Saved cleaned file to {filepath}")
    else:
        print("  No corrupted rows found based on criteria.")

    print("-" * 30)

if __name__ == "__main__":
    clean_csv('data/raw/database.csv')
    clean_csv('data/raw/database_nar.csv')
