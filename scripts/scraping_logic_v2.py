
# 2026-01-08: Rich Scraping Logic (JRA/NAR Universal)
# This code handles scraping of Race Result + Horse History + Pedigree in one pass.

import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
from datetime import datetime
import urllib.parse
import time
import random
from tqdm.auto import tqdm

# --- RaceScraper Helper Class (Embedded) ---
class RaceScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _get_soup(self, url):
        try:
            time.sleep(1) # Be polite
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = response.apparent_encoding
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    def get_horse_profile(self, horse_id):
        """
        Fetches horse profile to get pedigree (Father, Mother, Grandfather(BMS)).
        Returns a dictionary or None.
        """
        url = f"https://db.netkeiba.com/horse/ped/{horse_id}/"
        soup = self._get_soup(url)
        data = {"father": "", "mother": "", "bms": ""}
        if not soup: return data

        try:
            table = soup.select_one("table.blood_table")
            if table:
                rows = table.find_all("tr")
                if len(rows) >= 17:
                    # Father: Row 0
                    r0 = rows[0].find_all("td")
                    if r0:
                        txt = r0[0].text.strip()
                        data["father"] = txt.split('\n')[0].strip()

                    # Mother & BMS: Row 16
                    r16 = rows[16].find_all("td")
                    if len(r16) >= 2:
                        m_txt = r16[0].text.strip()
                        data["mother"] = m_txt.split('\n')[0].strip()
                        bms_txt = r16[1].text.strip()
                        data["bms"] = bms_txt.split('\n')[0].strip()
        except Exception as e:
            pass # Silent fail for profile
        return data

    def extract_run_style(self, passing_str):
        if not isinstance(passing_str, str): return 3
        try:
            cleaned = re.sub(r'[^0-9-]', '', passing_str)
            parts = [int(p) for p in cleaned.split('-') if p]
            if not parts: return 3
            first_corner = parts[0]
            if first_corner == 1: return 1 # Nige
            elif first_corner <= 4: return 2 # Senkou
            elif first_corner <= 9: return 3 # Sashi
            else: return 4 # Oikomi
        except: return 3

    def get_past_races(self, horse_id, current_race_date, n_samples=5):
        """
        Fetches past n_samples race results.
        Filters out races AFTER current_race_date.
        Returns a DataFrame.
        """
        url = f"https://db.netkeiba.com/horse/result/{horse_id}/"
        soup = self._get_soup(url)
        if not soup: return pd.DataFrame()

        table = soup.select_one("table.db_h_race_results")
        if not table:
             tables = soup.find_all("table")
             for t in tables:
                 if "着順" in t.text:
                     table = t
                     break
        if not table: return pd.DataFrame()

        try:
            df = pd.read_html(io.StringIO(str(table)))[0]
            df = df.dropna(how='all')
            # Normalize columns
            df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)
            
            # Date Parsing
            if '日付' in df.columns:
                df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
                df = df.dropna(subset=['date_obj'])
                
                # Filter past races only
                if isinstance(current_race_date, str):
                    current_date = pd.to_datetime(current_race_date)
                else:
                    current_date = pd.to_datetime(current_race_date)
                    
                df = df[df['date_obj'] < current_date]
                df = df.sort_values('date_obj', ascending=False)
            
            if df.empty: return df

            # Limit to N
            df = df.head(n_samples)

            # Extract Run Style
            if '通過' in df.columns:
                df['run_style_val'] = df['通過'].apply(self.extract_run_style)
            else:
                df['run_style_val'] = 3

            # Column Mapping
            column_map = {
                '日付': 'date', '開催': 'venue', '天気': 'weather', 'レース名': 'race_name',
                '着順': 'rank', '枠番': 'waku', '馬番': 'umaban', '騎手': 'jockey',
                '斤量': 'weight_carried', '馬場': 'condition', 'タイム': 'time',
                '着差': 'margin', '上り': 'last_3f', '通過': 'passing', '馬体重': 'horse_weight',
                'run_style_val': 'run_style', '単勝': 'odds', 'オッズ': 'odds', '距離': 'raw_distance'
            }
            df.rename(columns=column_map, inplace=True)
            
            # Parse Distance/Course
            if 'raw_distance' in df.columns:
                def parse_dist(x):
                    if not isinstance(x, str): return None, None
                    surf = None; dist = None
                    if '芝' in x: surf = '芝'
                    elif 'ダ' in x: surf = 'ダ'
                    elif '障' in x: surf = '障'
                    match = re.search(r'(\d+)', x)
                    if match: dist = int(match.group(1))
                    return surf, dist
                
                parsed = df['raw_distance'].apply(parse_dist)
                df['course_type'] = parsed.apply(lambda x: x[0])
                df['distance'] = parsed.apply(lambda x: x[1])
            else:
                df['course_type'] = None; df['distance'] = None

            return df
        except Exception as e:
            return pd.DataFrame()

