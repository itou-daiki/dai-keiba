
import requests
from bs4 import BeautifulSoup
import re

def test_nar_schedule_inspect():
    # Use a date known to have races
    url = "https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date=20241221"
    headers = { "User-Agent": "Mozilla/5.0" }
    
    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers, timeout=10)
    
    print(f"Original Encoding: {resp.encoding}")
    print(f"Apparent Encoding: {resp.apparent_encoding}")
    
    # Force EUC-JP which is common for older Netkeiba pages
    # Or ISO-8859-1 is default guess if headers missing charset
    
    resp.encoding = resp.apparent_encoding
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    print(f"Title: {soup.title.text if soup.title else 'No Title'}")
    
    # Check Structure
    boxes = soup.select('.RaceList_Box')
    print(f"Found {len(boxes)} '.RaceList_Box' elements.")
    
    if boxes:
        box = boxes[0]
        print("Iterating children of first box:")
        for child in box.find_all(recursive=False):
            name = child.name
            preview = child.text.replace("\n", "").strip()[:50]
            print(f" - Tag: {name}, Text: {preview}...")
            
            if name == 'dt':
                 # Check encoding/text
                 print(f"   -> HEADER CANDIDATE: {child.text.strip()}")
            if name == 'dd':
                 # Count items
                 cnt = len(child.select('.RaceList_DataItem'))
                 print(f"   -> Contains {cnt} races.")

    if not items:
        # Try finding via ID
        items = soup.select('.RaceList_DataList .RaceList_DataItem')
        
    print(f"Found {len(items)} items.")
    
    if items:
        item = items[0]
        print("\n--- First Item Dump ---")
        print(item.prettify())
        print("-----------------------")
        
        # Try parsing Venue
        # JRA uses .RaceList_Item02
        meta = item.select_one('.RaceList_Item02')
        if meta:
            print(f"Meta (.RaceList_Item02): {meta.text.strip()}")
        else:
            print("Meta (.RaceList_Item02) NOT FOUND")
            # Try finding venue by text analysis of other classes
            print("Trying .RaceList_Item01...")
            m1 = item.select_one('.RaceList_Item01')
            if m1: print(f"Meta (.RaceList_Item01): {m1.text.strip()}")
        
        # Check title
        title_elem = item.select_one('.RaceList_ItemTitle')
        print(f"Title Elem: {title_elem.text.strip() if title_elem else 'None'}")

if __name__ == "__main__":
    test_nar_schedule_inspect()
