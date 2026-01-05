
import sys
import os
import requests
from bs4 import BeautifulSoup
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
try:
    from auto_scraper import scrape_odds_for_race
except ImportError:
    from scraper.auto_scraper import scrape_odds_for_race

race_id = "202506050511" # Turquoise S
print(f"Testing odds scraping for {race_id}...")
odds = scrape_odds_for_race(race_id)
print(f"Odds found: {len(odds)}")
if not odds:
    # Debug Main Page access directly
    print("Debug: Accessing Main Page directly...")
    url = f"https://race.netkeiba.com/odds/index.html?race_id={race_id}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.select_one('table#Ninki')
    print(f"Table #Ninki found: {table is not None}")
    if table:
        rows = table.find_all('tr')
        print(f"Rows: {len(rows)}")
        for i, row in enumerate(rows[:3]):
             row_text = row.text.strip().replace('\n', ' ')
             print(f"Row {i}: {row_text}")
             
for h in odds[:5]:
    print(h)
