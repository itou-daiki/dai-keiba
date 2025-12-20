import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import time
import re
from datetime import datetime, timedelta, date
import os
import sys
try:
    from jra_scraper import scrape_jra_race, scrape_jra_year
    from race_scraper import RaceScraper
except ImportError:
    # Try relative import if running as module
    from .jra_scraper import scrape_jra_race, scrape_jra_year
    from .race_scraper import RaceScraper

# ==========================================
# CONSTANTS
# ==========================================
# Root directory (parent of scraper) -> database.csv
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")
TARGET_YEARS = [2024, 2025] # Expandable

# ==========================================
# 1. レース詳細データを取得する関数
# ==========================================
def scrape_race_data(race_id):
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
    }
    
    # Initialize Scraper
    scraper = RaceScraper()

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        target_table = soup.find("table", id="All_Result_Table")
        if not target_table:
            return None

        # --- メタデータ抽出 ---
        # 日付
        date_text = ""
        title_text = soup.title.text if soup.title else ""
        match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', title_text)
        if match:
            date_text = match.group(1)

        # 会場
        venue_elem = soup.select_one(".RaceKaisaiWrap .Active")
        venue_text = venue_elem.text.strip() if venue_elem else ""

        # レース番号・名
        race_num_elem = soup.select_one(".RaceNum")
        race_num_text = race_num_elem.text.strip().replace("\n", "") if race_num_elem else ""
        
        race_name_elem = soup.select_one(".RaceName")
        race_name_text = race_name_elem.text.strip().replace("\n", "") if race_name_elem else ""

        # 重賞グレード
        grade_text = ""
        if soup.select_one(".Icon_GradeType1"): grade_text = "G1"
        elif soup.select_one(".Icon_GradeType2"): grade_text = "G2"
        elif soup.select_one(".Icon_GradeType3"): grade_text = "G3"

        # --- データフレーム化 ---
        dfs = pd.read_html(io.StringIO(str(target_table)))
        if len(dfs) > 0:
            df = dfs[0]
            df = df.replace(r'\n', '', regex=True)
            
            # Column Normalization
            # Replace newlines in columns
            df.columns = df.columns.astype(str).str.replace(r'\n', '', regex=True).str.replace(r'\s+', '', regex=True)
            
            # Map known columns to database.csv standard
            # Expected DB: 着順, 枠, 馬番, 馬名, 性齢, 斤量, 騎手, タイム, 着差, 人気, 単勝オッズ, 後3F, ...
            # Actual from read_html might be: 着順, 枠番, 馬番, 馬名, 性齢, 斤量, 騎手, タイム, 着差, 人気, 単勝, 後3F...
            
            rename_map = {
                '枠番': '枠',
                '枠': '枠',
                '馬番': '馬 番', # DB has space? Check debug output or CSV header.
                # CSV Header: 着 順,枠,馬 番,馬名,性齢,斤量,騎手,タイム,着差,人 気,単勝 オッズ,後3F
                '馬名': '馬名',
                '単勝': '単勝 オッズ',
                '単勝オッズ': '単勝 オッズ',
                '人気': '人 気',
                '着順': '着 順',
                '上り': '後3F'
            }
            df.rename(columns=rename_map, inplace=True)
            
            # Ensure Odds is numeric
            if '単勝 オッズ' in df.columns:
                 df['単勝 オッズ'] = pd.to_numeric(df['単勝 オッズ'], errors='coerce').fillna(0.0) 
            
            # Warning if mismatch
            # print("Columns after rename:", df.columns)

            # 列追加
            df.insert(0, "日付", date_text)
            df.insert(1, "会場", venue_text)
            df.insert(2, "レース番号", race_num_text)
            df.insert(3, "レース名", race_name_text)
            df.insert(4, "重賞", grade_text)
            df["race_id"] = race_id # IDも保存 (末尾に追加されることが多いが明示的に)
            
            # 不要な列が含まれることがあるので整理しても良いが、
            # ユーザー要望は「蓄積」なので、基本はそのまま保持する
            
            # Extract Horse IDs from soup
            horse_id_map = {} # horse_name -> horse_id (Note: names might strictly not be unique but usually are in a race. Better to map by row index or horse number)
            # Actually, pd.read_html result index corresponds to table rows.
            # But the table has headers. 
            # We can iterate through table rows again.
            
            rows = target_table.find_all("tr")
            # Skip header if necessary. pd.read_html usually detects header.
            # Let's rely on finding "Horse_Name" class or anchor in rows.
            
            horse_ids = []
            
            # The DF from read_html might have removed some rows or headers.
            # Usually df length == number of horses.
            # Let's iterate `rows` and extract ID.
            
            found_ids = []
            for tr in rows:
                 # Check for horse link
                 a_tag = tr.select_one(".Horse_Name a")
                 if a_tag:
                     href = a_tag.get('href')
                     hid_match = re.search(r'/horse/(\d+)', href)
                     if hid_match:
                         found_ids.append(hid_match.group(1))
                     else:
                         found_ids.append("")
                 elif tr.select_one("td"): # If it's a data row but no link?
                     # Be careful about header rows that don't look like data
                     pass

            # Align IDs with DF
            # If len mismatches, we might have issues.
            if len(found_ids) == len(df):
                df['horse_id'] = found_ids
            else:
                # Try to fuzzy match or just warn
                print(f"Warning: ID count {len(found_ids)} != DF len {len(df)} for {race_id}")
                df['horse_id'] = ""

            # Enrich with Past Data
            # This is slow, so we only do it if we successfully got IDs
            # Parse Race Date for filtering
            try:
                current_race_date = datetime.strptime(date_text, '%Y年%m月%d日')
            except:
                current_race_date = datetime.now()
            
            print(f"  Enriching {len(df)} horses with past data...")
            
            past_columns = []
            # Prepare new columns
            # Added: last_3f, horse_weight, jockey, weight_carried, condition, odds, weather
            p_fields = ['date', 'rank', 'time', 'run_style', 'race_name', 'last_3f', 'horse_weight', 'jockey', 'condition', 'odds', 'weather']
            
            for i in range(1, 6):
                for f in p_fields:
                    past_columns.append(f"past_{i}_{f}")
            
            # Pre-fill empty
            for col in past_columns:
                df[col] = None

            for idx, row in df.iterrows():
                hid = row.get('horse_id')
                if hid and str(hid).isdigit():
                    past_df = scraper.get_past_races(hid, n_samples=20) # Get more to filter by date
                    
                    if not past_df.empty:
                         # Filter: Date < current_race_date
                         if 'date' in past_df.columns: # Changed from date_obj or 日付
                            if 'date_obj' not in past_df.columns and 'date' in past_df.columns:
                                past_df['date_obj'] = pd.to_datetime(past_df['date'], format='%Y/%m/%d', errors='coerce')
                            
                            if 'date_obj' in past_df.columns:
                                past_df = past_df[past_df['date_obj'] < current_race_date]
                         
                         # Take top 5
                         past_df = past_df.head(5)
                         
                         # Assign to columns
                         for i, (p_idx, p_row) in enumerate(past_df.iterrows()):
                             if i >= 5: break
                             n = i + 1
                             # p_row keys are now English from race_scraper
                             df.at[idx, f"past_{n}_date"] = p_row.get('date')
                             df.at[idx, f"past_{n}_rank"] = p_row.get('rank')
                             df.at[idx, f"past_{n}_time"] = p_row.get('time')
                             df.at[idx, f"past_{n}_run_style"] = p_row.get('run_style')
                             df.at[idx, f"past_{n}_race_name"] = p_row.get('race_name')
                             df.at[idx, f"past_{n}_last_3f"] = p_row.get('last_3f')
                             df.at[idx, f"past_{n}_horse_weight"] = p_row.get('horse_weight')
                             df.at[idx, f"past_{n}_jockey"] = p_row.get('jockey')
                             df.at[idx, f"past_{n}_condition"] = p_row.get('condition')
                             df.at[idx, f"past_{n}_odds"] = p_row.get('odds')
                             df.at[idx, f"past_{n}_weather"] = p_row.get('weather')
            
            return df
        else:
            return None

    except Exception as e:
        print(f"Error scraping {race_id}: {e}")
        return None

