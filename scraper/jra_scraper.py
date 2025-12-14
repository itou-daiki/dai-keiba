import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
from datetime import datetime

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
        # JRA HTML structure is complex. We try to find patterns.
        
        # --- Metadata Extraction ---
        # Look for the H1 header text
        # Example: "レース結果2025年12月14日（日曜）5回阪神4日 10レース"
        h1_elem = soup.select_one("div.header_line h1 .txt")
        full_text = h1_elem.text.strip() if h1_elem else ""
        if not full_text and soup.h1:
            full_text = soup.h1.text.strip()


        date_text = ""
        venue_text = ""
        race_num_text = ""
        kai = "01"
        day = "01"
        
        # Regex to parse specifically:
        # 2025年12月14日 ... 5回阪神4日 ... 10レース
        # Note: "レース結果" might prefix it.
        
        # Extract Date
        match_date = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', full_text)
        if match_date:
            date_text = match_date.group(1)
            
        # Extract Venue, Kai, Day
        # Pattern: (\d+)回(Venue)(\d+)日
        # Venues can be 2 chars.
        venues_str = "札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉"
        match_meta = re.search(rf'(\d+)回({venues_str})(\d+)日', full_text)
        if match_meta:
            kai = f"{int(match_meta.group(1)):02}"
            venue_text = match_meta.group(2)
            day = f"{int(match_meta.group(3)):02}"
            
        # Extract Race Num
        # Pattern: (\d+)レース
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
        # Find table with "着順"
        tables = soup.find_all('table')
        target_table = None
        for tbl in tables:
            if "着順" in tbl.text and "馬名" in tbl.text:
                target_table = tbl
                break
        
        if not target_table:
            print("Error: Could not find result table.")
            return None

        dfs = pd.read_html(io.StringIO(str(target_table)))
        if not dfs:
            return None
        
        df = dfs[0]
        
        # --- Column Mapping ---

        
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
        generated_id = f"{year}{p_code}{kai}{day}{r_num}"
        df['race_id'] = generated_id

        # Assign extracted metadata to columns
        df['日付'] = date_text
        df['会場'] = venue_text
        df['レース番号'] = race_num_text
        df['レース名'] = race_name_text
        df['重賞'] = grade_text

        
        # Ensure '単勝 オッズ' is numeric
        if '単勝 オッズ' in df.columns:
            # Clean up text (sometimes contains "---")
            df['単勝 オッズ'] = pd.to_numeric(df['単勝 オッズ'], errors='coerce').fillna(0.0)

        # Standardize '着 順'
        if '着 順' in df.columns:
             # handle "取消", "除外" etc -> keep as is or convert?
             # existing csv has mixed types or numeric? 
             # Usually standard scraper keeps them as string if mixed, or numeric
             pass

        # Select standard columns
        standard_columns = [
            "日付","会場","レース番号","レース名","重賞","着 順","枠","馬 番","馬名","性齢","斤量","騎手",
            "タイム","着差","人 気","単勝 オッズ","後3F","コーナー 通過順","厩舎","馬体重 (増減)","race_id"
        ]
        
        # Add missing columns with empty values
        for col in standard_columns:
            if col not in df.columns:
                df[col] = ""
                
        # Reorder
        df = df[standard_columns]
        
        print(f"Scraped {len(df)} rows.")
        return df

    except Exception as e:
        print(f"Error scraping JRA URL: {e}")
        return None
