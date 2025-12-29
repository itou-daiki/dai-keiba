
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from ml.feature_engineering import process_data

def verify_nar_integrity():
    print("=== Deep Verification of NAR Mode Integrity ===")
    
    db_path = "data/raw/database_nar.csv"
    if not os.path.exists(db_path):
        print("NAR Database not found. Skipping DB checks.")
        return

    print(f"Loading {db_path}...")
    df = pd.read_csv(db_path, dtype={'horse_id': str})
    
    print(f"Total Rows: {len(df)}")
    
    # 1. Check Course Type Coverage
    if 'コースタイプ' in df.columns:
        print("\n--- Course Type Distribution (Raw) ---")
        print(df['コースタイプ'].value_counts())
    
    # 2. Check Race Name Patterns (for Class)
    print("\n--- Race Name Sample (for Classify) ---")
    if 'レース名' in df.columns:
        print(df['レース名'].sample(10, random_state=42).tolist())
    
    # 3. Process Data
    print("\n--- Running Feature Engineering ---")
    processed_df = process_data(df)
    
    
    print("\n--- Processed Feature Check ---")
    print("Processed Columns:", processed_df.columns.tolist())
    
    # Class
    if 'race_class' in processed_df.columns:
        print("Race Class Distribution:")
        print(processed_df['race_class'].value_counts().sort_index())
    
    # Distance
    print("Distance Stats:")
    print(processed_df['distance_val'].describe())
    
    # Course Type Code
    print("Course Type Code (1=Turf, 2=Dirt):")
    print(processed_df['course_type_code'].value_counts())
    
    # Check for NaNs in critical features
    crit_cols = ['race_class', 'distance_val', 'course_type_code']
    for c in crit_cols:
        miss = processed_df[c].isna().sum()
        print(f"Nulls in {c}: {miss}")

    print("\nVerification Complete via Script.")

if __name__ == "__main__":
    verify_nar_integrity()
