import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
from datetime import datetime
import urllib.parse
import time

def scrape_jra_race(url, existing_race_ids=None):
    """
    Scrapes a single race page from JRA website.
    Returns a pandas DataFrame matching the schema of database.csv.
    If existing_race_ids is provided and the race ID is found, returns None (skip).
    """
    print(f"Accessing URL: {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Netkeiba usually uses EUC-JP, JRA uses Shift_JIS. 
        # Since this function is mostly used for Netkeiba (NAR/JRA-Backfill), default to EUC-JP.
        # response.encoding = 'cp932' 
        response.encoding = 'EUC-JP'
        
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- Metadata Extraction ---
        h1_elem = soup.select_one("div.header_line h1 .txt")
        full_text = h1_elem.text.strip() if h1_elem else ""
        if not full_text and soup.h1:
            full_text = soup.h1.text.strip()

        date_text = ""
        venue_text = ""
        race_num_text = ""
        kai = "01"
        day = "01"
        
        # Extract Date
        match_date = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', full_text)
        if match_date:
            date_text = match_date.group(1)
            
        # Extract Venue, Kai, Day
        venues_str = "札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉"
        match_meta = re.search(rf'(\d+)回({venues_str})(\d+)日', full_text)
        if match_meta:
            kai = f"{int(match_meta.group(1)):02}"
            venue_text = match_meta.group(2)
            day = f"{int(match_meta.group(3)):02}"
            
        # Extract Race Num
        match_race = re.search(r'(\d+)レース', full_text)
        if match_race:
            r_val = int(match_race.group(1))
            race_num_text = f"{r_val}R"
            r_num = f"{r_val:02}"
        else:
            race_num_text = "10R" # Fallback
            r_num = "10"
            
        # Race Name
        race_name_text = ""
        name_elem = soup.select_one(".race_name")
        if name_elem:
            race_name_text = name_elem.text.strip()

        # Grade
        grade_text = ""
        if "G1" in str(soup) or "ＧⅠ" in str(soup): grade_text = "G1"
        elif "G2" in str(soup) or "ＧⅡ" in str(soup): grade_text = "G2"
        elif "G3" in str(soup) or "ＧⅢ" in str(soup): grade_text = "G3"

        # --- Added: Course, Distance, Weather, Condition ---
        # JRA HTML structure varies, but often contained in specific divs or text lines.
        # We will scan the entire header text or specific class for these patterns.
        
        # 1. Course & Distance (e.g., "芝2000メートル", "ダート1800メートル", "芝・1600m")
        # Usually in the same block as race name or just below.
        # We search the whole header area text.
        header_text = soup.select_one("div.header_line").text if soup.select_one("div.header_line") else soup.text
        
        # Regex: Allow spaces, dots, etc. between Type and Dist
        dist_type_match = re.search(r'(芝|ダ|ダート|障害)[^0-9]*(\d+)', header_text)
        course_type = ""
        distance = ""
        
        if dist_type_match:
            c_val = dist_type_match.group(1)
            d_val = dist_type_match.group(2)
            
            if "芝" in c_val: course_type = "芝"
            elif "ダ" in c_val: course_type = "ダート"
            elif "障" in c_val: course_type = "障害"
            
            distance = int(d_val)
        
        # 1.5 Rotation (Right/Left/Straight)
        rotation = ""
        # Often formatted as "(右)" or "（左）" 
        rot_match = re.search(r'[（\(](右|左|直線)[）\)]', header_text)
        if rot_match:
            rotation = rot_match.group(1)
        else:
             # Fallback: Inference based on Venue
             # Tokyo, Chukyo, Niigata -> Left (Default), others Right
             # Niigata 1000m -> Straight
             if "左" in header_text: rotation = "左"
             elif "右" in header_text: rotation = "右"
             elif "直線" in header_text: rotation = "直線"

        
        # 2. Weather (e.g., "天候：晴")
        weather = ""
        w_match = re.search(r'天候\s*[:：]\s*(\S+)', soup.text)
        if w_match:
            weather = w_match.group(1).strip()
            
        # 3. Condition (e.g., "芝：良", "ダート：稍重")
        # Note: A race can have both if it's mixed, but usually we care about the main one or the one matching course_type.
        condition = ""
        
        # Try specific pattern based on course type
        if course_type == "芝":
             c_match = re.search(r'芝\s*[:：]\s*(\S+)', soup.text)
             if c_match: condition = c_match.group(1).strip()
        elif course_type == "ダート":
             c_match = re.search(r'ダート\s*[:：]\s*(\S+)', soup.text)
             if c_match: condition = c_match.group(1).strip()
        
        # Fallback if generic or course type unknown, grab first one found
        if not condition:
             c_match_gen = re.search(r'(?:芝|ダート)\s*[:：]\s*(\S+)', soup.text)
             if c_match_gen: condition = c_match_gen.group(1).strip()

        # --- Table Extraction (Custom BS4 Parsing) ---
        # Find table with "着順"
        tables = soup.find_all('table')
        target_table = None
        for tbl in tables:
            if "着順" in tbl.text and "馬名" in tbl.text:
                target_table = tbl
                break
        
        if not target_table:
            print(f"Warning: Result table not found in {url} (Encoding: {response.encoding})")
            return None

        # Parse Rows
        rows = target_table.find_all('tr')
        data = []
        
        for row in rows:
            # Skip header (usually th) or invalid rows
            if row.find('th'):
                continue
                
            cells = row.find_all('td')
            if not cells:
                continue

            # Correct Mapping based on standard JRA result table
            
            def get_text(idx):
                if idx < len(cells):
                    return cells[idx].get_text(strip=True)
                return ""

            # Extract Frame (Waku) from Image
            waku_text = ""
            if len(cells) > 1:
                img = cells[1].find('img')
                if img and 'alt' in img.attrs:
                    # Example: "枠6緑" -> Extract number
                    alt = img['alt']
                    m = re.search(r'枠(\d+)', alt)
                    if m:
                        waku_text = m.group(1)
                    else:
                        waku_text = alt # Fallback
            
            # Extract Horse ID
            horse_id = ""
            if len(cells) > 3:
                a_tag = cells[3].find('a')
                if a_tag and 'href' in a_tag.attrs:
                    href = a_tag['href']
                    # /horse/2018105247/
                    m = re.search(r'/horse/(\d+)', href)
                    if m:
                        horse_id = m.group(1)

            # Let's try dynamic finding for Trainer.
            trainer_raw = ""
            for i, c in enumerate(cells):
                txt = c.get_text(strip=True)
                # Trainer often has "美浦" or "栗東" or "北海道"
                if ("美浦" in txt or "栗東" in txt or "北海道" in txt or "川崎" in txt) and i > 5:
                     trainer_raw = c.get_text(separator="\n", strip=True) # Use separator to keep split
                     break
            
            # Separating Stable and Trainer
            stable_val = ""
            trainer_val = ""
            
            if trainer_raw:
                # Remove extra spaces
                # Example: "美浦\n\n青木"
                parts = [p.strip() for p in trainer_raw.split('\n') if p.strip()]
                if len(parts) >= 2:
                    stable_val = parts[0]
                    trainer_val = parts[1]
                elif len(parts) == 1:
                     # "北海道田中淳司" Combined case?
                     # Try regex split if not separated by newline
                     # Common stables: 美浦, 栗東, 北海道, 兵庫, etc.
                     # But usually JRA is separated.
                     
                     # Simple heuristic: First 2 chars are stable?
                     if parts[0].startswith("美浦") or parts[0].startswith("栗東"):
                         stable_val = parts[0][:2]
                         trainer_val = parts[0][2:].strip()
                     else:
                         trainer_val = parts[0] # Fallback
            
            # Re-mapping other cols
            # 9: Corner? 10: 3F?
            # We rely on text analysis for robustness if indices shift.
            
            row_data = {
                '着 順': get_text(0),
                '枠': waku_text,
                '馬 番': get_text(2),
                '馬名': get_text(3),
                'horse_id': horse_id,
                '性齢': get_text(4),
                '斤量': get_text(5),
                '騎手': get_text(6),
                'タイム': get_text(7),
                '着差': get_text(8),
                # Index 9 seems to be corner/passing based on previous result? No wait.
                # If 12 was corner..
                # Let's stick to the ones that worked or leave blank if unsure, 
                # but we need Trainer.
                'コーナー 通過順': get_text(12) if len(cells) > 12 else "",
                '厩舎': stable_val,   # NEW: Stable only
                '調教師': trainer_val, # NEW: Trainer name
                '人 気': get_text(9) if len(cells) > 9 else "", # Verify later
                '単勝 オッズ': "0.0" 
            }
            data.append(row_data)

        df = pd.DataFrame(data)
        
        # Add Metadata Columns
        df['日付'] = date_text
        df['会場'] = venue_text
        df['レース番号'] = race_num_text
        df['レース名'] = race_name_text
        df['重賞'] = grade_text
        df['距離'] = distance
        df['コースタイプ'] = course_type
        df['天候'] = weather
        df['天候'] = weather
        df['馬場状態'] = condition
        df['回り'] = rotation
        
        # ID Generation
        place_map = {
            "札幌": "01", "函館": "02", "福島": "03", "新潟": "04", "東京": "05",
            "中山": "06", "中京": "07", "京都": "08", "阪神": "09", "小倉": "10"
        }
        p_code = place_map.get(venue_text, "00")
        
        year = "2025"
        if date_text:
            year = date_text[:4]
            
        generated_id = f"{year}{p_code}{kai}{day}{r_num}"
        
        # SKIP CHECK
        if existing_race_ids and generated_id in existing_race_ids:
            print(f"Skipping {generated_id} (Already exists)")
            return None

        df['race_id'] = generated_id

        # Cleanups
        if '単勝 オッズ' in df.columns:
            df['単勝 オッズ'] = pd.to_numeric(df['単勝 オッズ'], errors='coerce').fillna(0.0)

        standard_columns = [
            "日付","会場","レース番号","レース名","重賞","着 順","枠","馬 番","馬名","性齢","斤量","騎手",
            "タイム","着差","人 気","単勝 オッズ","後3F","コーナー 通過順","厩舎","馬体重 (増減)","race_id",
            "距離","コースタイプ","天候","馬場状態","回り"
        ]
        
        for col in standard_columns:
            if col not in df.columns:
                df[col] = ""
                
        df = df[standard_columns]
        
        print(f"Scraped {len(df)} rows.")
        return df

    except Exception as e:
        print(f"Error scraping JRA URL: {e}")
        return None


# Parameter Map for Monthly Results (Reverse Engineered)
JRA_MONTH_PARAMS = {
    "2026": { "01": "E4", "02": "B2", "03": "80", "04": "4E", "05": "1C", "06": "EA", "07": "B8", "08": "86", "09": "54", "10": "22", "11": "F0", "12": "BE" },
    "2025": { "01": "3F", "02": "0D", "03": "DB", "04": "A9", "05": "77", "06": "45", "07": "13", "08": "E1", "09": "AF", "10": "1E", "11": "EC", "12": "D3" },
    "2024": { "01": "B3", "02": "81", "03": "4F", "04": "1D", "05": "EB", "06": "B9", "07": "87", "08": "55", "09": "23", "10": "92", "11": "60", "12": "2E" },
    "2023": { "01": "27", "02": "F5", "03": "C3", "04": "91", "05": "5F", "06": "2D", "07": "FB", "08": "C9", "09": "97", "10": "06", "11": "D4", "12": "A2" },
    "2022": { "01": "9B", "02": "69", "03": "37", "04": "05", "05": "D3", "06": "A1", "07": "6F", "08": "3D", "09": "0B", "10": "7A", "11": "48", "12": "16" },
    "2021": { "01": "0F", "02": "DD", "03": "AB", "04": "79", "05": "47", "06": "15", "07": "E3", "08": "B1", "09": "7F", "10": "EE", "11": "BC", "12": "8A" },
    "2020": { "01": "83", "02": "51", "03": "1F", "04": "ED", "05": "BB", "06": "89", "07": "57", "08": "25", "09": "F3", "10": "62", "11": "30", "12": "FE" }
}

def scrape_jra_year(year_str, start_date=None, end_date=None, save_callback=None, existing_race_ids=None):
    """
    Scrapes races for a given year and date range.
    year_str: "2024" or "2025"
    start_date: datetime.date (optional)
    end_date: datetime.date (optional)
    save_callback: function(df) to save progress
    """
    
    if year_str not in JRA_MONTH_PARAMS:
        print(f"Year {year_str} not supported in parameter map.")
        return

    params = JRA_MONTH_PARAMS[year_str]
    base_url = "https://www.jra.go.jp/JRADB/accessS.html"
    
    # Determine months to iterate
    start_m = 1
    end_m = 12
    
    if start_date:
        start_m = start_date.month
    if end_date:
        end_m = end_date.month
    
    # Cap at Today to prevent future scraping
    from datetime import date
    today = date.today()
    
    # If explicit end_date is used, respect it, but also respect today if it is earlier?
    # Usually for results, we never want future.
    if end_date:
        actual_end_date = min(end_date, today)
    else:
        actual_end_date = today
        
    print(f"=== Starting JRA Bulk Scraping for {year_str} (Period: {start_date or 'Start'} - {actual_end_date}) ===")

    # Adjust end_m based on today if we are in target year
    if int(year_str) == today.year:
        end_m = min(end_m, today.month)
    elif int(year_str) > today.year:
        print(f"Year {year_str} is in the future. Stopping.")
        return
    
    for m in range(start_m, end_m + 1):
        month = f"{m:02}"
        if month not in params:
            continue
            
        suffix = params[month]
        # Logic for skl00 vs skl10
        try:
            ym = int(year_str + month)
            prefix = "pw01skl00" if ym >= 202512 else "pw01skl10"
        except:
            prefix = "pw01skl10"

        cname = f"{prefix}{year_str}{month}/{suffix}"
        
        print(f"Fetching list for {year_str}/{month} (CNAME={cname})...")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
            }
            response = requests.post(base_url, data={"cname": cname}, headers=headers, timeout=10)
            response.encoding = 'cp932'
            
            if response.status_code != 200:
                print(f"Failed to fetch {cname} (Status {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            race_cnames = []
            links = soup.find_all('a')
            for link in links:
                onclick = link.get('onclick', '')
                match = re.search(r"doAction\('[^']+',\s*'([^']+)'\)", onclick)
                if match:
                    c = match.group(1)
                    if c.startswith('pw01srl'):
                        race_cnames.append(c)
            
            race_cnames = sorted(list(set(race_cnames)))
            print(f"  Found {len(race_cnames)} race days in month.")
            
            for day_cname in race_cnames:
                resp_day = requests.post(base_url, data={"cname": day_cname}, headers=headers, timeout=10)
                resp_day.encoding = 'cp932'
                soup_day = BeautifulSoup(resp_day.text, 'html.parser')
                
                # Check date of this day page
                day_date_text = ""
                d_h1 = soup_day.select_one("div.header_line h1 .txt")
                full_d_text = d_h1.text.strip() if d_h1 else (soup_day.h1.text.strip() if soup_day.h1 else "")
                
                # Parse date from "2025年1月5日（日曜）1回中山1日"
                # Need to match Date AND Venue/Kai/Day info for ID generation
                # Pattern: YYYY年M月D日 ... K回VenueD日
                
                current_day_date = None
                kai_str = "01"
                day_str = "01"
                venue_str = ""
                p_code = "00"
                
                match_day_date = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', full_d_text)
                if match_day_date:
                    y, mo, d_day = map(int, match_day_date.groups())
                    current_day_date = datetime(y, mo, d_day).date()
                    
                    # Filtering
                    if start_date and current_day_date < start_date:
                        print(f"    Skipping day {current_day_date} (Before start date)")
                        continue
                    if end_date and current_day_date > end_date:
                        print(f"    Skipping day {current_day_date} (After end date)")
                        continue
                    print(f"    Processing Day: {current_day_date} ({full_d_text})")
                else:
                    print(f"    Processing Day (Date unknown): {full_d_text[:20]}...")

                # Parse Venue Info for ID Generation
                venues_ptn = "札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉"
                match_meta = re.search(rf'(\d+)回({venues_ptn})(\d+)日', full_d_text)
                if match_meta:
                    kai_str = f"{int(match_meta.group(1)):02}"
                    venue_str = match_meta.group(2)
                    day_str = f"{int(match_meta.group(3)):02}"
                    
                    place_map = {
                        "札幌": "01", "函館": "02", "福島": "03", "新潟": "04", "東京": "05",
                        "中山": "06", "中京": "07", "京都": "08", "阪神": "09", "小倉": "10"
                    }
                    p_code = place_map.get(venue_str, "00")
                
                # Collect Race Links AND Race Numbers
                # Need to pair Link with Race Number
                race_list_items = []

                all_anchors = soup_day.find_all('a')
                for a in all_anchors:
                    onclick = a.get('onclick', '')
                    # Check for doAction with robust regex (handles single/double quotes, whitespace)
                    # Pattern: doAction('FormName', 'CNAME')
                    match_sde = re.search(r"doAction\s*\(\s*['\"][^'\"]+['\"]\s*,\s*['\"](pw01sde[^'\"]+)['\"]\s*\)", onclick)
                    href = a.get('href', '')
                    
                    final_url = ""
                    if match_sde:
                        final_url = f"{base_url}?CNAME={match_sde.group(1)}"
                    elif 'pw01sde' in href:
                        # Fallback for simple hrefs
                        if 'CNAME=' in href:
                             final_url = urllib.parse.urljoin(base_url, href)
                        else:
                             # If href="accessS.html?CNAME=..."
                             # or just "?CNAME=..."
                             final_url = urllib.parse.urljoin(base_url, href)
                    
                    if final_url:
                        # Extract Race Number from anchor text (e.g. "1R", "11R")
                        # Or generic image alt?
                        # Usually text is "1R" or img alt="1R"
                        txt = a.text.strip()
                        img = a.find('img')
                        if not txt and img and 'alt' in img.attrs:
                            txt = img['alt']
                        
                        r_num = -1
                        r_num_match = re.search(r'(\d+)R', txt)
                        if r_num_match:
                             r_num = int(r_num_match.group(1))
                             
                        # Append even if Race Num is not found (fix for missing races)
                        race_list_items.append((final_url, r_num))
                
                # Deduplicate by URL (keep first found usually fine)
                # Sort by Race Number (unknowns (-1) first or last?)
                seen_urls = set()
                unique_races = []
                for url, r_num in race_list_items:
                    if url not in seen_urls:
                        unique_races.append((url, r_num))
                        seen_urls.add(url)
                
                unique_races.sort(key=lambda x: x[1]) # Sort by race num (-1 will be first)
                
                print(f"      -> {len(unique_races)} races found.")

                for r_link, r_num in unique_races:
                    # PRE-FETCH OPTIMIZATION
                    # Construct ID
                    # Only if we successfully extracted Race Num and Venue info
                    if r_num != -1 and p_code != "00" and current_day_date:
                         # ID: YYYY PP KK DD RR
                         # y is from match_day_date loop var (int)
                         # p_code, kai_str, day_str strings
                         
                         # Ensure year is from the day page date
                         y_str = str(y)
                         r_num_str = f"{r_num:02}"
                         
                         generated_id = f"{y_str}{p_code}{kai_str}{day_str}{r_num_str}"
                         
                         if existing_race_ids and generated_id in existing_race_ids:
                             # print(f"        [Skip] {generated_id} (Pre-check)")
                             continue
                    
                    # If not skipped, fetch
                    df = scrape_jra_race(r_link, existing_race_ids=existing_race_ids)
                    
                    if df is not None and not df.empty:
                        if save_callback:
                            save_callback(df)
                        time.sleep(1)
        
        except Exception as e:
            print(f"Error processing month {month}: {e}")

