import sys
import os
import pandas as pd

# Add current dir to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'scraper'))

from scraper.auto_scraper import scrape_race_data

# Use a recent race: 2024 Arima Kinen is too far, use 2024 Japan Cup or similar?
# 2024 Japan Cup: 202405050812 (Tokyo)
# Let's try 202405050811 (Wait, let's use a known existing ID or just try a valid one)
# 202405051212 is Japan Cup 2024
race_id = "202507020109"

print(f"Scraping {race_id}...")
import requests
from bs4 import BeautifulSoup

url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers)
res.encoding = res.apparent_encoding
soup = BeautifulSoup(res.text, 'html.parser')

# Inspect Race Data
racedata = soup.select_one(".RaceData01")
if racedata:
    print("RaceData01:", racedata.text.strip())
    # Often looks like: "15:35発走 / 芝2000m (右) / 天候:晴 / 馬場:良"

racedata2 = soup.select_one(".RaceData02")
if racedata2:
     print("RaceData02:", racedata2.text.strip())

# Check Title
print("Title:", soup.title.text)

# Check existing scraper output
print("-" * 20)
from scraper.auto_scraper import scrape_race_data

df = scrape_race_data(race_id)
if df is not None:
   print("Scraped Columns:", df.columns.tolist())
   target_cols = ["コースタイプ", "距離", "回り", "天候", "馬場状態"]
   print("Target Cols Data:")
   print(df[target_cols].iloc[0])
else:
   print("Scraper returned None")