# ==========================================
# 2. Upcoming/Today's Race Scraping (JSON for Web App)
# ==========================================
    # ==========================================
# 2. Upcoming/Today's Race Scraping (JSON for Web App)
# ==========================================
def scrape_todays_schedule():
    """
    Scrapes race list for today + next 7 days (Total 8 days).
    Saves to 'todays_data.json'.
    """
    import json
    
    race_list = []
    today = datetime.now()
    
    print(f"Fetching schedule for next 8 days...")
    
    for i in range(8):
        target_date = today + timedelta(days=i)
        kaisai_date = target_date.strftime("%Y%m%d")
        date_str = target_date.strftime("%Y-%m-%d")
        
        # url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}"
        # sub html often returns empty if no race.
        # Main page: https://race.netkeiba.com/top/race_list.html?kaisai_date=...
        # But sub is better for parsing usually.
        url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}"
        headers = { "User-Agent": "Mozilla/5.0" }
        
        try:
            print(f" Checking {date_str}...")
            # We need a small sleep
            if i > 0: time.sleep(1)
            
            response = requests.get(url, headers=headers, timeout=10)
            if not response.text: continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Selectors
            items = soup.select('.RaceList_DataList .RaceList_DataItem')
            if not items:
                items = soup.select('.RaceList_Box .RaceList_DataItem')
                
            if not items:
                continue
                
            print(f"  Found {len(items)} races for {date_str}.")
            
            for item in items:
                link_elem = item.find('a')
                if not link_elem: continue
                
                href = link_elem.get('href', '')
                race_id_match = re.search(r'race_id=(\d+)', href)
                if not race_id_match: continue
                
                race_id = race_id_match.group(1)
                
                # Metadata
                venue_elem = item.select_one('.JyoName')
                race_num_elem = item.select_one('.Race_Num')
                race_name_elem = item.select_one('.RaceName') or item.select_one('.ItemTitle')
                
                venue = venue_elem.text.strip() if venue_elem else ""
                num = race_num_elem.text.strip() if race_num_elem else ""
                name = race_name_elem.text.strip() if race_name_elem else ""
                
                if not venue and len(race_id) >= 6:
                    place_code = race_id[4:6]
                    venue_map = {
                        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
                        "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"
                    }
                    venue = venue_map.get(place_code, "")
                
                # Clean up num (remove 'R' or spaces, keep digits)
                num = re.sub(r'\D', '', num) # Remove non-digits
                
                # Don't scrape odds for future dates aggressively (might not exist)
                # Only scrape odds if it's Today?
                # or just fetch basics. Providing odds is nice.
                # If date is today, fetch odds. Else maybe skip to save time.
                # Let's simple check: if date == today
                
                odds_data = []
                if i == 0:
                     odds_data = scrape_odds_for_race(race_id)
                
                race_info = {
                    "id": race_id,
                    "date": date_str,
                    "venue": venue,
                    "number": num,
                    "name": name,
                    "horses": odds_data
                }
                race_list.append(race_info)
                
        except Exception as e:
            print(f" Error fetching {date_str}: {e}")

    # Save to JSON
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "todays_data.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"date": today.strftime("%Y-%m-%d"), "races": race_list}, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(race_list)} future races to {output_path}")
    return True, f"{len(race_list)} races saved (Next 1 week)."

