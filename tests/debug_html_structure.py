import requests
from bs4 import BeautifulSoup

url = "https://race.netkeiba.com/race/shutuba.html?race_id=202506050701"
print(f"Fetching {url}")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
r = requests.get(url, headers=headers)
r.encoding = 'EUC-JP' # Netkeiba uses EUC-JP usually
soup = BeautifulSoup(r.content, 'html.parser')

rows = soup.select("tr.HorseList")
print(f"Found {len(rows)} rows")

for i, row in enumerate(rows):
    if i > 2: break
    jockey_elem = row.select_one(".Jockey a")
    if jockey_elem:
        print(f"--- Row {i} ---")
        print(f"Text: '{jockey_elem.text}'")
        print(f"Title: '{jockey_elem.get('title')}'")
        print(f"Href: '{jockey_elem.get('href')}'")
        print(f"Attrs: {jockey_elem.attrs}")
        
        # Check parent too
        parent = jockey_elem.parent
        print(f"Parent Attrs: {parent.attrs}")
    else:
        print(f"--- Row {i} (No Jockey Link) ---")
