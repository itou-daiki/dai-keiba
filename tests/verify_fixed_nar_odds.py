
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from scraper.auto_scraper import scrape_odds_for_race

def test_nar_odds():
    # 2025-12-29 Oi Race 1 (from todays_data_nar.json)
    race_id = "202544122901"
    
    print(f"Testing odds scraping for {race_id} (NAR)...")
    
    odds = scrape_odds_for_race(race_id, mode="NAR")
    
    print(f"Result Count: {len(odds)}")
    if odds:
        print("Sample Data:")
        for o in odds[:None]: # All
            print(o)
    else:
        print("No odds returned.")

if __name__ == "__main__":
    test_nar_odds()
