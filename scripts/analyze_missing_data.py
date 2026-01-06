import pandas as pd
import numpy as np
import os

def analyze_missing(csv_path, mode="JRA"):
    if not os.path.exists(csv_path):
        print(f"Skipping {mode}: File not found ({csv_path})")
        return

    print(f"\n{'='*40}")
    print(f"Analyzing {mode} Missing Data: {os.path.basename(csv_path)}")
    print(f"{'='*40}")
    
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        print(f"Error loading {csv_path}: {e}")
        return

    total_rows = len(df)
    
    # 1. Filter out New Horse Races (Shinba)
    # Common terms: "新馬", "2歳新馬", "3歳新馬", "メイクデビュー"
    # Note: Regex selection
    shinba_mask = df['レース名'].astype(str).str.contains('新馬|メイクデビュー', na=False)
    target_df = df[~shinba_mask].copy()
    
    print(f"Total Rows: {total_rows}")
    print(f"Shinba (excluded): {shinba_mask.sum()}")
    print(f"Target Rows (Non-Shinba): {len(target_df)}")
    
    if len(target_df) == 0:
        print("No non-shinba races found.")
        return

    # 2. Check for Missing History (past_1_date)
    # If past_1_date is null, we likely missed the history scrape
    missing_history = target_df[target_df['past_1_date'].isnull()]
    missing_hist_count = len(missing_history)
    
    print(f"Missing History (past_1_date): {missing_hist_count} / {len(target_df)} ({missing_hist_count/len(target_df)*100:.1f}%)")
    
    # 3. Check for Missing Pedigree (father)
    missing_pedigree = target_df[target_df['father'].isnull()]
    missing_ped_count = len(missing_pedigree)
    
    print(f"Missing Pedigree (father): {missing_ped_count} / {len(target_df)} ({missing_ped_count/len(target_df)*100:.1f}%)")
    
    # 4. Analyze Patterns (if missing > 0)
    if missing_hist_count > 0:
        print("\n--- Missing History Patterns ---")
        # By Year
        missing_history['year'] = pd.to_datetime(missing_history['日付'], format='%Y年%m月%d日', errors='coerce').dt.year
        print("Top 5 Missing Years:")
        print(missing_history['year'].value_counts().head())
        
        # By Venue
        print("\nTop 5 Missing Venues:")
        print(missing_history['venue'].value_counts().head() if 'venue' in missing_history.columns else missing_history['会場'].value_counts().head())

    if missing_ped_count > 0:
        print("\n--- Missing Pedigree Patterns ---")
        # By Year
        missing_pedigree['year'] = pd.to_datetime(missing_pedigree['日付'], format='%Y年%m月%d日', errors='coerce').dt.year
        print("Top 5 Missing Years:")
        print(missing_pedigree['year'].value_counts().head())

if __name__ == "__main__":
    analyze_missing('data/raw/database.csv', mode="JRA")
    analyze_missing('data/raw/database_nar.csv', mode="NAR")
