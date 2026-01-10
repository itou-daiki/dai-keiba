import pandas as pd
import os

def verify_merge():
    # Paths
    basic_path = "data/raw/database_basic.csv"
    details_path = "data/raw/database_details.csv"
    
    if not os.path.exists(basic_path) or not os.path.exists(details_path):
        print("❌ Files missing.")
        return

    print("📊 Loading Data...")
    # Load with string types for IDs to emulate admin_app behavior
    df_b = pd.read_csv(basic_path, dtype={'race_id': str, 'horse_id': str})
    df_d = pd.read_csv(details_path, dtype={'race_id': str, 'horse_id': str})
    
    print(f"  Basic: {len(df_b)} rows, {len(df_b.columns)} cols")
    print(f"  Details: {len(df_d)} rows, {len(df_d.columns)} cols")
    
    # Check Duplicates in Details
    dup_d = df_d.duplicated(subset=['race_id', 'horse_id']).sum()
    if dup_d > 0:
        print(f"⚠️ Details has {dup_d} duplicate keys! (These will be dropped in merge logic)")
        df_d = df_d.drop_duplicates(subset=['race_id', 'horse_id'])
    
    # Perform Merge
    print("\n🔄 Merging...")
    merged = pd.merge(df_b, df_d, on=['race_id', 'horse_id'], how='left')
    
    print(f"  Merged: {len(merged)} rows, {len(merged.columns)} cols")
    
    # Checks
    print("\n✅ Verification Results:")
    
    # 1. Row Count Integrity
    if len(merged) == len(df_b):
        print("  ✅ Row Count Check Passed (Merged == Basic)")
    else:
        print(f"  ❌ Row Count Mismatch! Basic: {len(df_b)} vs Merged: {len(merged)}")
    
    # 2. Column Presence
    details_cols_sample = ['father', 'mother', 'past_1_date', 'past_1_horse_weight']
    missing_cols = [c for c in details_cols_sample if c not in merged.columns]
    
    if not missing_cols:
        print(f"  ✅ Details Columns Present ({', '.join(details_cols_sample)})")
    else:
        # Note: If Details file is empty/partial, these might be missing.
        # But based on header updates, they should exist in df_d.
        missing_in_details = [c for c in details_cols_sample if c not in df_d.columns]
        if missing_in_details:
             print(f"  ⚠️ Columns missing in SOURCE Details file: {missing_in_details}")
        else:
             print(f"  ❌ Columns missing in Merged but present in Source: {missing_cols}")

    # 3. Data Population Check
    # Check if 'father' is populated (non-null) for at least some rows where Details existed
    # Intersection of keys
    common_keys = pd.merge(df_b[['race_id', 'horse_id']], df_d[['race_id', 'horse_id']], on=['race_id', 'horse_id'], how='inner')
    print(f"  ℹ️  Overlapping Keys (Horses with Details): {len(common_keys)}")
    
    if len(common_keys) > 0 and 'father' in merged.columns:
        # Check null rate for overlapping rows
        merged_overlap = merged[merged['race_id'].isin(common_keys['race_id']) & merged['horse_id'].isin(common_keys['horse_id'])]
        null_father = merged_overlap['father'].isna().sum()
        print(f"     Of {len(merged_overlap)} overlapping rows, 'father' is missing in {null_father} rows.")
        if null_father < len(merged_overlap):
             print("  ✅ Data Population Check Passed (Details mapped correctly)")
        else:
             print("  ⚠️ Data Population Warning: Merged successfully but Details columns are empty?")

if __name__ == "__main__":
    verify_merge()
