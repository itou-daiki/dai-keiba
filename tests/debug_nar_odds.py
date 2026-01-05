
import sys
import os
import requests
from bs4 import BeautifulSoup

def inspect_nar_html():
    race_id = "202544122901"
    url = f"https://nar.netkeiba.com/odds/index.html?race_id={race_id}&type=b1"
    
    print(f"Fetching {url}...")
    headers = { "User-Agent": "Mozilla/5.0" }
    
    resp = requests.get(url, headers=headers)
    resp.encoding = 'EUC-JP'
    
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    
    # Save to file
    with open("debug_nar_odds.html", "w", encoding='utf-8') as f:
        f.write(html)
        
    print("Saved HTML to debug_nar_odds.html")
    
    # Analyze Tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables.")
    
    for i, t in enumerate(tables):
        cls = t.get('class', [])
        ids = t.get('id', '')
        print(f"Table {i}: Class={cls}, ID={ids}")
        # Peek first row
        tr = t.find('tr')
        if tr:
            print(f"  Header: {tr.text.strip()[:50]}...")

if __name__ == "__main__":
    inspect_nar_html()
