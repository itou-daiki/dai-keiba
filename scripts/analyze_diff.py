import pandas as pd
import os

files = {
    "JRA Current": "data/raw/database.csv",
    "JRA Backup": "data/raw/database_bak.csv",
    "NAR Current": "data/raw/database_nar.csv",
    "NAR Backup": "data/raw/database_nar_bak.csv"
}

for label, path in files.items():
    print(f"--- {label} ---")
    if not os.path.exists(path):
        print("  File not found.")
        continue
        
    try:
        # Load focused columns to save memory and speed up
        df = pd.read_csv(path, usecols=['日付', 'race_id'], low_memory=False)
        print(f"  Rows: {len(df)}")
        print(f"  Unique Races: {df['race_id'].nunique()}")
        
        # Date analysis
        print(f"  Sample Date: {df['日付'].iloc[0]}")
        
        # Try converting strictly with possible formats
        # Assuming YYYY年MM月DD日 or YYYY/MM/DD
        df['date'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
        if df['date'].isnull().all():
             df['date'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
             
        min_date = df['date'].min()
        max_date = df['date'].max()
        print(f"  Date Range: {min_date} to {max_date}")
        
    except Exception as e:
        print(f"  Error reading {path}: {e}")
