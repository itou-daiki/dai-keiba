import sys
import os
import re
import requests
from bs4 import BeautifulSoup

# Add path to scraper
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scraper'))

def scrape_race_data_debug(race_id):
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    print(f"Fetching {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" 
    }
    
    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(f"Status: {response.status_code}")
    print(f"Title: {soup.title.text if soup.title else 'No Title'}")
    
    # Debug RaceData01
    racedata1 = soup.select_one(".RaceData01")
    if racedata1:
        raw_text = racedata1.text.replace("\n", "").strip()
        print(f"Raw RaceData01: '{raw_text}'")
        
        # Current Regex
        match_course = re.search(r'(芝|ダ|障)(\d+)m(?:\s*\((.*?)\))?', raw_text)
        if match_course:
            print(f"Match Group 1 (Type): '{match_course.group(1)}'")
            print(f"Match Group 2 (Dist): '{match_course.group(2)}'")
            print(f"Match Group 3 (Rot):  '{match_course.group(3)}'")
        else:
            print("Regex NO MATCH")
    else:
        print("RaceData01 element not found")

if __name__ == "__main__":
    # Test with the ID from database.csv (2025) and a 2024 one just in case
    print("--- 2025 Case ---")
    scrape_race_data_debug("202506010101")
    print("\n--- 2024 Case ---")
    scrape_race_data_debug("202406010101")
