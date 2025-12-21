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
        
    # Manual Request to inspect HTML if empty (or to debug split tables)
    print("\n--- Inspecting HTML Structure ---")
    base_domain = "nar.netkeiba.com" if mode == "NAR" else "race.netkeiba.com"
    url = f"https://{base_domain}/odds/index.html?race_id={race_id}&type=b1"
    print(f"Fetching {url}")
    headers = { "User-Agent": "Mozilla/5.0" }
    resp = requests.get(url, headers=headers)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Check tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables.")
    for i, t in enumerate(tables):
        cls = t.get('class', [])
        txt = t.text.replace("\n", "").strip()[:50]
        print(f"Table {i}: Class={cls}, Text={txt}")
                
    # Check if Ninki table exists
    ninki = soup.select_one('table#Ninki')
    if ninki:
         print(f"  Found #Ninki table with {len(ninki.find_all('tr'))} rows.")

if __name__ == "__main__":
    # Test with Kawasaki 11R (Past race, likely many horses)
    test_odds_fetch("202545121511", mode="NAR")
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
