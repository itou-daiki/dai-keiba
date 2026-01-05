import requests
from bs4 import BeautifulSoup
import re

# Target: 2026 Nakayama 1R (Assumption: 202606010101)
# User said 1/5 Nakayama 1R.
# If today is Jan 4 2026, then tomorrow is Jan 5 2026.
# Race ID format: YYYY PP KK DD RR
# Nakayama is 06.
# 1st Kai, 1st Day? Or something else?
# Generally, users navigate via the app which generates the correct ID.
# Let's try to just use a known logic or ask scraper to list races.
# Or better, just try the most likely ID. 
# 1/5 is usually the start (Gold Cup etc). Nakayama Gold Cup is 11R.
# 1R is just a Maiden.
# Let's try 202606010101.

RACE_ID = "202606010211" 
URL = f"https://race.netkeiba.com/race/shutuba.html?race_id={RACE_ID}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
}

# Check Odds Page
URL = f"https://race.netkeiba.com/odds/index.html?race_id={RACE_ID}"
# URL = f"https://race.netkeiba.com/odds/index.html?race_id={RACE_ID}&type=1"

print(f"Fetching {URL}...")
try:
    resp = requests.get(URL, headers=headers)
    resp.encoding = 'EUC-JP' # Odds page usually EUC-JP
    soup = BeautifulSoup(resp.text, 'html.parser')

    print(f"Title: {soup.title.text}")
    
    # Check for specific tables
    # Scan ALL tables
    tables = soup.select('table')
    print(f"Scanning {len(tables)} tables...")
    
    for i, t in enumerate(tables):
        txt = t.text.replace("\n", " ").strip()
        print(f"Table {i} ({len(t.find_all('tr'))} rows): {txt[:50]}...")
        if "予想" in txt or "オッズ" in txt or "人気" in txt:
             print(f"  -> Found keyword in Table {i}!")
             rows = t.find_all("tr")
             for j, row in enumerate(rows):
                 if j >= 3: break
                 t = row.text.strip().replace('\n', ' ')
                 print(f"     Row {j}: {t}")
                 cols = row.find_all('td')
                 for k, col in enumerate(cols):
                     print(f"       Col {k}: {col.text.strip()}")

except Exception as e:
    print(f"Error: {e}")
