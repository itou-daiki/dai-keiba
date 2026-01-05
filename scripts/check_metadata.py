
import pandas as pd
import os

csv_path = 'data/raw/database.csv'
if not os.path.exists(csv_path):
    print("database.csv not found")
else:
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Total rows: {len(df)}")
    
    # Check race_id format
    print("\n[race_id samples]")
    print(df['race_id'].head())
    print("\n[race_id types]")
    print(df['race_id'].apply(type).value_counts())
    
    # Check missing metadata
    meta_cols = ['コースタイプ', '距離', '天候', '馬場状態']
    print("\n[Missing Metadata Counts]")
    for c in meta_cols:
        if c in df.columns:
            missing = df[c].isna().sum()
            print(f"{c}: {missing} missing")
        else:
            print(f"{c}: Column not found")

    # Get a sample race_id with missing metadata
    mask = df['コースタイプ'].isna()
    if mask.any():
        sample_rid = df.loc[mask, 'race_id'].iloc[0]
        print(f"\nSample race_id with missing metadata: {sample_rid} (Type: {type(sample_rid)})")
    else:
        print("\nNo rows with missing 'コースタイプ'.")
