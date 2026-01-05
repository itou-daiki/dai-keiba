import pandas as pd
import os
import sys

# Define files with their specific directories
FILES_TO_MIGRATE = [
    {"dir": "data/raw", "filename": "database.csv"},
    {"dir": "data/raw", "filename": "database_nar.csv"},
    {"dir": "ml", "filename": "processed_data.csv"},
    {"dir": "ml", "filename": "processed_data_nar.csv"}
]

def migrate_file(file_info):
    directory = file_info["dir"]
    filename = file_info["filename"]
    
    csv_path = os.path.join(directory, filename)
    parquet_path = os.path.join(directory, filename.replace(".csv", ".parquet"))
    
    if not os.path.exists(csv_path):
        print(f"Skipping {filename}: Not found in {directory}.")
        return

    print(f"Reading {csv_path}...")
    try:
        # Read CSV with low memory option and dtype specification for critical columns
        dtype_map = {
            'race_id': str,
            'horse_id': str,
            'jockey_id': str,
            'trainer_id': str,
            'date': str # Ensure date is read as string first helps parsing later if needed
        }
        
        df = pd.read_csv(csv_path, low_memory=False, dtype=dtype_map)
        print(f"  Loaded {len(df)} rows. Columns: {len(df.columns)}")
        
        print(f"Writing to {parquet_path}...")
        try:
            df.to_parquet(parquet_path, index=False, compression='snappy')
        except Exception as e:
            print(f"  Error writing Parquet: {e}")
            try:
                print("  Retrying with engine='pyarrow' explicit...")
                df.to_parquet(parquet_path, index=False, engine='pyarrow')
            except Exception as e2:
                print(f"  Retry failed: {e2}")
                return

        # Verify sizes
        csv_size = os.path.getsize(csv_path) / (1024 * 1024)
        pq_size = os.path.getsize(parquet_path) / (1024 * 1024)
        print(f"  Success! Size reduced: {csv_size:.2f} MB -> {pq_size:.2f} MB ({(pq_size/csv_size)*100:.1f}%)")
        
    except Exception as e:
        print(f"Failed to migrate {filename}: {e}")

if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(PROJECT_ROOT) # Ensure cwd is project root
    
    for f in FILES_TO_MIGRATE:
        migrate_file(f)
