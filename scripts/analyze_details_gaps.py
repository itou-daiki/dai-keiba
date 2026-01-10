import pandas as pd
import matplotlib.pyplot as plt

def analyze_gaps():
    filepath = "data/raw/database_details.csv"
    print(f"Loading {filepath}...")
    try:
        df = pd.read_csv(filepath, dtype=str)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print(f"Total Rows: {len(df)}")
    print(f"Total Columns: {len(df.columns)}")

    # 1. Overall Null Rate per Column
    print("\n--- Column Null Rates (Top 20 worst) ---")
    null_rates = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    print(null_rates.head(20))

    # 2. Check for "Sudden Stop" (Row-wise Analysis)
    # create a "completeness score" per row (non-null count)
    df['completeness'] = df.notnull().sum(axis=1)
    
    # Plot or bin the completeness
    # If there's a drop, we might see it by index.
    
    print("\n--- Row Completeness Analysis (Binned by Index) ---")
    # Bin rows into chunks of 1000
    chunk_size = 1000
    num_chunks = (len(df) // chunk_size) + 1
    
    for i in range(num_chunks):
        start = i * chunk_size
        end = (i + 1) * chunk_size
        chunk = df.iloc[start:end]
        if chunk.empty: continue
        
        # Avg columns filled
        avg_filled = chunk.notnull().sum(axis=1).mean()
        
        # Check specific key columns
        # father, past_1_date, past_1_horse_weight
        has_father = chunk['father'].notnull().mean() * 100 if 'father' in chunk.columns else 0
        has_past1 = chunk['past_1_date'].notnull().mean() * 100 if 'past_1_date' in chunk.columns else 0
        
        print(f"Rows {start}-{end}: Avg Filled Cols={avg_filled:.1f}/{len(df.columns)}, Father={has_father:.1f}%, Past1={has_past1:.1f}%")

    # 3. Last added columns check (e.g. weight_change)
    if 'past_1_weight_change' in df.columns:
        filled_wc = df['past_1_weight_change'].notnull().sum()
        print(f"\n'past_1_weight_change' filled count: {filled_wc} / {len(df)}")
    else:
        print("\n'past_1_weight_change' column NOT FOUND.")

if __name__ == "__main__":
    analyze_gaps()
