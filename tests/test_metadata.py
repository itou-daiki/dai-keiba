
import sys
import os
import pandas as pd

sys.path.append(os.getcwd())
from scraper.race_scraper import RaceScraper

def test_metadata_fetch():
    race_id = "202506010101" 
    print(f"Testing metadata fetch for race_id: {race_id}")
    
    scraper = RaceScraper()
    data = scraper.get_race_metadata(race_id)
    
    print("Result:")
    print(data)
    
    if data and data.get('course_type') and data.get('distance'):
        print("SUCCESS: Metadata fetched.")
    else:
        print("FAILURE: Metadata missing or incomplete.")
        # Debug: try to fetch manually to see what's wrong
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
        print(f"Debug: Try accessing {url}")

if __name__ == "__main__":
    test_metadata_fetch()
