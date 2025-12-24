import sys
import os

# Create path to scraper module
sys.path.append(os.path.join(os.getcwd(), 'scraper'))

from auto_scraper import scrape_odds_for_race

race_id = "202506050601" # Nakayama 1R Today
print(f"Testing Odds Scrape for {race_id}...")

try:
    odds = scrape_odds_for_race(race_id)
    print(f"Result count: {len(odds)}")
    print(odds)
except Exception as e:
    print(f"Error: {e}")