# --- Main Rich Scraper Function ---
def scrape_race_rich(url, existing_race_ids=None, max_retries=3):
    """
    Scrapes Race + History + Pedigree in one go.
    """
    print(f"  レース解析中: {url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. Fetch Race Page
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # --- Metadata (Date, Venue, Race Name, etc) ---
        # (This part reuses logic from original scrape_jra_race)
        h1_elem = soup.select_one("div.header_line h1 .txt")
        full_text = h1_elem.text.strip() if h1_elem else (soup.h1.text.strip() if soup.h1 else "")
        
        date_text = ""; venue_text = ""; kai = "01"; day = "01"; r_num = "10"
        match_date = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', full_text)
        if match_date: date_text = match_date.group(1)
        
        venues_str = "札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉"
        match_meta = re.search(rf'(\d+)回({venues_str})(\\d+)日', full_text)
        if match_meta:
            kai = f"{int(match_meta.group(1)):02}"
            venue_text = match_meta.group(2)
            day = f"{int(match_meta.group(3)):02}"
            
        match_race = re.search(r'(\d+)レース', full_text)
        if match_race: r_num = f"{int(match_race.group(1)):02}"
        
        place_map = {
            "札幌": "01", "函館": "02", "福島": "03", "新潟": "04", "東京": "05",
            "中山": "06", "中京": "07", "京都": "08", "阪神": "09", "小倉": "10"
        }
        p_code = place_map.get(venue_text, "00")
        year = date_text[:4] if date_text else "2025"
        
        race_id = f"{year}{p_code}{kai}{day}{r_num}"
        
        # SKIP Check
        if existing_race_ids and race_id in existing_race_ids:
            return None

        # Basic Race Info
        race_name = soup.select_one(".race_name").text.strip() if soup.select_one(".race_name") else ""
        header_text = soup.select_one("div.header_line").text if soup.select_one("div.header_line") else full_text
        
        # Course/Dist
        course_type = ""; distance = ""
        dt_match = re.search(r'(芝|ダ|ダート|障害)[^0-9]*(\d+)', header_text)
        if dt_match:
            c = dt_match.group(1)
            course_type = '芝' if '芝' in c else ('ダート' if 'ダ' in c else '障害')
            distance = dt_match.group(2)
            
        # Weather/Condition
        weather = ""; condition = ""; rotation = ""
        w_match = re.search(r'天候\s*[:：]\s*(\S+)', soup.text)
        if w_match: weather = w_match.group(1)
        
        c_match = re.search(r'(?:芝|ダート)\s*[:：]\s*(\S+)', soup.text)
        if c_match: condition = c_match.group(1)
        
        if "右" in header_text: rotation = "右"
        elif "左" in header_text: rotation = "左"
        elif "直" in header_text: rotation = "直線"

        # --- Parse Result Table ---
        tables = soup.find_all('table')
        target_table = None
        for t in tables:
            if "着順" in t.text and "馬名" in t.text:
                target_table = t
                break
        
        if not target_table: return None
        
        rows = target_table.find_all('tr')
        race_scraper = RaceScraper()
        
        data_list = []
        
        # Pre-convert date for filtering
        d_obj = pd.to_datetime(date_text, format='%Y年%m月%d日') if date_text else datetime.now()
        
        print(f"    Fetching details for {len(rows)-1} horses...")
        
        for row in rows:
            if row.find('th'): continue # Skip header
            cells = row.find_all('td')
            if not cells: continue
            
            # Basic info
            rank = cells[0].text.strip()
            waku = ""
            if cells[1].find('img'): 
                alt = cells[1].find('img').get('alt', '')
                m = re.search(r'枠(\d+)', alt)
                waku = m.group(1) if m else alt
            umaban = cells[2].text.strip()
            horse_name_elem = cells[3].find('a')
            horse_name = cells[3].text.strip()
            horse_id = ""
            if horse_name_elem and 'href' in horse_name_elem.attrs:
                hm = re.search(r'/horse/(\d+)', horse_name_elem['href'])
                if hm: horse_id = hm.group(1)
            
            jockey = cells[6].text.strip()
            time_val = cells[7].text.strip()
            # ... other basic fields
            
            # --- Rich Fetching (History & Pedigree) ---
            blood_data = {"father": "", "mother": "", "bms": ""}
            past_data = {}
            
            if horse_id:
                # 1. Pedigree
                blood_data = race_scraper.get_horse_profile(horse_id)
                
                # 2. History
                df_past = race_scraper.get_past_races(horse_id, d_obj, n_samples=5)
                
                # Flatten History
                for i in range(5):
                    prefix = f"past_{i+1}"
                    if i < len(df_past):
                        r = df_past.iloc[i]
                        past_data[f"{prefix}_date"] = r.get('date', '')
                        past_data[f"{prefix}_rank"] = r.get('rank', '')
                        past_data[f"{prefix}_time"] = r.get('time', '')
                        past_data[f"{prefix}_run_style"] = r.get('run_style', '')
                        past_data[f"{prefix}_race_name"] = r.get('race_name', '')
                        past_data[f"{prefix}_last_3f"] = r.get('last_3f', '')
                        past_data[f"{prefix}_horse_weight"] = r.get('horse_weight', '')
                        past_data[f"{prefix}_jockey"] = r.get('jockey', '')
                        past_data[f"{prefix}_condition"] = r.get('condition', '')
                        past_data[f"{prefix}_odds"] = r.get('odds', '')
                        past_data[f"{prefix}_weather"] = r.get('weather', '')
                        past_data[f"{prefix}_distance"] = r.get('distance', '')
                        past_data[f"{prefix}_course_type"] = r.get('course_type', '')
                    else:
                        # Fill Empty
                        for col in ['date','rank','time','run_style','race_name','last_3f','horse_weight','jockey','condition','odds','weather','distance','course_type']:
                            past_data[f"{prefix}_{col}"] = ""

                # Be polite between horses
                time.sleep(0.5)
            
            # Combine
            row_dict = {
                "日付": date_text, "会場": venue_text, "レース番号": f"{r_num}R", "レース名": race_name, "重賞": "",
                "コースタイプ": course_type, "距離": distance, "回り": rotation, "天候": weather, "馬場状態": condition,
                "着順": rank, "枠": waku, "馬番": umaban, "馬名": horse_name, 
                "性齢": cells[4].text.strip(), "斤量": cells[5].text.strip(), "騎手": jockey, 
                "タイム": time_val, "着差": cells[8].text.strip(), "人気": cells[13].text.strip(), 
                "単勝オッズ": cells[14].text.strip() if len(cells)>14 else "0.0", 
                "後3F": cells[10].text.strip(), "厩舎": cells[12].text.strip(), 
                "馬体重(増減)": cells[11].text.strip(),
                "race_id": race_id, "horse_id": horse_id,
                **blood_data,
                **past_data
            }
            data_list.append(row_dict)
            
        df = pd.DataFrame(data_list)
        
        # Enforce User-Specified Column Order
        ordered_columns = [
            "日付", "会場", "レース番号", "レース名", "重賞", "コースタイプ", "距離", "回り", "天候", "馬場状態",
            "着順", "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "タイム", "着差", "人気", "単勝オッズ",
            "後3F", "厩舎", "馬体重(増減)", "race_id", "horse_id"
        ]
        # rich data columns
        for i in range(1, 6):
            p = f"past_{i}"
            ordered_columns.extend([
                f"{p}_date", f"{p}_rank", f"{p}_time", f"{p}_run_style", f"{p}_race_name",
                f"{p}_last_3f", f"{p}_horse_weight", f"{p}_jockey", f"{p}_condition",
                f"{p}_odds", f"{p}_weather", f"{p}_distance", f"{p}_course_type"
            ])
        ordered_columns.extend(["father", "mother", "bms"])
        
        # Add missing cols with empty string, remove extras (if any/optional)
        # reindex handles this safely
        df_ordered = df.reindex(columns=ordered_columns, fill_value="")
        
        return df_ordered

    except Exception as e:
        print(f"Error scraping race {url}: {e}")
        return None

# --- Year/Month Iteration Logic (Scrape Year Rich) ---
def scrape_jra_year_rich(year_str, start_date=None, end_date=None, save_callback=None, existing_race_ids=None):
    # Parameter Map for Monthly Results
    JRA_MONTH_PARAMS = {
        "2026": { "01": "E4", "02": "B2", "03": "80", "04": "4E", "05": "1C", "06": "EA", "07": "B8", "08": "86", "09": "54", "10": "22", "11": "F0", "12": "BE" },
        "2025": { "01": "3F", "02": "0D", "03": "DB", "04": "A9", "05": "77", "06": "45", "07": "13", "08": "E1", "09": "AF", "10": "1E", "11": "EC", "12": "D3" },
        "2024": { "01": "B3", "02": "81", "03": "4F", "04": "1D", "05": "EB", "06": "B9", "07": "87", "08": "55", "09": "23", "10": "92", "11": "60", "12": "2E" },
        "2023": { "01": "27", "02": "F5", "03": "C3", "04": "91", "05": "5F", "06": "2D", "07": "FB", "08": "C9", "09": "97", "10": "06", "11": "D4", "12": "A2" },
        "2022": { "01": "9B", "02": "69", "03": "37", "04": "05", "05": "D3", "06": "A1", "07": "6F", "08": "3D", "09": "0B", "10": "7A", "11": "48", "12": "16" },
        "2021": { "01": "0F", "02": "DD", "03": "AB", "04": "79", "05": "47", "06": "15", "07": "E3", "08": "B1", "09": "7F", "10": "EE", "11": "BC", "12": "8A" },
        "2020": { "01": "83", "02": "51", "03": "1F", "04": "ED", "05": "BB", "06": "89", "07": "57", "08": "25", "09": "F3", "10": "62", "11": "30", "12": "FE" }
    }
    
    if year_str not in JRA_MONTH_PARAMS:
        print(f"年度 {year_str} はサポートされていません。")
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

    # Cap at Today
    from datetime import date
    today = date.today()

    if end_date:
        actual_end_date = min(end_date, today)
    else:
        actual_end_date = today

    print(f"=== JRA 一括スクレイピング開始 {year_str} (リッチモード) ===")
    print(f"期間: {start_date or 'Start'} - {actual_end_date}")
    
    if int(year_str) == today.year:
        end_m = min(end_m, today.month)

    total_processed = 0

    for m in range(start_m, end_m + 1):
        month = f"{m:02}"
        if month not in params:
            continue

        suffix = params[month]
        try:
            ym = int(year_str + month)
            prefix = "pw01skl00" if ym >= 202512 else "pw01skl10"
        except:
            prefix = "pw01skl10"

        cname = f"{prefix}{year_str}{month}/{suffix}"

        print(f"\n📅 {year_str}/{month} を取得中...")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.post(base_url, data={"cname": cname}, headers=headers, timeout=15)
            response.encoding = 'cp932'

            if response.status_code != 200:
                print(f"❌ {cname} の取得に失敗しました (Status {response.status_code})")
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
            print(f"  {len(race_cnames)} 開催日が見つかりました")

            for day_cname in tqdm(race_cnames, desc=f"  {year_str}/{month}", leave=False):
                resp_day = requests.post(base_url, data={"cname": day_cname}, headers=headers, timeout=15)
                resp_day.encoding = 'cp932'
                soup_day = BeautifulSoup(resp_day.text, 'html.parser')

                race_list_items = []
                all_anchors = soup_day.find_all('a')
                for a in all_anchors:
                    onclick = a.get('onclick', '')
                    match_sde = re.search(r"doAction\s*\(\s*['\"][^'\"]+['\"]\s*,\s*['\"](pw01sde[^'\"]+)['\"]\s*\)", onclick)
                    href = a.get('href', '')

                    final_url = ""
                    if match_sde:
                        final_url = f"{base_url}?CNAME={match_sde.group(1)}"
                    elif 'pw01sde' in href:
                         if 'CNAME=' in href:
                             final_url = urllib.parse.urljoin(base_url, href)
                         else:
                             final_url = urllib.parse.urljoin(base_url, href)

                    if final_url:
                        race_list_items.append(final_url)

                unique_races = sorted(list(set(race_list_items)))

                for r_link in unique_races:
                    # Fetch with Rich Scraper
                    df = scrape_race_rich(r_link, existing_race_ids=existing_race_ids)

                    if df is not None and not df.empty:
                        if save_callback:
                            save_callback(df)
                        total_processed += 1
                    
                    # Rate limiting
                    time.sleep(1.0) 

        except Exception as e:
            print(f"❌ {month}月の処理中にエラーが発生しました: {e}")
            
    print("完了しました。")
