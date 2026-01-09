print("SCRIPT STARTING...", flush=True)

import requests
from bs4 import BeautifulSoup
import re
import time
import random

# ==========================================
# Shared Logic
# ==========================================

TRAINER_CACHE = {}

def get_trainer_fullname(url, default_name, mode="JRA"):
    if not url: return default_name
    if url in TRAINER_CACHE: return TRAINER_CACHE[url]
    
    try:
        # Rate limit
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        base_domain = "https://race.netkeiba.com" if mode == "JRA" else "https://nar.netkeiba.com"
        if url.startswith('/'): url = f"{base_domain}{url}"
        
        r = requests.get(url, headers=headers, timeout=5)
        r.encoding = 'EUC-JP'
        s = BeautifulSoup(r.text, 'html.parser')
        
        title = s.title.text if s.title else ""
        m = re.search(r'^([^|]+)のプロフィール', title)
        if m:
            fullname = m.group(1).strip()
            TRAINER_CACHE[url] = fullname
            return fullname
            
        h1 = s.select_one('div.id_visual h1')
        if h1:
             txt = h1.text.strip().split()[0]
             TRAINER_CACHE[url] = txt
             return txt
    except:
        pass
    TRAINER_CACHE[url] = default_name
    return default_name

def test_jra_race(race_id):
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    try:
        time.sleep(0.5)
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if resp.status_code != 200: return None
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        if "レース結果" not in soup.title.text and not soup.find("table", summary="レース結果"):
             return None

        tables = soup.find_all('table')
        result_table = None
        for table in tables:
            if '着順' in table.text and '馬名' in table.text:
                result_table = table
                break
        if not result_table: return None
        
        rows = result_table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 14: continue
            
            stable_col = cells[13]
            raw_text = stable_col.text.strip()
            t_link = stable_col.find('a')
            t_url = t_link['href'] if t_link else None
            
            parts = [p for p in raw_text.replace('\n', ' ').split() if p.strip()]
            stable_val = ""
            temp_name = ""
            
            if len(parts) >= 2:
                stable_val = parts[0]
                temp_name = parts[-1]
            elif len(parts) == 1:
                if raw_text.startswith("美浦") or raw_text.startswith("栗東"):
                     stable_val = raw_text[:2]
                     temp_name = raw_text[2:]
                else:
                     temp_name = raw_text
            
            trainer_val = get_trainer_fullname(t_url, temp_name, mode="JRA")
            
            return {
                "race_id": race_id,
                "raw_text": raw_text.replace('\n', '\\n'),
                "stable": stable_val,
                "trainer": trainer_val,
                "url": t_url
            }
        return None
    except Exception:
        return None

def test_nar_race(race_id):
    url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"
    try:
        time.sleep(0.5)
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if resp.status_code != 200: return None
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        if "レース結果" not in soup.title.text and not soup.find("table", summary="レース結果"):
             return None

        tables = soup.find_all('table')
        result_table = None
        for table in tables:
            if '着順' in table.text and '馬名' in table.text:
                result_table = table
                break
        if not result_table: return None
        
        rows = result_table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 13: continue
            
            stable_col = cells[12]
            raw_text = stable_col.text.strip()
            t_link = stable_col.find('a')
            t_url = t_link['href'] if t_link else None
            
            stable_val = ""
            trainer_val = ""
            
            affiliates = ["北海道", "岩手", "水沢", "盛岡", "浦和", "船橋", "大井", "川崎", 
                          "金沢", "笠松", "愛知", "名古屋", "兵庫", "園田", "姫路", "高知", "佐賀",
                          "美浦", "栗東", "JRA", "地方", "海外", "仏国"]
            
            temp_name = raw_text
            for aff in affiliates:
                if raw_text.startswith(aff):
                    stable_val = aff
                    temp_name = raw_text[len(aff):].strip()
                    break
            
            trainer_val = get_trainer_fullname(t_url, temp_name, mode="NAR")
            
            return {
                "race_id": race_id,
                "raw_text": raw_text.replace('\n', '\\n'),
                "stable": stable_val,
                "trainer": trainer_val,
                "url": t_url
            }
        return None
    except:
        return None

# ==========================================
# ID Fetcher Logic
# ==========================================

