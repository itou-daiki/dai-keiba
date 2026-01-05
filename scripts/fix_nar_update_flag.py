import pandas as pd
import os

CSV_PATH = 'data/raw/database_nar.csv'

if os.path.exists(CSV_PATH):
    print(f"Reading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    
    # Check if we need to reset
    if 'past_1_odds' in df.columns and 'past_1_date' in df.columns:
        # Condition: Has Date but Missing Odds
        # Since we found 0% fill rate for odds, this is basically "Has Date"
        mask = df['past_1_date'].notna() & df['past_1_odds'].isna()
        count = mask.sum()
        
        if count > 0:
            print(f"Found {count} rows with Past Date but Missing Odds.")
            print("Resetting 'past_1_date' to NaN to force re-scraping in optimized notebook...")
            
            df.loc[mask, 'past_1_date'] = None
            
            # Save
            df.to_csv(CSV_PATH, index=False)
            print("Database updated.")
        else:
            print("No rows need resetting (Maybe odds are already filled separate?).")
    else:
        print("Columns not found.")
else:
    print("File not found.")
