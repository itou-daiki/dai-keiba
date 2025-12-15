import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
from datetime import datetime
import urllib.parse
import time

def scrape_jra_race(url):
    """
    Scrapes a single race page from JRA website.
    Returns a pandas DataFrame matching the schema of database.csv.
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
            
        # Race Name extraction attempts
        race_name_text = ""
        name_elem = soup.select_one(".race_name")
        if name_elem:
            race_name_text = name_elem.text.strip()

        # Grade
        grade_text = ""
        if "G1" in str(soup) or "ＧⅠ" in str(soup): grade_text = "G1"
        elif "G2" in str(soup) or "ＧⅡ" in str(soup): grade_text = "G2"
        elif "G3" in str(soup) or "ＧⅢ" in str(soup): grade_text = "G3"

        # --- Table Extraction ---
        tables = soup.find_all('table')
        target_table = None
        for tbl in tables:
            if "着順" in tbl.text and "馬名" in tbl.text:
                target_table = tbl
                break
        
        if not target_table:
            return None

        dfs = pd.read_html(io.StringIO(str(target_table)))
        if not dfs:
            return None
        
        df = dfs[0]
        
        # --- Column Mapping ---
        rename_map = {
            '着順': '着 順',
            '枠番': '枠',
            '枠': '枠', 
            '馬番': '馬 番',
            '馬名': '馬名',
            '性齢': '性齢',
            '負担重量': '斤量',
            '騎手': '騎手',
            'タイム': 'タイム',
            '着差': '着差',
            '人気': '人 気',
            '単勝': '単勝 オッズ', 
            '単勝オッズ': '単勝 オッズ',
            '上り': '後3F',
            '推定上り': '後3F',
            '通過': 'コーナー 通過順',
            '調教師': '厩舎',
            '馬体重': '馬体重 (増減)'
        }
        
        df.rename(columns=rename_map, inplace=True)
        
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
        df['race_id'] = generated_id

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

def scrape_jra_year(year_str, start_date=None, end_date=None, save_callback=None):
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
                    df = scrape_jra_race(r_link)
                    if df is not None and not df.empty:
                        if save_callback:
                            save_callback(df)
                    time.sleep(0.5)

        except Exception as e:
            print(f"Error processing month {month}: {e}")
