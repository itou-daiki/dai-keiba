import pandas as pd
import os

def verify_file(path):
    print(f"Checking {path}...")
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return
    
    try:
        df = pd.read_parquet(path)
        print(f"✅ Loaded {len(df)} rows. Columns: {len(df.columns)}")
    except Exception as e:
        print(f"❌ Failed to load: {e}")

if __name__ == "__main__":
    verify_file("ml/processed_data.parquet")
    verify_file("ml/processed_data_nar.parquet")
