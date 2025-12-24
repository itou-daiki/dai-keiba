import sys
import os
import pandas as pd
import traceback

# Add paths
sys.path.append(os.path.abspath('scraper'))
sys.path.append(os.path.abspath('ml'))

import auto_scraper
import feature_engineering

RACE_ID = "202545121701" # Kawasaki 1R
MODE = "NAR"

print(f"--- 1. Scraping Shutuba Data for {RACE_ID} ({MODE}) ---")
try:
    df = auto_scraper.scrape_shutuba_data(RACE_ID, mode=MODE)
    if df is not None:
        print("✅ Data fetched.")
        print("Columns:", df.columns.tolist())
        if '会場' in df.columns:
            print(f"会場: {df['会場'].iloc[0]}")
        else:
            print("❌ '会場' column is MISSING!")
    else:
        print("❌ Scrape returned None.")
        sys.exit(1)
except Exception as e:
    print(f"❌ Scrape crashed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n--- 2. Processing Data ---")
try:
    # Mimic app/public_app.py call
    processed_df = feature_engineering.process_data(df, use_venue_features=True)
    print("✅ Processed Data.")
    print("Processed Columns:", processed_df.columns.tolist())
except Exception as e:
    print(f"❌ process_data crashed: {e}")
    traceback.print_exc()

print("\n--- Done ---")
