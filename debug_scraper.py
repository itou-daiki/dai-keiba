import sys
import os
import pandas as pd

# Add current dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'scraper'))

from scraper.auto_scraper import scrape_race_data

# Use a recent race: 2024 Arima Kinen is too far, use 2024 Japan Cup or similar?
# 2024 Japan Cup: 202405050812 (Tokyo)
# Let's try 202405050811 (Wait, let's use a known existing ID or just try a valid one)
# 202405051212 is Japan Cup 2024
race_id = "202507020109"

print(f"Scraping {race_id}...")
df = scrape_race_data(race_id)

if df is not None:
    print("Columns:", df.columns.tolist())
    # Check Odds column
    possible_cols = [c for c in df.columns if '単勝' in c or 'Odds' in c]
    print("Odds Columns:", possible_cols)
    if possible_cols:
        print(df[possible_cols + ['馬名']].head())
    else:
        print("No Odds column found.")
else:
    print("Failed to scrape.")
