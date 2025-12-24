import sys
import os
import requests
from bs4 import BeautifulSoup
import re

race_id = "202506050601"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"--- Debugging Race {race_id} ---")

# Method 1: API
url = f"https://race.netkeiba.com/odds/odds_get_form.html?type=b1&race_id={race_id}"
print(f"Fetching API: {url}")
try:
    r = requests.get(url, headers=headers, timeout=10)
    r.encoding = r.apparent_encoding
    print(f"Status: {r.status_code}")
    print(f"Length: {len(r.text)}")
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Check key elements
    tan_block = soup.select_one('#odds_tan_block')
    print(f"Has #odds_tan_block: {tan_block is not None}")
    
    rows = soup.select('#odds_tan_block .RaceOdds_HorseList_Table tbody tr')
    print(f"Rows found (Selector 1): {len(rows)}")
    
    if not rows:
        rows = soup.select('.RaceOdds_HorseList_Table tbody tr')
        print(f"Rows found (Selector 2): {len(rows)}")
        
    if rows:
        print("Sampling Row 1:")
        print(rows[0].prettify())

except Exception as e:
    print(f"API Error: {e}")

print("\n--- Fallback Main Page ---")
# Method 2: Main
url_main = f"https://race.netkeiba.com/odds/index.html?race_id={race_id}"
print(f"Fetching Main: {url_main}")
try:
    r = requests.get(url_main, headers=headers, timeout=10)
    # Netkeiba often uses EUC-JP
    r.encoding = 'EUC-JP'
    print(f"Status: {r.status_code}")
    
    soup = BeautifulSoup(r.text, 'html.parser')
    title = soup.title.text if soup.title else "No Title"
    print(f"Title: {title}")
    
    table = soup.select_one('table#Ninki') # Popularity table sometimes used
    print(f"Has table#Ninki: {table is not None}")
    
    # Check for *any* table
    tables = soup.find_all('table')
    print(f"Total tables: {len(tables)}")
    for i, t in enumerate(tables):
        cls = t.get('class', [])
        cw = t.text[:30].replace('\n', '')
        print(f"Table {i}: Class={cls} Content={cw}")

    # Check for specific odds elements
    odds_spans = soup.select('.Odds')
    print(f"Elements with .Odds: {len(odds_spans)}")

except Exception as e:
    print(f"Main Error: {e}")
