import pandas as pd
import numpy as np
import sys
import re

def validate_file(filepath, mode="JRA"):
    print(f"\n{'='*40}")
    print(f"Exhaustive Validation for {mode}: {filepath}")
    print(f"{'='*40}")
    
    try:
        df = pd.read_csv(filepath, low_memory=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"❌ CRITICAL: Failed to load CSV. Error: {e}")
        return

    print(f"Total Rows: {len(df)}")
    print(f"Total Columns: {len(df.columns)}")
    
    errors = []
    
    # Iterate over EVERY column
    for col in df.columns:
        col_lower = col.lower()
        
        # 1. Date Check
        if 'date' in col_lower or '日付' in col:
            # Allow NaNs, but if present, must look like a date
            invalid = df[col].astype(str).apply(lambda x: 
                not (pd.isna(x) or x == 'nan' or x == '' or 
                     re.match(r'\d{4}[年/]\d{1,2}[月/]\d{1,2}日?', x))
            )
            if invalid.any():
                bad = df.loc[invalid, col].unique()[:3]
                errors.append(f"⚠️ [Date Error] Column '{col}': Invalid format {bad}")

        # 2. Numeric Check (Odds, Weight, Time)
        elif 'odds' in col_lower or 'オッズ' in col or 'weight' in col_lower or '体重' in col or 'time' in col_lower or 'タイム' in col or '距離' in col:
            # Time can be '1:23.4', convert to seconds check is complex, but check it's not random text
            # Here we check strict numerics for Odds/Weight/Distance
            if 'time' not in col_lower and 'タイム' not in col:
                 # Coerce to numeric
                 numeric_series = pd.to_numeric(df[col], errors='coerce')
                 # Check what became NaN but wasn't empty originally
                 original_str = df[col].astype(str).replace({'nan': '', 'None': ''})
                 bad_mask = numeric_series.isna() & (original_str != '')
                 
                 # Allow '計不' or specific racing terms if necessary, but generally should be numeric
                 if bad_mask.any():
                     bad_vals = df.loc[bad_mask, col].unique()
                     # Filter out common non-numeric placeholders if needed (e.g. '取消', '除外')
                     # specific to JRA data: '取消', '除外', '中止' are common in rank/odds
                     valid_exceptions = ['取消', '除外', '中止', '失格', '---', '--']
                     real_bad = [v for v in bad_vals if v not in valid_exceptions]
                     
                     if real_bad:
                         errors.append(f"⚠️ [Numeric Error] Column '{col}': Found non-numeric values {real_bad[:3]}")

        # 3. ID Check
        elif 'id' in col_lower and ('race' in col_lower or 'horse' in col_lower):
            # Should be digits only
            non_digit = df[col].astype(str).apply(lambda x: not (x.replace('.0','').isdigit() or pd.isna(x) or x=='nan'))
            if non_digit.any():
                 bad = df.loc[non_digit, col].unique()[:3]
                 errors.append(f"⚠️ [ID Error] Column '{col}': Found non-digits {bad}")

    if not errors:
        print(f"✅ Checked all {len(df.columns)} columns. No issues found.")
    else:
        print(f"❌ Found {len(errors)} issues.")
        for e in errors:
            print(e)
            
if __name__ == "__main__":
    validate_file('data/raw/database.csv', mode="JRA")
    validate_file('data/raw/database_nar.csv', mode="NAR")
