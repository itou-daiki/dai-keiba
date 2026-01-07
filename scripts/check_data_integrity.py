
import pandas as pd
import sys
import os

def check_file(filepath):
    print(f"Checking {filepath}...")
    if not os.path.exists(filepath):
        print("File not found.")
        return

    # Load with low_memory=False to see mapped types
    try:
        df = pd.read_csv(filepath, low_memory=False)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    issues = []
    
    # Check 1: '馬名' should not be numeric
    if '馬名' in df.columns:
        # strict check: if it can be coerced to float, it might be a shift (unless name is "8" or something weird, but unusual)
        # Actually some Japanese names might be numbers? No.
        # But Horse ID is numeric. If Horse Name is numeric, it might be a shift.
        
        # Try to convert to numeric. If successful, it's suspicious.
        numeric_names = pd.to_numeric(df['馬名'], errors='coerce')
        suspicious_rows = df[numeric_names.notna()]
        if len(suspicious_rows) > 0:
            print(f"⚠️ Suspicious '馬名' (Numeric) found in {len(suspicious_rows)} rows.")
            print(suspicious_rows[['日付', '馬名']].head())
            issues.append("Numeric Horse Name")

    # Check 2: '日付' should contain '年' or '/'
    if '日付' in df.columns:
        # Check rows where '日付' doesn't contain '年' and doesn't contain '/'
        # Handle non-string
        non_string_dates = df[~df['日付'].astype(str).str.contains(r'[年/]', na=True)]
        if len(non_string_dates) > 0:
             print(f"⚠️ Suspicious '日付' (Format) found in {len(non_string_dates)} rows.")
             print(non_string_dates[['日付']].head())
             issues.append("Invalid Date Format")

    # Check 3: '単勝 オッズ' should be numeric
    if '単勝 オッズ' in df.columns:
         # Coerce to numeric. If NaN (and original wasn't empty), it's an issue.
         # But '---' is common for cancelled.
         odds_numeric = pd.to_numeric(df['単勝 オッズ'], errors='coerce')
         # Check values that failed conversion but weren't empty strings
         failed = df[odds_numeric.isna() & df['単勝 オッズ'].notna() & (df['単勝 オッズ'].astype(str) != '')]
         # Exclude common cancellation markers if any (like '---', '取消', '除外')
         # If the value implies a shift, it would look like a horse name or date.
         
         # Filter strictly for things that look like text (Japanese)
         # Using regex to find Japanese characters in Odds
         failed_japanese = failed[failed['単勝 オッズ'].astype(str).str.contains(r'[ァ-ン一-龥]', regex=True)]
         
         if len(failed_japanese) > 0:
              print(f"⚠️ Suspicious '単勝 オッズ' (Text detected) found in {len(failed_japanese)} rows.")
              print(failed_japanese[['日付', '馬名', '単勝 オッズ']].head())
              issues.append("Text in Odds")

    # Check 4: 'venue' (会場) should be known text
    if '会場' in df.columns:
         # Just check unique values. If we see a number, it's a shift.
         venues = df['会場'].unique()
         print(f"Venues found: {venues[:20]}")
         # Simple check if any venue is numeric
         for v in venues:
             if str(v).replace('.','',1).isdigit():
                 print(f"⚠️ Numeric Venue found: {v}")
                 issues.append(f"Numeric Venue: {v}")

    if not issues:
        print("✅ No obvious column shifts detected.")
    else:
        print("❌ Potential issues detected.")
    print("-" * 30)

if __name__ == "__main__":
    check_file('data/raw/database.csv')
    check_file('data/raw/database_nar.csv')
