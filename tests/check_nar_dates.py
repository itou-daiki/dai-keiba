
import requests
from bs4 import BeautifulSoup
import re

def check_nar_dates():
    dates = ["20260101", "20260102", "20260103"]
    
    for d in dates:
        url = f"https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date={d}"
        print(f"\nChecking {d}: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            r = requests.get(url, headers=headers)
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.text, 'html.parser')
            
            wrapper = soup.select_one('.RaceList_Box')
            items = []
            if wrapper:
                items = wrapper.select('.RaceList_DataItem')
            
            print(f"  Status: {r.status_code}")
            print(f"  Wrapper Found: {bool(wrapper)}")
            print(f"  Items Found: {len(items)}")
            
            # If 0 items, check if 'race_list.html' works better?
            if len(items) == 0:
                 url2 = f"https://nar.netkeiba.com/top/race_list.html?kaisai_date={d}"
                 print(f"  [Fallback Check] {url2}")
                 r2 = requests.get(url2)
                 r2.encoding = r2.apparent_encoding
                 soup2 = BeautifulSoup(r2.text, 'html.parser')
                 items2 = soup2.select('.RaceList_DataItem')
                 print(f"  Fallback Items: {len(items2)}")

        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    check_nar_dates()
