import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

def debug_race_columns():
    # URL from previous successful log
    url = "https://www.jra.go.jp/JRADB/accessS.html?CNAME=pw01sde1006202501010120250105/6B" 
    print(f"Fetching {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
    }
    resp = requests.get(url, headers=headers)
    resp.encoding = 'cp932'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables.")
    
    target_table = None
    for i, tbl in enumerate(tables):
        txt = tbl.text[:100].replace('\n', ' ')
        print(f"Table {i}: {txt}...")
        if "着順" in tbl.text and "馬名" in tbl.text:
            target_table = tbl
            print("  -> Identified as Result Table")
            
    if not target_table:
        print("Error: Target table not found.")
        return

    dfs = pd.read_html(io.StringIO(str(target_table)))
    df = dfs[0]
    
    print("\n=== Table Headers (HTML) ===")
    headers = target_table.find_all('th')
    for th in headers:
        print(f"TH: {th.get_text(strip=True)}")
        
    print("\n=== Raw Columns Detected ===")
    print(df.columns.tolist())
    
    print("\n=== First Row HTML ===")
    rows = target_table.find_all('tr')
    # Row 0 is likely header, Row 1 is data
    if len(rows) > 1:
        cells = rows[1].find_all(['td', 'th'])
        for i, cell in enumerate(cells):
            print(f"Cell {i}: {cell}")

if __name__ == "__main__":
    debug_race_columns()
