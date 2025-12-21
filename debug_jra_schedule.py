
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def test_jra_schedule():
    # Use a recent Saturday or Sunday for JRA
    # 2024/12/21 is Saturday (Today)
    url = "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=20241221"
    headers = { "User-Agent": "Mozilla/5.0" }
    
    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers)
    resp.encoding = resp.apparent_encoding
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    print(f"Title: {soup.title.text if soup.title else 'None'}")
    
    # Check structure
    boxes = soup.select('.RaceList_Box')
    print(f"Found {len(boxes)} '.RaceList_Box' elements.")
    
    if boxes:
        print("--- Box 0 Children ---")
        for c in boxes[0].find_all(recursive=False):
            print(f"Tag: {c.name}, Text: {c.text.strip()[:30]}")
            
    # Try existing parsing logic
    items = soup.select('.RaceList_DataList .RaceList_DataItem')
    if not items:
         items = soup.select('.RaceList_Box .RaceList_DataItem')
         
    print(f"Found {len(items)} items using old selectors.")
    
    if items:
        item = items[0]
        print("--- Item 0 ---")
        print(item.prettify())
        
        # Check Item02
        m02 = item.select_one('.RaceList_Item02')
        print(f"Item02: {m02.text.strip() if m02 else 'None'}")

if __name__ == "__main__":
    test_jra_schedule()
