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
    print(f"Accessing JRA URL: {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'cp932' # JRA uses Shift_JIS
        
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

        # --- Table Extraction (Custom BS4 Parsing) ---
        # Find table with "着順"
        tables = soup.find_all('table')
        target_table = None
        for tbl in tables:
            if "着順" in tbl.text and "馬名" in tbl.text:
                target_table = tbl
                break
        
        if not target_table:
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

            # Need to robustly map cells. 
            # We can use class names if available, or index.
            # Based on debug:
            # 0: place (着順)
            # 1: waku (枠) -> img alt
            # 2: num (馬番)
            # 3: horse (馬名)
            # 4: age (性齢)
            # 5: weight (斤量)
            # 6: jockey (騎手)
            # 7: time (タイム)
            # 8: margin (着差)
            # 9: corner (通過)
            # 10: f_time (上り)
            # 11: h_weight (馬体重)
            # 12: trainer (調教師)
            # 13: pop (人気)
            # * Odds is missing *

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
            
            row_data = {
                '着 順': get_text(0),
                '枠': waku_text,
                '馬 番': get_text(2),
                '馬名': get_text(3),
                '性齢': get_text(4),
                '斤量': get_text(5),
                '騎手': get_text(6),
                'タイム': get_text(7),
                '着差': get_text(8),
                'コーナー 通過順': get_text(9),
                '後3F': get_text(10),
                '馬体重 (増減)': get_text(11),
                '厩舎': get_text(12),
                '人 気': get_text(13),
                '単勝 オッズ': "0.0" # Missing in source
            }
            data.append(row_data)

        df = pd.DataFrame(data)
        
        # Add Metadata Columns
        df['日付'] = date_text
        df['会場'] = venue_text
        df['レース番号'] = race_num_text
        df['レース名'] = race_name_text
        df['重賞'] = grade_text
        
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
            "タイム","着差","人 気","単勝 オッズ","後3F","コーナー 通過順","厩舎","馬体重 (増減)","race_id"
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
    "2025": { "01": "3F", "02": "0D", "03": "DB", "04": "A9", "05": "77", "06": "45", "07": "13", "08": "E1", "09": "AF", "10": "1E", "11": "EC", "12": "D3" },
    "2024": { "01": "B3", "02": "81", "03": "4F", "04": "1D", "05": "EB", "06": "B9", "07": "87", "08": "55", "09": "23", "10": "92", "11": "60", "12": "2E" }
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
        
    print(f"=== Starting JRA Bulk Scraping for {year_str} (Period: {start_date} - {end_date}) ===")
    
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
                
                # Parse date from "2025年1月5日（日曜）..."
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
                    print(f"    Processing Day: {current_day_date}")
                else:
                    print(f"    Processing Day (Date unknown): {full_d_text[:20]}...")

                race_links_set = set()
                all_anchors = soup_day.find_all('a')
                for a in all_anchors:
                    href = a.get('href', '')
                    if 'CNAME=' in href and 'pw01sde' in href:
                        race_links_set.add(urllib.parse.urljoin(base_url, href))
                        
                for a in all_anchors:
                    onclick = a.get('onclick', '')
                    match_sde = re.search(r"doAction\('[^']+',\s*'(pw01sde[^']+)'\)", onclick)
                    if match_sde:
                        full_l = f"{base_url}?CNAME={match_sde.group(1)}"
                        race_links_set.add(full_l)

                sorted_race_links = sorted(list(race_links_set))
                print(f"      -> {len(sorted_race_links)} races.")
                
                for r_link in sorted_race_links:
                    # Check ID from link? JRA scrape_jra_race generates ID internally based on content.
                    # ID format: YYYY Venue Kai Day Num (e.g., 202506010811)
                    # We can try to parse r_link CNAME to guess ID but generated ID is safer.
                    # BUT scrape_jra_race pulls the page first.
                    # To skip WITHOUT fetching, we need to guess ID from CNAME/Link.
                    # CNAME=pw01sde... is not directly ID.
                    # However, typical JRA ID is Year+Place+Times+Day+RaceNum
                    # We might not be able to skip 100% accurately without fetching if logic is complex.
                    # But wait, scrape_jra_race returns None if fail.
                    
                    # Optimization:
                    # If we really want to skip, we need to know the ID before scraping.
                    # In JRA scraper, ID is generated: f"{year}{p_code}{kai}{day}{r_num}"
                    # Can we parse these from r_link?
                    # r_link is just a CNAME post key. Impossible to know details without fetching "day" page (which we did).
                    # We are in the loop of races for a day.
                    # We don't have race num in the loop variable easily?
                    # Actually, day page lists races.
                    # But we are iterating sorted_race_links which are just links.
                    
                    # Strategy: We must fetch the page to get metadata and generate ID.
                    # So we can't save bandwidth on generating ID, but we can save parsing/saving time?
                    # Or maybe we can't skip JRA easily without refactoring race link parsing?
                    # Actually, scrape_jra_race prints "Accessing...".
                    # Let's add skipping INSIDE scrape_jra_race if we pass existing_ids?
                    # No, scrape_jra_race usually just returns DF.
                    
                    # Compromise: We have to scrape to generate ID.
                    # But we can check before saving?
                    # No, user wants to skip *scraping*.
                    
                    # Wait, JRA scraping is "Post to get list" -> "Scrape each race".
                    # If we want to skip, we need to identify the race from the link/list.
                    # On the "Day Page", the links are generic "Selection List".
                    # However, usually the anchor text says "1R", "2R"...
                    # We parsed `all_anchors` to get links.
                    # We can try to extract Race Num from anchor text?
                    
                    # Let's try to extract race num effectively.
                    # In the loop `for a in all_anchors`, we can associate Race Num.
                    
                    # For now, to be safe and simple:
                    # We will fetch the page (lightweight compared to full browser), generate ID, and THEN if separate check in save_callback?
                    # No, the user wants "skip scraping".
                    
                    # Actually, let's look at `scrape_jra_race`.
                    # It fetches, parses, then generates ID.
                    # If we want to skip network, we need ID before fetch.
                    # JRA site structure makes this hard without parsing the day page more deeply.
                    # But we ARE parsing the day page.
                    # `soup_day` has the links.
                    # The links usually are in a table or list with "1R", "2R"...
                    
                    # Let's assume we can't easily skip JRA without logic change.
                    # BUT, we can add a check: if we scraped and generated ID, and it exists, we return None or Empty?
                    # That saves "processing" but not "fetching".
                    # But `scrape_jra_race` is the fetcher.
                    
                    # Alternative:
                    # Verify ID generation logic in `scrape_jra_year` loop?
                    # We know Year (year_str), Month (m), Day (d_day).
                    # Venue is usually consistent for the day.
                    # If we parse Venue once from Day Page title ("2回中山8日"), we know Venue/Kai/Day.
                    # Then we just need Race Num.
                    # Race Num corresponds to the link order? usually 1..12.
                    # `sorted_race_links` might sort by CNAME which might not be order.
                    
                    # Let's just implement explicit skip in `scrape_jra_race` call?
                    # Passing `existing_ids` to `scrape_jra_race` is weird.
                    
                    # Let's try to parse the Day Page better in `scrape_jra_year` to allow skipping.
                    # `full_d_text` has "1回中山1日".
                    # Match `(\d+)回(\S+)(\d+)日`
                    # If we match this, we have Kai, Venue, Day.
                    # Then for each link, if we can find "1R", "2R" in the anchor text...
                    
                    # Current logic matches `doAction` in `onclick`.
                    # Let's look at `scrape_jra_year` again.
                    # It iterates `all_anchors` and adds to set.
                    # We lose the relationship between Link and Race Num.
                    
                    # PLAN:
                    # Since JRA skipping is hard without heavy refactor, I will add `existing_race_ids` to `scrape_jra_year` signature
                    # and pass it to `scrape_jra_race`.
                    # Inside `scrape_jra_race`, we fetch (unavoidable potentially), generate ID.
                    # IF ID exists, we return None immediately before detailed parsing?
                    # Or we just check after DF creation.
                    # The user wants "Speed up".
                    # If we fetch, we lose speed.
                    
                    # Refined Plan:
                    # Trust the Loop.
                    # Modify `scrape_jra_year` to parse metadata from the Day Page header ONCE.
                    # (Venue, Kai, Day).
                    # Then iterate links. If we can map link to Race Num (1..12), we build ID.
                    # If ID exists, skip `scrape_jra_race`.
                    
                    # But mapping link to Race Num is risky if structure changes.
                    # Let's stick to "Fetch, Generate ID, Check, Return".
                    # It still saves the overhead of creating DF?
                    # Actually `scrape_jra_race` creates DF.
                    
                    # Let's just add the param to `scrape_jra_year` but mostly use it for NAR (which iterates ID 1..12 easily if we wanted, but valid list is better).
                    # Wait, allow NAR logic to be applied.
                    # For JRA, I will leave it as "Partial Skip" (Fetch happens, but maybe we can optimize `scrape_jra_race`?).
                    
                    # Actually, let's keep it simple.
                    # Just add the param to signature for consistency.
                    # Even if JRA doesn't fully utilize it for pre-fetch skipping yet,
                    # we can implement "Check after fetch" to avoid duplicate data processing?
                    # The user asked "Is there a skip function?".
                    # For NAR there is now. JRA is harder.
                    
                    # Ok, I will add the param to `scrape_jra_year` signature but mostly ignore it for now or just check after DF?
                    # No, check `scrape_jra_race` return.
                    # Actually, if I update `colab/JRA_Scraper`, I can load existing IDs.
                    # If JRA scraper doesn't support skipping, it will re-scrape.
                    # I should try to support it.
                    
                    # In `scrape_jra_year` loop:
                    # ...
                    df = scrape_jra_race(r_link, existing_race_ids=existing_race_ids) 
                    # I need to update `scrape_jra_race` signature too.
                    
                    if df is not None and not df.empty:
                        # ...
                        pass

        except Exception as e:
            print(f"Error processing month {month}: {e}")
