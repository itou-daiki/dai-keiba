import requests
from bs4 import BeautifulSoup
import re

def test_jra_fetch():
    year = 2024
    month = 1
    url = f"https://race.netkeiba.com/top/calendar.html?year={year}&month={month}"
    print(f"Fetching JRA Calendar: {url}")
    
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Status: {r.status_code}")
    r.encoding = 'EUC-JP'
    
    soup = BeautifulSoup(r.text, 'html.parser')
    links = soup.select('a[href*="race_list.html?kaisai_date="]')
    print(f"Found {len(links)} day links.")
    
    if not links:
        print("DEBUG HTML (first 500 chars):")
        print(soup.text[:500])
        return

    first_date_link = links[0]['href']
    m = re.search(r'kaisai_date=(\d+)', first_date_link)
    if m:
        date_str = m.group(1)
        print(f"First Date: {date_str}")
        
        # Test Sub List
        sub_url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date_str}"
        print(f"Fetching Sub List: {sub_url}")
        r2 = requests.get(sub_url, headers={'User-Agent': 'Mozilla/5.0'})
        r2.encoding = 'EUC-JP'
        soup2 = BeautifulSoup(r2.text, 'html.parser')
        
        race_links = soup2.find_all('a', href=re.compile(r'race_id=\d+'))
        print(f"Found {len(race_links)} race links.")
        if race_links:
            print(f"Sample ID: {race_links[0]['href']}")
            
if __name__ == "__main__":
    test_jra_fetch()
