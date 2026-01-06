import requests
from bs4 import BeautifulSoup
import datetime

def test_nar(date_str):
    url = f'https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date={date_str}'
    print(f"Testing {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers)
        resp.encoding = 'EUC-JP'
        print(f"Status: {resp.status_code}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Check for typical elements
        race_list = soup.select('.RaceList_DataItem')
        print(f"RaceList Items found: {len(race_list)}")
        
        links = soup.select('a[href*="race/result.html"]')
        print(f"Result Links found: {len(links)}")
        
        if len(links) == 0:
            print("No links found. Dumping part of HTML:")
            print(resp.text[:500])
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    # Test a date known to have races (e.g. 2024-01-01 Kawasaki?)
    # Or recent date.
    # 2025-01-01
    test_nar("20240401") 
