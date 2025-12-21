import sys
import os
import requests
from bs4 import BeautifulSoup
import re

# Add scraper dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
from auto_scraper import scrape_odds_for_race

def test_odds_fetch(race_id, mode="NAR"):
    print(f"Testing Odds Fetch for Race ID: {race_id} (Mode: {mode})")
    
    odds = scrape_odds_for_race(race_id, mode=mode)
    print(f"Result count: {len(odds)}")
    print("Results:")
    for h in odds:
        print(f"  #{h['number']}: {h['odds']}")
        
    # Manual Request to inspect HTML if empty
    if not odds:
        print("\n--- Inspecting HTML ---")
        base_domain = "nar.netkeiba.com" if mode == "NAR" else "race.netkeiba.com"
        url = f"https://{base_domain}/odds/index.html?race_id={race_id}"
        print(f"Fetching {url}")
        resp = requests.get(url)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Check tables
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables.")
        for i, t in enumerate(tables):
            cls = t.get('class', [])
            txt = t.text.replace("\n", "").strip()[:50]
            print(f"Table {i}: Class={cls}, Text={txt}")
            
        # Check specific broken selectors
        ninki = soup.select_one('table#Ninki')
        print(f"#Ninki table exists: {bool(ninki)}")
        
        tanfuku = soup.select('table.RaceOdds_HorseList_Table')
        print(f".RaceOdds_HorseList_Table count: {len(tanfuku)}")

if __name__ == "__main__":
    # Test with a Mizusawa race from JSON
    test_odds_fetch("202454122101", mode="NAR") # Use a likely valid recent ID or valid one from file
    # Or confirm the ID from todays_data_nar.json content earlier?
    # actually the user file had 2025 dates? "2025-12-14"? That's future/weird.
    # Ah, system time is 2025-12-21. So 2025-12-14 is past.
    # Let's try to get a race that is happening TODAY 2025-12-21
    # From JSON earlier:
    # 202554121412 (Kochi) -> This was 12/14.
    # Today is 12/21.
    # Let's try 202554122101 (Kochi 1R on 21st)?
    # Or just use the one from JSON if I saw 12/21 data?
    # I only saw 12/14 and 12/15 in the first 800 lines.
    # I'll rely on the user report implies valid race.
    # I'll try 202554122101 (Kochi 2025/12/21 1R) assuming standard ID formation.