def get_kaisai_dates(year, month, mode='JRA'):
    base_domain = "race.netkeiba.com" if mode == 'JRA' else "nar.netkeiba.com"
    cal_url = f"https://{base_domain}/top/calendar.html?year={year}&month={month}"
    try:
        print(f"  [DEBUG] Fetching Calendar {year}/{month}...", flush=True)
        r = requests.get(cal_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        r.encoding = 'EUC-JP'
        soup = BeautifulSoup(r.text, 'html.parser')
        links = soup.select('a[href*="race_list.html?kaisai_date="]')
        dates = []
        for link in links:
            m = re.search(r'kaisai_date=(\d+)', link['href'])
            if m: dates.append(m.group(1))
        return sorted(list(set(dates)))
    except Exception as e:
        print(f"  [ERROR] {e}", flush=True)
        return []

def get_race_ids_from_date(date_str, mode='JRA'):
    base_domain = "race.netkeiba.com" if mode == 'JRA' else "nar.netkeiba.com"
    # Important: use race_list_sub.html
    url = f"https://{base_domain}/top/race_list_sub.html?kaisai_date={date_str}"
    try:
        time.sleep(0.5)
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        r.encoding = 'EUC-JP'
        soup = BeautifulSoup(r.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'race_id=\d+'))
        ids = []
        for link in links:
            m = re.search(r'race_id=(\d+)', link['href'])
            if m: ids.append(m.group(1))
        return sorted(list(set(ids)))
    except:
        return []

def get_valid_race_ids(year, mode="JRA", limit=2):
    ids = []
    months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    if mode == "NAR": months = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
    
    for month in months:
        dates = get_kaisai_dates(year, month, mode)
        if not dates: continue
        
        # Try dates sequentially until we get limit IDs
        for date_str in dates: 
            day_ids = get_race_ids_from_date(date_str, mode)
            if day_ids:
                random.shuffle(day_ids)
                needed = limit - len(ids)
                ids.extend(day_ids[:needed])
            if len(ids) >= limit: return ids[:limit]
            
    return ids

def run_sampling():
    print("IMPORTS DONE. Starting Logic...", flush=True)
    years = range(2020, 2027)
    
    print("\n=== JRA Verification (Sampled via Calendar) ===", flush=True)
    print(f"{'Year':<5} | {'Race ID':<12} | {'Raw Text':<15} | {'Stable':<6} | {'Trainer':<12} | {'URL Found'}", flush=True)
    print("-" * 80, flush=True)
    
    for year in years:
        if year > 2025: pass
        
        print(f"DEBUG: Processing JRA {year}...", flush=True)
        rids = get_valid_race_ids(year, mode="JRA", limit=2)
        if not rids:
            if year > 2025:
                 print(f"{year:<5} | (No data yet)", flush=True)
            else:
                 print(f"{year:<5} | No IDs found (Scan failed)", flush=True)
            continue
            
        for rid in rids:
            res = test_jra_race(rid)
            if res:
                 print(f"{year:<5} | {res['race_id']:<12} | {res['raw_text'][:15]:<15} | {res['stable']:<6} | {res['trainer']:<12} | {'Yes' if res['url'] else 'No'}", flush=True)

    print("\n=== NAR Verification (Sampled via Calendar) ===", flush=True)
    print(f"{'Year':<5} | {'Race ID':<12} | {'Raw Text':<15} | {'Stable':<6} | {'Trainer':<12} | {'URL Found'}", flush=True)
    print("-" * 80, flush=True)
    
    for year in years:
         if year > 2025: pass
         
         print(f"DEBUG: Processing NAR {year}...", flush=True)
         rids = get_valid_race_ids(year, mode="NAR", limit=2)
         if not rids:
            if year > 2025:
                 print(f"{year:<5} | (No data yet)", flush=True)
            else:
                 print(f"{year:<5} | No IDs found (Scan failed)", flush=True)
            continue
            
         for rid in rids:
            res = test_nar_race(rid)
            if res:
                 print(f"{year:<5} | {res['race_id']:<12} | {res['raw_text'][:15]:<15} | {res['stable']:<6} | {res['trainer']:<12} | {'Yes' if res['url'] else 'No'}", flush=True)
    
    print("\nVerification complete.", flush=True)

if __name__ == "__main__":
    run_sampling()
