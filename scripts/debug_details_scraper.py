import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
import datetime

# Known Horse: Equinox (Retired 2023)
# ID: 2019105219
# We set RACE_DATE to 2025. He should have history.
JRA_HORSE_ID = "2019105219" 
JRA_RACE_DATE = "2025/01/01" 

def debug_jra_details_real():
    print(f"\n🔍 DEBUGGING JRA DETAILS (REAL REQUEST)")
    print(f"  Target: Horse {JRA_HORSE_ID} (Equinox), Race Date {JRA_RACE_DATE}")
    
    # Testing potential "Result" specific URL
    url = f"https://db.netkeiba.com/horse/result/{JRA_HORSE_ID}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://db.netkeiba.com/',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8'
    }
    
    try:
        resp = requests.get(url, headers=headers)
        resp.encoding = 'EUC-JP'
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print("  ❌ Request Failed")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Find Table
        table = soup.select_one("table.db_h_race_results")
        if not table:
             print("  ❌ 'table.db_h_race_results' NOT FOUND (Real)")
             # Check fallback
             tables = soup.find_all("table")
             for t in tables:
                if "着順" in t.text:
                    print("  ⚠️ Found table by text '着順'")
                    table = t
                    break
        
        if not table:
             print("  ❌ FATAL: No table found.")
             print(f"  Page Title: {soup.title.string if soup.title else 'No Title'}")
             # Print all tables
             tables = soup.find_all("table")
             print(f"  Found {len(tables)} tables.")
             for i, t in enumerate(tables):
                 print(f"    Table {i}: Classes={t.get('class', 'No Class')}, Text snippet: {t.text.strip().replace(chr(10), ' ')[:50]}")
             
             # Check for Race Name in text and find PARENT
             target_text = "ジャパンC"
             if target_text in soup.text:
                 print(f"  ⚠️ '{target_text}' FOUND. Searching for element...")
                 # Find the element containing the text
                 found = soup.find(string=re.compile(target_text))
                 if found:
                     parent = found.parent
                     print(f"    Text Parent: <{parent.name} class='{parent.get('class')}'>")
                     
                     # Trace up 3 levels
                     curr = parent
                     for k in range(3):
                         if curr.parent:
                             curr = curr.parent
                             print(f"      Up {k+1}: <{curr.name} class='{curr.get('class')}'>")
                 else:
                     print("    Could not locate element despite text presence.")
             else:
                 print("  ❌ Race Names NOT FOUND in text.")
             
             return

        # 2. Parse DF
        df = pd.read_html(io.StringIO(str(table)))[0]
        df = df.dropna(how='all')
        print(f"  Raw Rows: {len(df)}")
        
        # 3. Clean Columns
        df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)
        print(f"  Columns: {df.columns.tolist()}")

        # 4. Date Parsing (Robust)
        # Using the logic inserted into the notebook
        if '日付' in df.columns:
            print(f"  Sample Date Raw: '{df['日付'].iloc[0]}'")
            df['date_obj'] = pd.to_datetime(df['日付'].astype(str).str.replace('.', '/'), errors='coerce')
            valid = df['date_obj'].notna().sum()
            print(f"  Valid Dates: {valid}/{len(df)}")
        else:
            print("  ❌ '日付' column missing")
            return

        # 5. Filtering
        current_date = pd.to_datetime(JRA_RACE_DATE)
        df_filtered = df[df['date_obj'] < current_date]
        print(f"  Filtered Rows (< {JRA_RACE_DATE}): {len(df_filtered)}")
        
        if df_filtered.empty:
            print("  ❌ FILTERED DF IS EMPTY! (Date Logic Issue?)")
            print("  Top 5 Dates in DF:")
            print(df['date_obj'].head(5))
            return
        
        # 6. Extraction Check
        row = df_filtered.iloc[0]
        print("\n  --- Extraction Check (Top Row) ---")
        print(f"  Date: {getattr(row, '日付', '')}")
        print(f"  Rank: {getattr(row, '着順', '')}")
        print(f"  Race: {getattr(row, 'レース名', '')}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    debug_jra_details_real()
