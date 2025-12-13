import requests
from bs4 import BeautifulSoup

race_id = "202506050401" # Nakayama 1R
url = f"https://race.netkeiba.com/odds/odds_get_form.html?type=b1&race_id={race_id}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
}

print(f"Fetching {url}...")
try:
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check selectors
    rows1 = soup.select('.Shutuba_Table tbody tr')
    rows2 = soup.select('.RaceTable01 tr[class^="HorseList"]')
    
    print(f"Rows found via .Shutuba_Table tbody tr: {len(rows1)}")
    print(f"Rows found via .RaceTable01 tr[class^='HorseList']: {len(rows2)}")
    
    # Check if table exists
    tables = soup.find_all('table')
    print(f"Tables found: {len(tables)}")
    for t in tables[:3]:
        print(f" Table class: {t.get('class')}")
        
    # Save for inspection
    with open("debug_shutuba.html", "w") as f:
        f.write(response.text)
    print("Saved debug_shutuba.html")

except Exception as e:
    print(f"Error: {e}")
