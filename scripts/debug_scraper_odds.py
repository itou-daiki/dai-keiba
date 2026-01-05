import sys
import os
import pandas as pd

# Add scraper to path
sys.path.append(os.path.join(os.getcwd(), 'scraper'))

from auto_scraper import scrape_race_data

def debug_odds():
    # Test race from DB that had 0.0 odds
    target_id = "202201010101" 
    
    print(f"Debug Scraping Race ID: {target_id}")
    
    # Run scraper
    # Note: scrape_race_data might print errors if it fails
    df = scrape_race_data(target_id)
    
    if df is None:
        print("Scraper returned None. ID might be invalid or network error.")
        return

    print(f"\nScraped DF Columns: {df.columns.tolist()}")
    
    if '単勝 オッズ' in df.columns:
        print("\nOdds Column Head:")
        print(df['単勝 オッズ'].head(20))
        print("\nUnique Values:")
        print(df['単勝 オッズ'].unique())
    else:
        print("\n'単勝 オッズ' column MISSING!")
        # Print all columns to see what we got
        print(df.head(1).to_string())

if __name__ == "__main__":
    debug_odds()
