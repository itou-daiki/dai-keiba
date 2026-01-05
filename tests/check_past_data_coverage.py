
import pandas as pd
import os

def check_past_data():
    csv_path = "data/raw/database.csv"
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    print(f"Loading {csv_path}...")
    # Load only necessary columns to save memory if file is huge
    # But we need to know what columns exist first.
    # So read output header first.
    
    try:
        df_iter = pd.read_csv(csv_path, iterator=True, chunksize=1000)
        df_head = next(df_iter)
        columns = df_head.columns.tolist()
        
        past_cols = [c for c in columns if c.startswith("past_") and c.endswith("_date")]
        past_cols.sort()
        
        if not past_cols:
            print("No 'past_N_date' columns found!")
            print("Columns sample:", columns[:20])
            return

        print(f"Found past columns: {past_cols}")
        
        # Now process full file for stats
        print("Calculating coverage...")
        total_rows = 0
        counts = {c: 0 for c in past_cols}
        
        # Re-read from start
        for chunk in pd.read_csv(csv_path, usecols=past_cols, chunksize=10000):
            total_rows += len(chunk)
            for c in past_cols:
                counts[c] += chunk[c].notna().sum()
        
        print(f"Total Rows: {total_rows}")
        for c in past_cols:
            count = counts[c]
            rate = (count / total_rows) * 100 if total_rows > 0 else 0
            print(f"{c}: {count} ({rate:.1f}%)")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_past_data()
