import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime

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

    def get_past_races(self, horse_id, n_samples=5):
        """
        Fetches past n_samples race results for a given horse_id from netkeiba db.
        Returns a DataFrame of past races.
        """
        url = f"https://db.netkeiba.com/horse/result/{horse_id}/"
        soup = self._get_soup(url)
        if not soup:
            return pd.DataFrame()

        # The results are usually in a table with class "db_h_race_results"
        table = soup.select_one("table.db_h_race_results")
        if not table:
            # Try to find any table with "着順"
            tables = soup.find_all("table")
            for t in tables:
                if "着順" in t.text:
                    table = t
                    break
        
        if not table:
            return pd.DataFrame()

        # Parse table
        # We need to manually parse to get clean data and handle links if needed (though for past data, text is mostly fine)
        # pd.read_html is easier for the table
        try:
            df = pd.read_html(str(table))[0]
            
            # Basic cleaning
            df = df.dropna(how='all')
            
            # The columns in db.netkeiba are roughly:
            # 日付, 開催, 天気, R, レース名, 映像, 頭数, 枠番, ... 着順, ... 通過, ...
            
            # We want to keep: Date, Race Name, Course info, Rank, Time, Passing (Style)
            
            # Normalize column names (remove spaces/newlines)
            df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)

            # Filter rows that look like actual races (Date column exists)
            if '日付' in df.columns:
                df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
                df = df.dropna(subset=['date_obj'])
                df = df.sort_values('date_obj', ascending=False)
                
            # Take top N
            df = df.head(n_samples)
            
            # Process Run Style (Leg Type)
            if '通過' in df.columns:
                df['run_style_val'] = df['通過'].apply(self.extract_run_style)
            else:
                df['run_style_val'] = 3 # Unknown

            # Extract/Rename Columns
            # We want: 日付, 開催, 天気, R, レース名, 映像, 頭数, 枠番, ... 着順, ... 通過, ...
            # Important: '上り' (3F), '馬体重', '騎手'
            
            # Map standard columns if they exist
            column_map = {
                '日付': 'date',
                '開催': 'venue',
                '天気': 'weather',
                'レース名': 'race_name',
                '着順': 'rank',
                '枠番': 'waku',
                '馬番': 'umaban',
                '騎手': 'jockey',
                '斤量': 'weight_carried',
                '馬場': 'condition', # 芝/ダート + 良/重
                'タイム': 'time',
                '着差': 'margin',
                '上り': 'last_3f',
                '通過': 'passing',
                '馬体重': 'horse_weight',
                'run_style_val': 'run_style',
                '単勝': 'odds'
            }
            
            # Rename available columns
            df.rename(columns=column_map, inplace=True)
            
            # Coerce numeric
            if 'rank' in df.columns:
                df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
            
            if 'odds' in df.columns:
                 df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
            
            # Fill missing
            for target_col in column_map.values():
                if target_col not in df.columns:
                    df[target_col] = None
                
            return df
            
        except Exception as e:
            print(f"Error parsing past races for {horse_id}: {e}")
            return pd.DataFrame()

    def extract_run_style(self, passing_str):
        """
        Converts passing order string (e.g., "1-1-1", "10-10-12") to run style (1,2,3,4).
        1: Nige (Escape) - Lead at 1st corner
        2: Senkou (Leader) - Within first ~4 or so
        3: Sashi (Mid) - Midpack
        4: Oikomi (Chaser) - Back
        Returns integer code.
        """
        if not isinstance(passing_str, str):
            return 3 # Default to Mid
            
        # Clean string "1-1-1" -> [1, 1, 1]
        try:
            cleaned = re.sub(r'[^0-9-]', '', passing_str)
            parts = [int(p) for p in cleaned.split('-') if p]
            
            if not parts:
                return 3
                
            first_corner = parts[0]
            
            # Heuristics
            if first_corner == 1:
                return 1 # Nige
            elif first_corner <= 4:
                return 2 # Senkou
            elif first_corner <= 9: # Assuming standard field size of 10-16, 9 is mid-ish limit? 
                # Actually "Sashi" is usually mid-rear. 
                # Let's say: 1=Lead, 2-4=Front, 5-10=Mid, >10=Back
                return 3 # Sashi
            else:
                return 4 # Oikomi
                
        except:
            return 3

    def scrape_race_with_history(self, race_id):
        """
        Detailed scraper that enters a race_result page, finding horse IDs, 
        then fetches history for each horse.
        Returns a dictionary or structured object with the race result + history.
        """
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
        soup = self._get_soup(url)
        if not soup:
            return None
            
        # 1. Parse Main Result Table to get Horse IDs and basic result
        # Note: auto_scraper already does some of this, but we need Horse IDs specifically.
        # "All_Result_Table"
        
        result_data = []
        
        table = soup.find("table", id="All_Result_Table")
        if not table:
            return None
            
        rows = table.find_all("tr", class_="HorseList")
        
        print(f"Found {len(rows)} horses in race {race_id}. Fetching histories...")
        
        for row in rows:
            # Extract basic info
            rank_elem = row.select_one(".Rank")
            rank = rank_elem.text.strip() if rank_elem else ""
            
            horse_name_elem = row.select_one(".Horse_Name a")
            horse_name = horse_name_elem.text.strip() if horse_name_elem else ""
            horse_url = horse_name_elem.get("href") if horse_name_elem else ""
            
            # Extract ID from URL
            # https://db.netkeiba.com/horse/2018105027
            horse_id = None
            if horse_url:
                match = re.search(r'/horse/(\d+)', horse_url)
                if match:
                    horse_id = match.group(1)
            
            if not horse_id:
                print(f"  Skipping {horse_name} (No ID)")
                continue

            print(f"  Fetching history for {horse_name} ({horse_id})...")
            
            # 2. Get Past History
            df_past = self.get_past_races(horse_id, n_samples=5)
            
            # 3. Structure Data
            # converting df_past to a list of dicts or flattened fields
            history = []
            if not df_past.empty:
                for idx, r in df_past.iterrows():
                    # Extract relevant columns
                    # We need at least: Rank, RunStyle, Time(Seconds?), Pace?
                    # For now just dump raw-ish data
                    hist_item = {
                        "date": r.get('日付'),
                        "race_name": r.get('レース名'),
                        "rank": r.get('着順'),
                        "passing": r.get('通過'),
                        "run_style": r.get('run_style_val'),
                        "time": r.get('タイム'),
                        # Add more as needed for Feature Engineering
                    }
                    history.append(hist_item)
            
            entry = {
                "race_id": race_id,
                "horse_id": horse_id,
                "horse_name": horse_name,
                "rank": rank,
                "history": history
            }
            result_data.append(entry)
            
        return result_data

