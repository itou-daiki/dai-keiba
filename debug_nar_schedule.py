import requests
from bs4 import BeautifulSoup

def test_nar_schedule():
    url = "https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date=20241221"
    headers = { 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36" 
    }
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # NAR often uses EUC-JP
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if soup.title:
            print(f"Title: {soup.title.text}")
        else:
            print("No <title> tag found.")
            print("Response snapshot:", response.text[:200])

        # Try selectors
        # NAR Top Page usually has a different list structure?
        # Let's try finding any links with race_id
        links = soup.select('a[href*="race_id"]')
        print(f"Found {len(links)} race links.")
        if links:
            print("Sample:", links[0]['href'])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nar_schedule()
