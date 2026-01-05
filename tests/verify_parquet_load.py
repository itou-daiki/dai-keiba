import sys
import os
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test without importing public_app to avoid streamlit/model issues
def test_load_direct():
    print("Testing JRA Load (Direct Parquet)...")
    path = "data/raw/database.parquet"
    if os.path.exists(path):
        try:
             df = pd.read_parquet(path)
             print(f"✅ JRA Parquet Loaded: {len(df)} rows. Columns: {len(df.columns)}")
        except Exception as e:
             print(f"❌ JRA Parquet Load Failed: {e}")
    else:
         print("❌ JRA Parquet Not Found")

    print("\nTesting NAR Load (Direct Parquet)...")
    path_nar = "data/raw/database_nar.parquet"
    if os.path.exists(path_nar):
        try:
             df = pd.read_parquet(path_nar)
             print(f"✅ NAR Parquet Loaded: {len(df)} rows. Columns: {len(df.columns)}")
        except Exception as e:
             print(f"❌ NAR Parquet Load Failed: {e}")
    else:
         print("❌ NAR Parquet Not Found")

if __name__ == "__main__":
    test_load_direct()
