

import requests
from bs4 import BeautifulSoup
import re

def test_parsing_reproduction():
    # 12/22 (Mizusawa date)
    url = "https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date=20241222"
    headers = { "User-Agent": "Mozilla/5.0" }
    
    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = resp.apparent_encoding
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    print(f"Title: {soup.title.text if soup.title else 'No Title'}")
    
    # -----------------------------------------------
    # LOGIC FROM auto_scraper.py
    # -----------------------------------------------
    print("\n--- Running Logic ---")
    wrapper = soup.select_one('.RaceList_Box')
    
    venue_blocks = []
    if wrapper:
        venue_blocks = wrapper.find_all('dl', recursive=False)
    
    if not venue_blocks:
          print(" ! No venue blocks (dl) found recursively.")
          if wrapper and wrapper.name == 'dl':
              print(" ! Wrapper is dl.")
              venue_blocks = [wrapper]
          else:
              print(" ! Fallback to flat list.")
              
    print(f"Found {len(venue_blocks)} venue blocks.")
    
    venue_item_pairs = []
    
    for i, block in enumerate(venue_blocks):
        print(f"\n[Block {i}] Tag: {block.name}")
        venue_name = "Unknown"
        dt = block.select_one('dt')
        if dt:
            txt = dt.text.replace("\n", " ").strip()
            print(f"  Header Text: {txt}")
            m = re.search(r'(\S+?)競馬場', txt)
            if m:
                venue_name = m.group(1)
            else:
                match_v = re.search(r'(帯広|門別|盛岡|水沢|浦和|船橋|大井|川崎|金沢|笠松|名古屋|園田|姫路|高知|佐賀)', txt)
                if match_v:
                    venue_name = match_v.group(1)
        
        print(f"  > Venue Identified: {venue_name}")
        
        sub_items = block.select('.RaceList_DataItem')
        print(f"  > Items in block: {len(sub_items)}")
        
        for it in sub_items:
             # Check race title to see if it matches user report
             title_elem = it.select_one('.RaceList_ItemTitle')
             rt = title_elem.text.strip() if title_elem else "No Title"
             print(f"    - {rt}")
             venue_item_pairs.append((venue_name, it))
             
    print(f"\nTotal Pairs: {len(venue_item_pairs)}")

if __name__ == "__main__":
    test_parsing_reproduction()
