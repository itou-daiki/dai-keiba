import pandas as pd
import sys
import os

def analyze_csv(file_path):
    print(f"Analyzing {file_path}...")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print(f"Total Rows: {len(df)}")
    print(f"Total Columns: {len(df.columns)}")
    print("-" * 30)
    
    missing_stats = []
    
    for col in df.columns:
        missing_count = df[col].isna().sum() 
        # Also count empty strings if object type
        if df[col].dtype == 'object':
            empty_str_count = (df[col] == "").sum()
            missing_count += empty_str_count
            
        missing_rate = (missing_count / len(df)) * 100
        
        if missing_count > 0:
            missing_stats.append((col, missing_count, missing_rate))

    # Sort by missing rate descending
    missing_stats.sort(key=lambda x: x[2], reverse=True)
    
    print(f"{'Column':<30} | {'Missing':<10} | {'Rate (%)':<10}")
    print("-" * 56)
    for col, count, rate in missing_stats:
        print(f"{col:<30} | {count:<10} | {rate:<10.2f}")
        
    print("-" * 56)
    if not missing_stats:
        print("No missing values found!")

if __name__ == "__main__":
    target_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/raw/database_nar.csv")
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        
    analyze_csv(target_file)
