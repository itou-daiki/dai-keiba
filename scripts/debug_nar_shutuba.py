
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sys
import os

# Add scraper path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
import auto_scraper

def test_shutuba_parsing():
    race_id = "202536122101" # Mizusawa 1R
    print(f"Testing scrape_shutuba_data for {race_id} (NAR)...")
    
    # 1. Run the actual function
    try:
        df = auto_scraper.scrape_shutuba_data(race_id, mode="NAR")
        if df is not None:
            print(f"\nDataFrame Found: {len(df)} rows")
            print(df.columns)
            print(df[['枠', '馬 番', '馬名', '性齢', '騎手', '斤量']].head(10))
        else:
            print("DataFrame is None")
    except Exception as e:
        print(f"Error executing function: {e}")

    # 2. Inspect HTML manually to see structure
    url = f"https://nar.netkeiba.com/race/shutuba.html?race_id={race_id}"
    print(f"\nFetching {url} for inspection...")
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Inspect all tables
    tables = soup.find_all("table")
    print(f"\nFound {len(tables)} tables.")
    
    for i, tbl in enumerate(tables):
        t_classes = tbl.get("class", [])
        rows = tbl.find_all("tr")
        print(f"\n[Table {i}] Class: {t_classes}, Rows: {len(rows)}")
        
        # Print first few rows to see content
        if len(rows) > 5: # Likely the main table
             print(f"  [Detailed Inspection of Table {i}]")
             for j, r in enumerate(rows[:3]):
                 print(f"  Row {j}:")
                 for k, c in enumerate(r.find_all(['td', 'th'])):
                     print(f"    Cell {k}: Tag={c.name}, Class={c.get('class')}, Text={c.text.strip()[:10]}")
            
    # Check for Cancelled/Scratched
    print("\nChecking for .HorseList recursively in soup:")
    all_hl = soup.select(".HorseList")
    print(f"Total .HorseList elements: {len(all_hl)}")

if __name__ == "__main__":
    test_shutuba_parsing()