if __name__ == "__main__":
    # Test
    scraper = RaceScraper()
    print("Running test...")
    # Example: Do Deuce (2019105219)
    # url = "https://db.netkeiba.com/horse/2019105219/"
    # print(f"Fetching {url}")
    df = scraper.get_past_races("2019105219")
    if df.empty:
        print("DF is empty. Checking raw soup for 'db_h_race_results'...")
        soup = scraper._get_soup(f"https://db.netkeiba.com/horse/result/2019105219/")
        if soup:
             t = soup.select_one("table.db_h_race_results")
             print(f"Selector 'table.db_h_race_results' found: {t is not None}")
             if not t:
                 print("Trying fallback 'table' with '着順'...")
                 tables = soup.find_all("table")
                 found = False
                 for i, tbl in enumerate(tables):
                     print(f"Table {i} classes: {tbl.get('class')}")
                     if "着順" in tbl.text or "着 順" in tbl.text or "日付" in tbl.text:
                         print("Found a table with '着順/日付'.")
                         # print(str(tbl)[:200])
                         t = tbl
                         found = True
                         break
                 if not found:
                     print("No table with '着順' found in soup.")
                     print("Soup snippet:", soup.text[:500])
                 else:
                    # Retry parsing with found table
                     try:
                        df = pd.read_html(str(t))[0]
                        print("Retry DF Head:")
                        print(df.head())
                     except Exception as e:
                        print(f"Retry parsing failed: {e}")
        else:
            print("Soup is None.")
    else:
        print(df.head())
        print("Columns:", df.columns)
