import subprocess
from bs4 import BeautifulSoup
import urllib.parse
import sys

def fetch_links():
    url = "https://www.jra.go.jp/datafile/seiseki/replay/2025/index.html"
    print(f"Fetching {url} via curl...")
    
    try:
        # Use curl
        cmd = ["curl", "-s", url]
        result = subprocess.run(cmd, capture_output=True, text=False) # Get bytes
        
        if result.returncode != 0:
            print(f"Curl Error: {result.stderr}")
            return

        # Decode assuming Shift_JIS
        html = result.stdout.decode('cp932', errors='replace')
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all links
        links = soup.find_all('a')
        print(f"Found {len(links)} links.")
        
        print(f"Printing first 50 links...")
        
        count = 0
        for link in links:
            href = link.get('href')
            if href:
                full = urllib.parse.urljoin(url, href)
                print(f"Link: {link.text.strip()} -> {full}")
                count += 1
                if count >= 50: break


                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_links()

