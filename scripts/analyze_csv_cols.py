import pandas as pd
import os

csv_path = 'data/raw/database.csv'

if not os.path.exists(csv_path):
    print(f"File not found: {csv_path}")
    exit()

try:
    df = pd.read_csv(csv_path, low_memory=False)
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit()

print(f"Total Rows: {len(df)}")
print(f"Total Columns: {len(df.columns)}")

print("-" * 30)
print("Empty or Mostly Empty Columns:")
print("-" * 30)

empty_cols = []
for col in df.columns:
    missing = df[col].isnull().sum()
    percent = (missing / len(df)) * 100
    
    if percent > 0:
        print(f"{col}: {missing} missing ({percent:.1f}%)")
        if percent == 100:
            empty_cols.append(col)

print("-" * 30)
print(f"Completely Empty Columns ({len(empty_cols)}):")
print(empty_cols)
