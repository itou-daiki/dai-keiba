import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

def scrape_jra_sample():
    # User provided URL
    url = "https://www.jra.go.jp/JRADB/accessS.html?CNAME=pw01sde0109202505041020251214/54"
    
    print(f"Accessing {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        # JRA usually uses Shift_JIS or CP932
        response.encoding = 'cp932' 
        
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Race Title / Info
        # Usually in a specific class or ID. Let's look for common JRA structures or just dump title.
        # Based on curl output, there are images for race numbers, etc.
        # Let's try to find the main table.
        
        # Look for the table with "着順" (Order of Finish)
        tables = soup.find_all('table')
        target_table = None
        for tbl in tables:
            if "着順" in tbl.text and "馬名" in tbl.text:
                target_table = tbl
                break
        
        if target_table:
            print("Found result table!")
            # Use pandas to parse
            dfs = pd.read_html(io.StringIO(str(target_table)))
            if dfs:
                df = dfs[0]
                print(df.head())
                print(f"\nTotal rows: {len(df)}")
                
                # Check for specific columns
                if '馬名' in df.columns:
                    print(f"\nSample Horse: {df.iloc[0]['馬名']}")
        else:
            print("Could not find table with '着順' and '馬名'.")
            # Debug: Print first 500 chars of body text
            print("Page text sample:", soup.body.text[:500].strip())

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    scrape_jra_sample()
