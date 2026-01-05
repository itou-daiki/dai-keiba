
import pandas as pd
import os

def update_parquet():
    base_dir = "data/raw"
    files = ["database", "database_nar"]
    
    for f in files:
        csv_path = os.path.join(base_dir, f"{f}.csv")
        parquet_path = os.path.join(base_dir, f"{f}.parquet")
        
        if os.path.exists(csv_path):
            print(f"Converting {f}.csv to parquet...")
            try:
                # Load with minimal types to handle large files
                df = pd.read_csv(csv_path, dtype={'race_id': str, 'horse_id': str}, low_memory=False)
                
                # Clean keys
                if 'horse_id' in df.columns:
                    df['horse_id'] = df['horse_id'].astype(str).str.replace(r'\.0$', '', regex=True)
                if 'race_id' in df.columns:
                    df['race_id'] = df['race_id'].astype(str).str.replace(r'\.0$', '', regex=True)
                    
                df.to_parquet(parquet_path, index=False)
                print(f"✅ Saved {parquet_path}")
            except Exception as e:
                print(f"❌ Failed to convert {f}: {e}")
        else:
            print(f"⚠️ {f}.csv not found.")

if __name__ == "__main__":
    update_parquet()