def scrape_odds_for_race(race_id):
    """
    Fetches odds for a specific race_id.
    Tries API first, then falls back to Main Odds page (Predicted Odds).
    Returns list of {number, odds}
    """
    horses = []
    headers = { "User-Agent": "Mozilla/5.0" }
    
    # 1. Try API (odds_get_form.html) - Good for real-time official odds
    try:
        url = f"https://race.netkeiba.com/odds/odds_get_form.html?type=b1&race_id={race_id}"
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rows = soup.select('#odds_tan_block .RaceOdds_HorseList_Table tbody tr')
        if not rows:
             rows = soup.select('.RaceOdds_HorseList_Table tbody tr')
        
        for row in rows:
            if 'RaceOdds_HorseList_Table' in str(row.find_parent('table')):
                num_elem = row.select_one('td:nth-child(2)')
                odds_elem = row.select_one('td:nth-child(6)')
            else:
                num_elem = row.select_one('.Umaban') or row.select_one('td:nth-child(2)')
                odds_elem = row.select_one('.Odds_Tan') or row.select_one('td:nth-child(14)')
            
            if num_elem and odds_elem:
                try:
                    num_txt = num_elem.text.strip()
                    if not num_txt.isdigit(): continue
                    num = int(num_txt)
                    
                    odds_txt = odds_elem.text.strip()
                    if '---' in odds_txt: odds = 0.0
                    else: odds = float(odds_txt)
                        
                    horses.append({"number": num, "odds": odds})
                except: continue
    except Exception as e:
        print(f"Error scraping API odds for {race_id}: {e}")

    # 2. Check if we got valid odds (at least one non-zero)
    has_valid_odds = any(h['odds'] > 0 for h in horses)
    
    if not has_valid_odds:
        # Fallback to Main Page (index.html) - Good for Predicted Odds / Early Odds
        print(f"  No official odds found via API. Trying Main Odds page for {race_id}...")
        try:
            url_main = f"https://race.netkeiba.com/odds/index.html?race_id={race_id}"
            response = requests.get(url_main, headers=headers, timeout=10)
            response.encoding = 'EUC-JP' # Netkeiba is usually EUC-JP
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Target #Ninki table (Popularity order)
            # Row structure: Rank | Waku | Umaban | Horse ... | Odds
            # But Selector check says Umaban is nth-child(3)
            table = soup.select_one('table#Ninki')
            if table:
                rows = table.find_all('tr')
                # Reset horses list as we are re-fetching
                horses = []
                
                for row in rows:
                    # Skip header (usually th)
                    if row.find('th'): continue
                    
                    cols = row.find_all('td')
                    if len(cols) < 5: continue
                    
                    # Umaban is usually 3rd col (index 2)
                    # Odds is usually in class 'Odds' or 'Tan_Odds'
                    try:
                        num_txt = cols[2].text.strip() # Umaban
                        if not num_txt.isdigit(): continue
                        num = int(num_txt)
                        
                        odds_elem = row.select_one('.Odds') or row.select_one('.Tan_Odds')
                        if odds_elem:
                            odds_txt = odds_elem.text.strip()
                            if '---' in odds_txt: odds = 0.0
                            else: odds = float(odds_txt)
                        else:
                            odds = 0.0
                            
                        horses.append({"number": num, "odds": odds})
                    except: continue
        except Exception as e:
            print(f"Error scraping Main odds for {race_id}: {e}")
            
    return horses

    return horses

