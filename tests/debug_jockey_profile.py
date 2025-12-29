import requests
from bs4 import BeautifulSoup
import re

url = "https://db.netkeiba.com/jockey/result/recent/01126/"
print(f"Fetching {url}")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
r.encoding = 'EUC-JP'

soup = BeautifulSoup(r.content, 'html.parser')

title = soup.title.string if soup.title else ""
print(f"Page Title: '{title}'")

if "のプロフィール" in title:
    name = title.split("のプロフィール")[0]
    print(f"Extracted Name: '{name}'")

