print("SCRIPT STARTING (Targeted Mode)...", flush=True)

import requests
from bs4 import BeautifulSoup
import re
import time

# ==========================================
# Shared Logic (Re-implemented for Verification)
# ==========================================

TRAINER_CACHE = {}
JOCKEY_CACHE = {}

def get_fullname_from_url(url, default_name, cache, mode="JRA"):
    if not url: return default_name
    if url in cache: return cache[url]
    
    try:
        time.sleep(0.3)
        headers = {'User-Agent': 'Mozilla/5.0'}
        base_domain = "https://race.netkeiba.com" if mode == "JRA" else "https://nar.netkeiba.com"
        if url.startswith('/'): url = f"{base_domain}{url}"
        
        # DEBUG
        print(f"DEBUG: Fetching {url}...", flush=True)
        r = requests.get(url, headers=headers, timeout=5)
        print(f"DEBUG: Status {r.status_code}", flush=True)
        
        r.encoding = 'EUC-JP'
        s = BeautifulSoup(r.text, 'html.parser')
        
        title = s.title.text if s.title else ""
        print(f"DEBUG: Title '{title}'", flush=True)

        m = re.search(r'^(.+?)(?:のプロフィール|の騎手成績|｜)', title)
        if m:
            fullname = m.group(1).strip()
            print(f"DEBUG: Hit Title -> {fullname}", flush=True)
            cache[url] = fullname
            return fullname
            
        h1 = s.find('h1') # Simpler H1 check
        if h1:
             txt = h1.text.strip().split()[0] # Split in case of "Name (Kana)"
             print(f"DEBUG: Hit H1 -> {txt}", flush=True)
             cache[url] = txt
             return txt
             
        print(f"DEBUG: No match. Defaulting to {default_name}", flush=True)
    except Exception as e:
        print(f"DEBUG: Error {e}", flush=True)
        pass
    cache[url] = default_name
    return default_name

def get_jockey_fullname(url, default_name, mode="JRA"):
    return get_fullname_from_url(url, default_name, JOCKEY_CACHE, mode)

def test_race(race_id, mode="JRA"):
    base_domain = "race.netkeiba.com" if mode == "JRA" else "nar.netkeiba.com"
    url = f"https://{base_domain}/race/result.html?race_id={race_id}"
    
    try:
        time.sleep(0.5)
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if resp.status_code != 200: return None
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        if "着順" not in soup.text: return None

        tables = soup.find_all('table')
        result_table = None
        for table in tables:
            if '着順' in table.text and '馬名' in table.text:
                result_table = table
                break
        if not result_table: return None
        
        rows = result_table.find_all('tr')
        # Skip header
        for row in rows:
            if row.find('th'): continue
            cells = row.find_all('td')
            if len(cells) < 10: continue
            
            # --- Jockey ---
            jockey_col = cells[6]
            j_text = jockey_col.text.strip()
            j_link = jockey_col.find('a')
            j_url = j_link['href'] if j_link else None
            jockey_val = get_jockey_fullname(j_url, j_text, mode=mode) if j_url else j_text
            
            # --- Weight ---
            # JRA: 14, NAR: 13
            w_idx = 14 if mode == "JRA" else 13
            weight_val = ""
            change_val = ""
            w_text = ""
            if len(cells) > w_idx:
                 w_text = cells[w_idx].text.strip()
                 m = re.search(r'(\d+)\(([\+\-\d]+)\)', w_text)
                 if m:
                     weight_val = m.group(1)
                     change_val = m.group(2)
                 else:
                     weight_val = w_text

            return {
                "race_id": race_id,
                "jockey": jockey_val,
                "weight": weight_val,
                "change": change_val,
                "raw_weight": w_text
            }
        return None
    except Exception as e:
        # print(f"Error {race_id}: {e}", flush=True)
        return None

def run_targeted():
    years = range(2020, 2027)
    
    print("\n=== JRA Targeted Verification ===", flush=True)
    print(f"{'Year':<5} | {'Race ID':<12} | {'Jockey (Full)':<18} | {'Weight'} | {'Change'}")
    print("-" * 75, flush=True)
    
    for year in years:
        if year > 2025: # Future
             print(f"{year:<5} | (Future/No Data)", flush=True)
             continue
             
        # Try Arima Kinen approx IDs
        # Nakayama (06) Kai 5 Day 8/9 R11
        candidates = [
            f"{year}06050811", f"{year}06050911", # Arima
            f"{year}05010111", # Tokyo Feb
            f"{year}09010101", # Hanshin
            f"{year}06010101", # Nakayama Jan
        ]
        
        hit = False
        for rid in candidates:
            res = test_race(rid, mode="JRA")
            if res:
                print(f"{year:<5} | {res['race_id']:<12} | {res['jockey'][:18]:<18} | {res['weight']:<6} | {res['change']}", flush=True)
                hit = True
                break
        if not hit:
            print(f"{year:<5} | -- Scan failed --", flush=True)

    print("\n=== NAR Targeted Verification ===", flush=True)
    print(f"{'Year':<5} | {'Race ID':<12} | {'Jockey (Full)':<18} | {'Weight'} | {'Change'}")
    print("-" * 75, flush=True)
    
    for year in years:
        if year > 2025:
             print(f"{year:<5} | (Future/No Data)", flush=True)
             continue
             
        # Try Tokyo Daishoten (Ooi 44, 12/29)
        candidates = [
            f"{year}44122910", f"{year}44122911", f"{year}44122909", # Tokyo Daishoten
            f"{year}45010310", # Kawasaki Jan 3
            f"{year}43010101", # Funabashi?
            f"{year}44040811", # Ooi April
        ]
        
        hit = False
        for rid in candidates:
            res = test_race(rid, mode="NAR")
            if res:
                print(f"{year:<5} | {res['race_id']:<12} | {res['jockey'][:18]:<18} | {res['weight']:<6} | {res['change']}", flush=True)
                hit = True
                break
        if not hit:
             print(f"{year:<5} | -- Scan failed --", flush=True)
             
if __name__ == "__main__":
    run_targeted()