# ==========================================
# 2.5 Shutuba Scraping (Future Races)
# ==========================================
def scrape_shutuba_data(race_id):
    """
    Scrapes the Shutuba Hyo (Race Card) for a given race_id.
    Enriches with past data using RaceScraper.
    Returns a DataFrame ready for prediction (no Rank).
    """
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.124 Safari/537.36" 
    }
    
    # Initialize Scraper
    scraper = RaceScraper()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Meta info
        race_name_elem = soup.select_one(".RaceName")
        race_name = race_name_elem.text.strip() if race_name_elem else ""
        
        # Date extraction (Title or Meta)
        # Usually in title: "2023年5月28日 ..."
        title = soup.title.text if soup.title else ""
        date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', title)
        date_text = date_match.group(1) if date_match else datetime.now().strftime('%Y年%m月%d日')
        
        try:
             current_race_date = datetime.strptime(date_text, '%Y年%m月%d日')
        except:
             current_race_date = datetime.now()

        # Parse Shutuba Table
        # The table class might be "Shutuba_Table"
        table = soup.find("table", class_="Shutuba_Table")
        if not table:
            # Try RaceTable01
            table = soup.find("table", class_="RaceTable01")
            
        if not table:
            print("Shutuba table not found.")
            return None
            
        rows = table.find_all("tr", class_="HorseList")
        
        data = []
        
        for row in rows:
            # Extract fields
            # Waku
            waku = ""
            waku_td = row.select_one("td.Waku") or row.select_one("td:nth-child(1)")
            if waku_td: waku = waku_td.text.strip()
            
            # Umaban
            umaban = ""
            umaban_td = row.select_one("td.Umaban") or row.select_one("td:nth-child(2)")
            if umaban_td: umaban = umaban_td.text.strip()
            
            # Horse
            horse_td = row.select_one("td.HorseInfo") or row.select_one("td.Horse_Info") # Class varies
            # Or assume standard column index if classes fail? Netkeiba is usually semantic.
            # .HorseName is inside .HorseInfo
            horse_name_a = row.select_one(".HorseName a") or row.select_one("td:nth-child(4) a")
            
            horse_name = ""
            horse_id = ""
            if horse_name_a:
                horse_name = horse_name_a.text.strip()
                href = horse_name_a.get("href", "")
                hm = re.search(r'/horse/(\d+)', href)
                if hm: horse_id = hm.group(1)
            
            # Basic info
            jockey = row.select_one(".Jockey a").text.strip() if row.select_one(".Jockey a") else ""
            weight = row.select_one(".Txt_C").text.strip() if row.select_one(".Txt_C") else "57.0" # Txt_C is usually weight? Or .Weight
            
            entry = {
                "日付": date_text,
                "レース名": race_name,
                "枠": waku,
                "馬 番": umaban,
                "馬名": horse_name,
                "horse_id": horse_id,
                "騎手": jockey,
                "斤量": weight,
                "race_id": race_id
                # Add 性齢 if needed for Age feature
            }
            
            # Age extraction usually in .Barei or similar
            # Example: "牡3"
            # It's usually near Horse Name
            # Let's inspect typical structure or ignore for now if not critical (Feature Engineering defaults to 3)
            # Find td with class "Barei" ?
            barei = row.select_one(".Barei")
            if barei:
                entry["性齢"] = barei.text.strip()
            
            data.append(entry)
            
        df = pd.DataFrame(data)
        
        # Merge Current Odds
        print(f"  Fetching current odds for {race_id}...")
        try:
            current_odds_list = scrape_odds_for_race(race_id)
            # Map by horse number (umaban)
            odds_map = {item['number']: item['odds'] for item in current_odds_list}
            
            # Add to DF
            df['単勝'] = df['馬 番'].apply(lambda x: odds_map.get(int(x) if str(x).isdigit() else 0, 0.0))
            df['Odds'] = df['単勝'] # Alias
        except Exception as e:
            print(f"Warning: Failed to fetch current odds: {e}")
            df['単勝'] = 0.0
            df['Odds'] = 0.0

        # Enrich
        print(f"  Enriching {len(df)} horses with past data...")
        past_columns = []
        p_fields = ['date', 'rank', 'time', 'run_style', 'race_name', 'last_3f', 'horse_weight', 'jockey', 'condition', 'odds', 'weather']
        
        for i in range(1, 6):
             for f in p_fields:
                past_columns.append(f"past_{i}_{f}")
        
        for col in past_columns:
            df[col] = None
            
        for idx, row in df.iterrows():
            hid = row.get('horse_id')
            if hid and str(hid).isdigit():
                past_df = scraper.get_past_races(hid, n_samples=20)
                if not past_df.empty:
                     if 'date' in past_df.columns:
                        if 'date_obj' not in past_df.columns:
                             past_df['date_obj'] = pd.to_datetime(past_df['date'], format='%Y/%m/%d', errors='coerce')
                        
                        if 'date_obj' in past_df.columns:
                             past_df = past_df[past_df['date_obj'] < current_race_date]
                     
                     past_df = past_df.head(5)
                     
                     for i, (p_idx, p_row) in enumerate(past_df.iterrows()):
                         if i >= 5: break
                         n = i + 1
                         df.at[idx, f"past_{n}_date"] = p_row.get('date')
                         # Ensure Rank is extracted
                         df.at[idx, f"past_{n}_rank"] = p_row.get('rank')
                         df.at[idx, f"past_{n}_time"] = p_row.get('time')
                         df.at[idx, f"past_{n}_run_style"] = p_row.get('run_style')
                         df.at[idx, f"past_{n}_race_name"] = p_row.get('race_name')
                         df.at[idx, f"past_{n}_last_3f"] = p_row.get('last_3f')
                         df.at[idx, f"past_{n}_horse_weight"] = p_row.get('horse_weight')
                         df.at[idx, f"past_{n}_jockey"] = p_row.get('jockey')
                         df.at[idx, f"past_{n}_condition"] = p_row.get('condition')
                         df.at[idx, f"past_{n}_odds"] = p_row.get('odds')
                         df.at[idx, f"past_{n}_weather"] = p_row.get('weather')
        
        return df
        
    except Exception as e:
        print(f"Error scraping Shutuba {race_id}: {e}")
        return None
