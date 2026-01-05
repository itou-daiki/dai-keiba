import sys
import os
import pandas as pd
from time import sleep

# Ensure scraper is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
try:
    import auto_scraper
except ImportError:
    from scraper import auto_scraper

# Target races (Recent major races to ensure we get data)
# 2023 Arima Kinen: 202306050811
# 2023 Japan Cup: 202305050812
# 2023 Derby: 202305021211
race_ids = [
    "202306050811", 
    "202305050812", 
    "202305021211"
]

all_data = []

print("Generating sample data...")
for rid in race_ids:
    print(f"Scraping {rid}...")
    try:
        df = auto_scraper.scrape_race_data(rid)
        if df is not None and not df.empty:
            all_data.append(df)
        sleep(2)
    except Exception as e:
        print(f"Error {rid}: {e}")

if all_data:
    new_df = pd.concat(all_data, ignore_index=True)
    
    # Path to database.csv
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "database.csv")
    
    if os.path.exists(csv_path):
        try:
            existing = pd.read_csv(csv_path)
            # Reconcile columns
            combined = pd.concat([existing, new_df], ignore_index=True)
        except:
            combined = new_df
    else:
        combined = new_df
        
    # Deduplicate
    if 'race_id' in combined.columns and '馬名' in combined.columns:
        combined = combined.drop_duplicates(subset=['race_id', '馬名'], keep='last')
        
    combined.to_csv(csv_path, index=False)
    print(f"Saved {len(new_df)} rows to {csv_path}. Total: {len(combined)}")
    print("Columns:", combined.columns.tolist())
else:
    print("No data fetched.")
