
import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
try:
    from auto_scraper import scrape_shutuba_data
except ImportError:
    from scraper.auto_scraper import scrape_shutuba_data

race_id = "202506050511" # Turquoise S
print(f"--- Debugging scrape_shutuba_data for {race_id} ---")
df = scrape_shutuba_data(race_id)

if df is not None and not df.empty:
    print(f"Data Extracted: {len(df)} rows")
    print("Columns:", df.columns.tolist())
    
    # Check Horse IDs
    print("\n--- Horse IDs ---")
    print(df[['馬 番', '馬名', 'horse_id']].head(5))
    
    # Check Past Data Enrichment (Sample)
    print("\n--- Past Data Sample (Row 0) ---")
    cols = [c for c in df.columns if 'past_1_' in c]
    print(df.iloc[0][cols])
    
    # Check Odds
    if 'Odds' in df.columns:
        print("\n--- Current Odds Column (Odds) ---")
        print(df['Odds'].head())
    elif '単勝' in df.columns:
        print("\n--- Current Odds Column (単勝) ---")
        print(df['単勝'].head())
    else:
        print("\n--- No Odds Column Found ---")
else:
    print("No data returned from scrape_shutuba_data")