def get_start_params(start_args=None, end_args=None, places_args=None):
    """
    start_args, end_args: datetime objects or None.
    places_args: list of ints or None.
    If provided, use them. Otherwise check CLI args or existing CSV.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--places", type=str, help="Target places (comma separated, e.g. 6,7)")
    
    # Only parse args if not provided programmatically or if we want to fallback
    # If called from admin UI, sys.argv might contain streamlit args, so be careful.
    # To be safe, if programmatic args are None, we check sys.argv BUT
    # best to rely on programmatic invocation from admin.py passing distinct args.
    
    # If run from CLI, parse_known_args will pick up --start etc.
    args, unknown = parser.parse_known_args()

    # Determine Start Date
    start_date = start_args
    if start_date is None and args.start:
        try:
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
        except:
             print("日付フォーマットエラー。YYYY-MM-DDで指定してください。")

    # Determine End Date
    end_date_str = end_args # Might be passed as str or obj? Let's assume passed as None or YYYY-MM-DD str usually not needed if object passed.
    
    # Let's standardize: main accepts datetime objects or None.
    # get_start_params returns datetime objects and places list.
    
    # Determine Places
    target_places = places_args if places_args is not None else range(1, 11)
    if places_args is None and args.places:
        try:
            target_places = [int(p) for p in args.places.split(",")]
        except:
            print("places指定エラー。カンマ区切り数字で指定してください。")
            
    # Auto-detect start if still None
    if start_date is None:
        if os.path.exists(CSV_FILE_PATH):
            try:
                df_existing = pd.read_csv(CSV_FILE_PATH)
                if '日付' in df_existing.columns and not df_existing.empty:
                    df_existing['date_obj'] = pd.to_datetime(df_existing['日付'], format='%Y年%m月%d日', errors='coerce')
                    last_date = df_existing['date_obj'].max()
                    
                    if pd.notna(last_date):
                        print(f"既存データが見つかりました。最終データ日時: {last_date}")
                        start_date = last_date + timedelta(days=1)
            except Exception as e:
                print(f"既存CSV読み込みエラー: {e}")
    
    if start_date is None:
         # デフォルト：最近の結果を取得しやすくするため、2025年12月頭にしておく（デモ用）
         print("既存データなし。デモ用に2025年12月1日から開始します。")
         start_date = datetime(2025, 12, 1)

    return start_date, args.end, target_places

# ==========================================
# 3. メイン実行処理
# ==========================================
def main(start_date_arg=None, end_date_arg=None, places_arg=None, progress_callback=None):
    """
    progress_callback: function(str) -> None. If provided, call with status update.
    """
    print("=== 自動スクレイピング開始 ===")
    start_time = time.time()
    
    # Pass arguments to helper
    start_date, end_arg_cli, places = get_start_params(start_date_arg, end_date_arg, places_arg)
    
    today = datetime.now()
    
    # Determine absolute End Date
    if end_date_arg:
        # If passed valid datetime or string?
        if isinstance(end_date_arg, str):
            try:
                end_date = datetime.strptime(end_date_arg, "%Y-%m-%d")
            except:
                end_date = today
        elif isinstance(end_date_arg, datetime) or isinstance(end_date_arg, date):
            end_date = pd.to_datetime(end_date_arg) # Ensure datetime
            # pd.to_datetime returns Timestamp, convert to datetime for compare
            end_date = end_date.to_pydatetime()
        else:
             end_date = today
    elif end_arg_cli:
        try:
             end_date = datetime.strptime(end_arg_cli, "%Y-%m-%d")
        except:
             end_date = today
    else:
        end_date = today
    
    # 終了日補正（その日の終わりまで）
    end_date = end_date.replace(hour=23, minute=59, second=59)

    info_msg = f"取得対象期間: {start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}"
    print(info_msg)
    if progress_callback: progress_callback(info_msg)

    if start_date > end_date:
        msg = "指定期間が不正、または最新データまで取得済みです。"
        print(msg)
        if progress_callback: progress_callback(msg)
        return

    print(f"対象会場: {list(places)}")

    all_data = []
    
    # 年ごとのループ
    years_to_scan = range(start_date.year, end_date.year + 1)

    # 探索ロジック
    kais = range(1, 7)    # 開催回
    days = range(1, 13)   # 開催日数
    
    existing_ids = set()
    if os.path.exists(CSV_FILE_PATH):
        try:
            df_ex = pd.read_csv(CSV_FILE_PATH)
            if 'race_id' in df_ex.columns:
                existing_ids = set(df_ex['race_id'].astype(str))
        except:
            pass

    for year in years_to_scan:
        for place in places:
            for kai in kais:
                for day in days:
                    check_race_id = f"{year}{place:02}{kai:02}{day:02}01"
                    
                    if check_race_id in existing_ids:
                        pass
                    
                    status_text = f"確認中: {check_race_id} (Year:{year} Place:{place} Kai:{kai} Day:{day})"
                    if progress_callback: progress_callback(status_text)
                    print(f"Search: {check_race_id} ... ", end="")
                    
                    # サーバー負荷軽減
                    time.sleep(1)
                    
                    first_race_df = scrape_race_data(check_race_id)
                    
                    if first_race_df is None:
                        # 1Rがない -> この開催日はない、または終了
                        print("Miss")
                        if day == 1:
                            break 
                        else:
                            break
                    else:
                        # 開催あり。日付をチェック
                        race_date_str = first_race_df.iloc[0]["日付"] 
                        try:
                            race_date = datetime.strptime(race_date_str, '%Y年%m月%d日')
                        except:
                            race_date = datetime(year, 1, 1)

                        # 対象期間チェック
                        if race_date < start_date:
                            print(f"Skip (Old Data: {race_date_str})")
                            continue
                        
                        if race_date > end_date:
                            print(f"Skip (Future/Outside Range: {race_date_str})")
                            break

                        msg_hit = f"Hit ({race_date_str}) -> 取得開始"
                        print(msg_hit)
                        if progress_callback: progress_callback(msg_hit)
                        
                        # 1Rを保存
                        if check_race_id not in existing_ids:
                             all_data.append(first_race_df)
                        
                        # 2R〜12R
                        for r in range(2, 13):
                            race_id = f"{year}{place:02}{kai:02}{day:02}{r:02}"
                            if race_id in existing_ids:
                                continue
                                
                            if progress_callback: progress_callback(f"取得中: {race_date_str} {r}R ({race_id})")
                            
                            time.sleep(1) # Wait
                            df = scrape_race_data(race_id)
                            if df is not None:
                                all_data.append(df)
                                print(f".", end="", flush=True) 
                            else:
                                break
                        print(" Done")

    # ==========================================
    # CSV保存 (追記 or 新規)
    # ==========================================
    if len(all_data) > 0:
        print("\nデータ結合中...")
        new_df = pd.concat(all_data, ignore_index=True)
        
        # 既存データとマージ
        if os.path.exists(CSV_FILE_PATH):
            try:
                existing_df = pd.read_csv(CSV_FILE_PATH)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            except:
                combined_df = new_df
        else:
            combined_df = new_df
        
        # Column name cleaning
        # Sometimes header has newlines
        
        # 重複排除
        # race_id と 馬名 でユニークにする
        subset_cols = ['race_id', '馬名']
        # 実際に存在するカラムだけでフィルタ
        subset_cols = [c for c in subset_cols if c in combined_df.columns]
        
        if subset_cols:
            combined_df.drop_duplicates(subset=subset_cols, keep='last', inplace=True)
        
        # 日付ソート
        try:
            combined_df['date_obj'] = pd.to_datetime(combined_df['日付'], format='%Y年%m月%d日', errors='coerce')
            combined_df = combined_df.sort_values(['date_obj', 'race_id'])
            combined_df = combined_df.drop(columns=['date_obj'])
        except:
            pass

        combined_df.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
        print(f"保存完了: {len(new_df)} 件追加 (Total: {len(combined_df)})")
        print(f"ファイル: {CSV_FILE_PATH}")
    else:
        print("新規取得データはありませんでした。")

    print(f"所要時間: {(time.time() - start_time)/60:.1f} 分")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", action="store_true", help="Scrape today's race schedule")
    parser.add_argument("--jra_url", type=str, help="Direct JRA URL to scrape")
    parser.add_argument("--jra_year", type=str, help="Scrape entire year from JRA (e.g. 2025)")
    parser.add_argument("--jra_date_start", type=str, help="Start date (YYYY-MM-DD) for JRA bulk scrape")
    parser.add_argument("--jra_date_end", type=str, help="End date (YYYY-MM-DD) for JRA bulk scrape")
    # Also parse arguments for main() to avoid conflicts if they are passed
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--places", type=str, help="Target places")
    
    args, unknown = parser.parse_known_args()
    
    if args.today:
        scrape_todays_schedule()
    elif args.jra_url:
        print(f"Direct JRA Mode: {args.jra_url}")
        df = scrape_jra_race(args.jra_url)
        if df is not None and not df.empty:
            # Save logic (similar to main)
            # We can reuse the save logic but it's embedded in main()
            # Let's minimal-copy the save logic here for simplicity or refactor
            # For now, append to CSV directly
            CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")
            
            if os.path.exists(CSV_FILE_PATH):
                try:
                    existing_df = pd.read_csv(CSV_FILE_PATH)
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                except:
                    combined_df = df
            else:
                combined_df = df
                
            # Deduplicate
            subset_cols = ['race_id', '馬名']
            subset_cols = [c for c in subset_cols if c in combined_df.columns]
            if subset_cols:
                combined_df.drop_duplicates(subset=subset_cols, keep='last', inplace=True)
            
            combined_df.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
            print(f"Saved to {CSV_FILE_PATH}")
        else:
            print("Failed to scrape JRA data.")
    elif args.jra_year:
        print(f"JRA Bulk Scraping Year: {args.jra_year}")
        
        start_date = None
        end_date = None
        
        if args.jra_date_start:
            try:
                start_date = datetime.strptime(args.jra_date_start, "%Y-%m-%d").date()
            except ValueError:
                print("Invalid start date format. Use YYYY-MM-DD")
                sys.exit(1)

        if args.jra_date_end:
            try:
                end_date = datetime.strptime(args.jra_date_end, "%Y-%m-%d").date()
            except ValueError:
                print("Invalid end date format. Use YYYY-MM-DD")
                sys.exit(1)

        # Define save callback to handle incremental saves
        def save_chunk(df_chunk):
            CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")
            
            if os.path.exists(CSV_FILE_PATH):
                try:
                    existing_df = pd.read_csv(CSV_FILE_PATH)
                    combined_df = pd.concat([existing_df, df_chunk], ignore_index=True)
                except:
                    combined_df = df_chunk
            else:
                combined_df = df_chunk
            
            # Deduplicate
            subset_cols = ['race_id', '馬名']
            subset_cols = [c for c in subset_cols if c in combined_df.columns]
            if subset_cols:
                combined_df.drop_duplicates(subset=subset_cols, keep='last', inplace=True)
            
            combined_df.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
            print(f"  -> Saved {len(df_chunk)} rows. Total: {len(combined_df)}")
            
        scrape_jra_year(args.jra_year, start_date=start_date, end_date=end_date, save_callback=save_chunk)

    else:
        # Pass unknown arguments or parse them again inside main/get_start_params 
        # but get_start_params parses sys.argv again or uses its own parser.
        # Since get_start_params uses parse_known_args, it should be fine.
        main()
