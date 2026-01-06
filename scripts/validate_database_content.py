import pandas as pd
import numpy as np
import sys
import re

def validate_file(filepath, mode="JRA"):
    print(f"\n{'='*40}")
    print(f"Validating {mode} Database: {filepath}")
    print(f"{'='*40}")
    
    try:
        # Load with low_memory=False to prevent dtype warnings obscuring issues
        df = pd.read_csv(filepath, low_memory=False, encoding='utf-8-sig') # Handle BOM if present
    except Exception as e:
        print(f"❌ CRITICAL: Failed to load CSV. Error: {e}")
        return

    print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
    
    errors = []
    
    # --- 1. Date Validation ---
    date_cols = [c for c in df.columns if 'date' in c.lower() or '日付' in c]
    for col in date_cols:
        # Check for non-date patterns (heuristically)
        # Expected: YYYY年MM月DD日 OR YYYY/MM/DD OR NaN
        invalid_mask = df[col].astype(str).apply(lambda x: 
            not (pd.isna(x) or x == 'nan' or x == '' or 
                 re.match(r'\d{4}年\d{1,2}月\d{1,2}日', x) or 
                 re.match(r'\d{4}/\d{1,2}/\d{1,2}', x))
        )
        if invalid_mask.any():
            bad_values = df.loc[invalid_mask, col].unique()[:5]
            errors.append(f"⚠️ Column '{col}' contains invalid dates: {bad_values}")

    # --- 2. Numeric Validation ---
    numeric_cols = ['単勝 オッズ', '距離', '斤量', '着 順', 'タイム', '人 気']
    # Also include past_X_odds, past_X_rank, past_X_time (if normalized)
    
    for col in numeric_cols:
        if col not in df.columns: continue
        
        # '着 順' often contains '除', '中', etc. So strict numeric check is tricky.
        # But '単勝 オッズ' should be float-convertible.
        if col == '単勝 オッズ':
            non_numeric = pd.to_numeric(df[col], errors='coerce').isna()
            if non_numeric.any():
                # Ignore empty strings or NaNs, but check for weird text
                bad_vals = df.loc[non_numeric, col].dropna().unique()
                valid_failures = [v for v in bad_vals if v not in ['', 'nan']]
                if valid_failures:
                    errors.append(f"❌ Column '{col}' has non-numeric values: {valid_failures[:5]}")

    # --- 3. Logic/Content Validation ---
    # Check if 'bms' (Last Col) is a number (Column Shift Indicator)
    if 'bms' in df.columns:
        # Look for pure numbers in BMS
        # Filter out NaNs/Empty
        bms_series = df['bms'].astype(str)
        # Regex for pure number (int or float)
        is_number = bms_series.str.match(r'^\d+(\.\d+)?$')
        # Filter for values > 100 (Horse name "10" is possible, but odds "12.3" or dist "1200" is suspicious)
        suspicious_mask = is_number & (pd.to_numeric(df['bms'], errors='coerce') > 20)
        
        if suspicious_mask.any():
             bad_rows = df[suspicious_mask].index[:3].tolist()
             bad_vals = df.loc[bad_rows, 'bms'].tolist()
             errors.append(f"❌ Possible Column Shift detected in 'bms' (Found numbers): {bad_vals} at indices {bad_rows}")

    # --- Summary ---
    if not errors:
        print("✅ No content irregularities found.")
    else:
        print(f"⚠️ Found {len(errors)} issues:")
        for e in errors:
            print(e)

if __name__ == "__main__":
    validate_file('data/raw/database.csv', mode="JRA")
    validate_file('data/raw/database_nar.csv', mode="NAR")
