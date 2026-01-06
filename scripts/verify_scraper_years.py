import requests
import sys
import os
import time
from bs4 import BeautifulSoup

# Add scraper to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from scraper.jra_scraper import JRA_MONTH_PARAMS
except ImportError:
    print("Could not import JRA_MONTH_PARAMS. Check path.")
    JRA_MONTH_PARAMS = {}

def verify_jra_years():
    print("\n=== Verifying JRA (2020-2026) ===")
    base_url = "https://www.jra.go.jp/JRADB/accessS.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
    }
    
    years = range(2020, 2027)
    for y in years:
        s_y = str(y)
        if s_y not in JRA_MONTH_PARAMS:
            print(f"❌ Year {y}: Missing params!")
            continue
            
        # Test Month 01
        params = JRA_MONTH_PARAMS[s_y]
        if "01" not in params:
             print(f"❌ Year {y}: Missing Month 01 param!")
             continue
             
        suffix = params["01"]
        # Logic for skl00 vs skl10 (copied from jra_scraper.py)
        # Assuming current logic mostly uses pw01skl10
        # But let's check current date or rough logic
        prefix = "pw01skl10"
        # If scraper logic had > 202512 check, we follow it?
        # Actually scrape_jra_year has: prefix = "pw01skl00" if ym >= 202512 else "pw01skl10"
        # 2026 is >= 202512, so 2026 Jan -> pw01skl00
        if int(s_y + "01") >= 202512:
            prefix = "pw01skl00"
        
        cname = f"{prefix}{s_y}01/{suffix}"
        
        # Request
        try:
            time.sleep(0.5)
            resp = requests.post(base_url, data={"cname": cname}, headers=headers, timeout=10)
            resp.encoding = 'cp932'
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Check for race links (pw01srl)
                links = soup.find_all('a', onclick=lambda x: x and 'pw01srl' in x)
                count = len(links)
                if count > 0:
                    print(f"✅ Year {y}: OK ({count} race days found in Jan)")
                else:
                    # It might be offline or empty month (e.g. future 2026)
                    # For 2026, data might not exist yet, but the page should load.
                    if "開催データが存在しません" in resp.text:
                         print(f"⚠️ Year {y}: Page loaded but no data (Expected for future).")
                    else:
                         print(f"⚠️ Year {y}: Page loaded but 0 links found. Content length: {len(resp.text)}")
            else:
                 print(f"❌ Year {y}: HTTP {resp.status_code}")
                 
        except Exception as e:
            print(f"❌ Year {y}: Exception {e}")

def verify_nar_years():
    print("\n=== Verifying NAR (2020-2026) ===")
    base_url = "https://nar.netkeiba.com/top/race_list_sub.html"
    
    years = range(2020, 2027)
    for y in years:
        # Try finding a valid date in April (Start of fiscal year, usually active)
        # Try a few days until hit
        found = False
        for d in range(1, 15):
            date_str = f"{y}04{d:02}"
            url = f"{base_url}?kaisai_date={date_str}"
            try:
                time.sleep(0.5)
                resp = requests.get(url, timeout=5)
                resp.encoding = 'EUC-JP'
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Look for race list dl/dt or RaceList_Box
                    races = soup.select('.RaceList_DataItem')
                    if len(races) > 0:
                        print(f"✅ Year {y}: OK (Found races on {date_str})")
                        found = True
                        break
            except:
                pass
        
        if not found:
             # Try January for 2026 if April is future
             if y >= 2025:
                 date_str = f"{y}0105" # Try Jan 5th
                 try:
                    resp = requests.get(f"{base_url}?kaisai_date={date_str}", timeout=5)
                    if resp.status_code == 200 and len(BeautifulSoup(resp.text, 'html.parser').select('.RaceList_DataItem')) > 0:
                        print(f"✅ Year {y}: OK (Found races on {date_str})")
                        continue
                 except: pass
                 
             print(f"⚠️ Year {y}: Could not find active race day in simple check.")

if __name__ == "__main__":
    verify_jra_years()
    verify_nar_years()
