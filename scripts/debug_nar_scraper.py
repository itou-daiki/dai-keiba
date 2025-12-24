import sys
import os
import requests
from bs4 import BeautifulSoup

# Adjust path to import auto_scraper
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))

import auto_scraper

def test_nar_scraping(race_id):
    print(f"Testing NAR scraping (Shutuba) for {race_id} (Mode=NAR)...")
    # scrape_shutuba_data returns a DataFrame
    df = auto_scraper.scrape_shutuba_data(race_id, mode="NAR")
    if df is not None and not df.empty:
        print("Success! Scraped DataFrame:")
        print(df.head())
        print("Columns:", df.columns.tolist())
        if 'Odds' in df.columns:
            print("Odds Sample:", df['Odds'].head().tolist())
    else:
        print("Failed to scrape.")

def inspect_nar_result(race_id):
    url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"
    print(f"--- Fetching Result {url} ---")
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Result table usually id="All_Result_Table"
        table = soup.find("table", id="All_Result_Table")
        print(f"Found Result Table: {table is not None}")
        if table:
            rows = table.find_all("tr")
            print(f"Total Rows: {len(rows)}")
            for i, r in enumerate(rows[:5]):
                print(f"  Result Row {i} classes: {r.get('class')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # ID from schedule debug: 202454122101 (Mizusawa 1R on 20241221)
    target_id = "202454122101"
    inspect_nar_result(target_id)
