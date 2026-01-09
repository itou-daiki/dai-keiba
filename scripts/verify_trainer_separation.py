import sys
import os
import random
import pandas as pd
from datetime import datetime

# Adjust path to find scraper modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper.jra_scraper import scrape_jra_race
from scraper.auto_scraper import scrape_race_data

def get_random_race_ids(year, count=10, mode="JRA"):
    """
    Generates random race IDs for testing.
    JRA format: YYYY PP KK DD RR
    NAR format: YYYY PP KK DD RR (PP > 30 usually)
    """
    ids = []
    
    # Simple ID generation logic for sampling
    # We might generate invalid IDs, so we'll try more and only return valid ones if we were checking validity.
    # But since we are scraping, we need valid IDs. 
    # For now, we will use known patterns or just iterate until we hit valid ones? No, that's slow.
    # Let's target specific known date ranges or venues.
    
    # Better approach might be to just construct POTENTIALLY valid IDs.
    # JRA Venues: 01-10
    # NAR Venues: 30-55
    
    venues = range(1, 11) if mode == "JRA" else [42, 43, 44, 45, 46, 47, 48, 50, 51, 54, 55] # Some NAR venues
    
    for _ in range(count * 5): # Generate more candidates
        venue = random.choice(list(venues))
        kai = random.randint(1, 6)
        day = random.randint(1, 12)
        race_num = random.randint(1, 12)
        
        rid = f"{year}{venue:02}{kai:02}{day:02}{race_num:02}"
        if rid not in ids:
            ids.append(rid)
        if len(ids) >= count:
            break
            
    return ids

def verify_jra(years):
    print("\n=== Verifying JRA Scraper ===")
    
    # We'll actually use a specific KNOWN race ID provided by user as a stable test case first
    # 202001010101 (Sapporo)
    known_id = "202001010101"
    url = f"https://race.netkeiba.com/race/result.html?race_id={known_id}"
    
    print(f"Testing Known ID: {known_id}")
    try:
        df = scrape_jra_race(url)
        if df is not None and not df.empty:
            cols = ['馬名', '厩舎', '調教師'] if '調教師' in df.columns else ['馬名', '厩舎']
            print(df[cols].head(3).to_string())
        else:
            print("Failed to scrape.")
    except Exception as e:
        print(f"Error: {e}")

    # Random Sampling
    # Note: Random IDs fail often because race schedules aren't dense. 
    # Maybe skipping random sampling for now and focusing on the known use-case + a few recent ones.
    # We'll try one recent ID from 2025.
    # 202506010101 (Nakayama 2025/1/5 1R)
    recent_id = "202506010101" 
    url = f"https://race.netkeiba.com/race/result.html?race_id={recent_id}"
    print(f"\nTesting Recent ID: {recent_id}")
    try:
        df = scrape_jra_race(url)
        if df is not None and not df.empty:
            cols = ['馬名', '厩舎', '調教師'] if '調教師' in df.columns else ['馬名', '厩舎']
            print(df[cols].head(3).to_string())
        else:
            print("Failed to scrape.")
    except Exception as e:
        print(f"Error: {e}")

def verify_nar(years):
    print("\n=== Verifying NAR Scraper ===")
    
    # Known ID from User: 202030041501
    known_id = "202030041501"
    print(f"Testing Known ID: {known_id}")
    try:
        df = scrape_race_data(known_id, mode="NAR")
        if df is not None and not df.empty:
            cols = ['馬名', '厩舎', '調教師'] if '調教師' in df.columns else ['馬名', '厩舎']
            print(df[cols].head(3).to_string())
        else:
            print("Failed to scrape.")
    except Exception as e:
        print(f"Error: {e}")
        
    # Another Random NAR ID?
    # 202545010101 (Kawasaki Jan 1 2025 1R)
    recent_id = "202545010101"
    print(f"\nTesting Recent ID: {recent_id}")
    try:
        df = scrape_race_data(recent_id, mode="NAR")
        if df is not None and not df.empty:
            cols = ['馬名', '厩舎', '調教師'] if '調教師' in df.columns else ['馬名', '厩舎']
            print(df[cols].head(3).to_string())
        else:
            print("Failed to scrape.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    years = range(2020, 2027)
    verify_jra(years)
    verify_nar(years)
