"""
Generate Past Race History via Self-Join

This script creates past_1_*, past_2_*, ... past_5_* columns by looking up
each horse's previous races within the same database_basic.csv file.

This eliminates the need to scrape individual horse pages for race history.
Only pedigree data (father, mother, bms) still requires separate scraping.
"""

import pandas as pd
import numpy as np
from tqdm.auto import tqdm
import os

# Configuration
INPUT_PATH = 'data/raw/database_basic.csv'
OUTPUT_PATH = 'data/raw/database_with_history.csv'

# Column mappings: Basic column -> past_N field name
COLUMN_MAPPING = {
    '日付': 'date',
    '着順': 'rank',
    'タイム': 'time',
    '騎手': 'jockey',
    '馬体重': 'horse_weight',
    '増減': 'weight_change',
    '天候': 'weather',
    '馬場状態': 'condition',
    '距離': 'distance',
    'コースタイプ': 'course_type',
    '後3F': 'last_3f',
    '単勝オッズ': 'odds',
    'レース名': 'race_name',
}

def generate_past_history():
    print("📂 Loading database_basic.csv...")
    df = pd.read_csv(INPUT_PATH, dtype=str)
    print(f"   Loaded {len(df)} rows")
    
    # Convert date to datetime for comparison
    df['date_obj'] = pd.to_datetime(df['日付'], errors='coerce')
    
    # Sort by horse_id and date for efficient lookup
    df = df.sort_values(['horse_id', 'date_obj']).reset_index(drop=True)
    
    # Initialize past columns
    past_fields = list(COLUMN_MAPPING.values())
    for i in range(1, 6):
        for field in past_fields:
            df[f'past_{i}_{field}'] = ''
    
    print("\n🔄 Generating past race history via self-join...")
    
    # Group by horse_id for efficient lookup
    grouped = df.groupby('horse_id')
    
    # For each row, find previous races for that horse
    for idx in tqdm(range(len(df)), desc="Processing"):
        row = df.iloc[idx]
        horse_id = row['horse_id']
        current_date = row['date_obj']
        
        if pd.isna(current_date) or pd.isna(horse_id):
            continue
        
        # Get all races for this horse
        horse_races = grouped.get_group(horse_id)
        
        # Filter to races before current date
        past_races = horse_races[horse_races['date_obj'] < current_date]
        
        if past_races.empty:
            continue
        
        # Sort by date descending (most recent first) and take top 5
        past_races = past_races.sort_values('date_obj', ascending=False).head(5)
        
        # Fill past columns
        for i, (_, past_row) in enumerate(past_races.iterrows(), 1):
            for basic_col, field_name in COLUMN_MAPPING.items():
                if basic_col in past_row.index:
                    df.at[idx, f'past_{i}_{field_name}'] = str(past_row[basic_col]) if pd.notna(past_row[basic_col]) else ''
    
    # Drop temporary column
    df = df.drop(columns=['date_obj'])
    
    # Save result
    print(f"\n💾 Saving to {OUTPUT_PATH}...")
    df.to_csv(OUTPUT_PATH, index=False)
    
    # Stats
    has_past1 = (df['past_1_date'] != '').sum()
    print(f"\n✅ Complete!")
    print(f"   Rows with past_1 data: {has_past1} / {len(df)} ({has_past1/len(df)*100:.1f}%)")
    
    return df

if __name__ == "__main__":
    generate_past_history()
