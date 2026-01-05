import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# ==========================================
# RaceScraper Class Definition
# ==========================================

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
        try:
            df = pd.read_html(io.StringIO(str(table)))[0]
            
            # Basic cleaning
            df = df.dropna(how='all')
            
            # Normalize column names (remove spaces/newlines)
            df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)

            # Filter rows that look like actual races (Date column exists)
            if '日付' in df.columns:
                df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
                df = df.dropna(subset=['date_obj'])
                df = df.sort_values('date_obj', ascending=False)
                
            # Take top N
            if n_samples:
                df = df.head(n_samples)
            
            # Process Run Style (Leg Type)
            if '通過' in df.columns:
                df['run_style_val'] = df['通過'].apply(self.extract_run_style)
            else:
                df['run_style_val'] = 3 # Unknown

            # Extract/Rename Columns
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
                '馬場': 'condition', # 良/重/稍重 etc.
                'タイム': 'time',
                '着差': 'margin',
                '上り': 'last_3f',
                '通過': 'passing',
                '馬体重': 'horse_weight',
                'run_style_val': 'run_style',
                '単勝': 'odds',
                '距離': 'raw_distance' # e.g. "芝1600"
            }
            
            # Rename available columns
            df.rename(columns=column_map, inplace=True)
            
            # Extract Surface and Distance from 'raw_distance'
            if 'raw_distance' in df.columns:
                def parse_dist(x):
                    if not isinstance(x, str): return None, None
                    # "芝1600", "ダ1200", "障3000"
                    surf = None
                    dist = None
                    if '芝' in x: surf = '芝'
                    elif 'ダ' in x: surf = 'ダ'
                    elif '障' in x: surf = '障'
                    
                    # Extract number
                    match = re.search(r'(\d+)', x)
                    if match:
                        dist = int(match.group(1))
                    return surf, dist

                parsed = df['raw_distance'].apply(parse_dist)
                df['course_type'] = parsed.apply(lambda x: x[0])
                df['distance'] = parsed.apply(lambda x: x[1])
            else:
                df['course_type'] = None
                df['distance'] = None

            # Coerce numeric
            if 'rank' in df.columns:
                df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
            
            if 'odds' in df.columns:
                 df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
            
            # Fill missing
            for target_col in list(column_map.values()) + ['course_type', 'distance']:
                if target_col not in df.columns:
                    df[target_col] = None
                
            return df
            
        except Exception as e:
            # print(f"Error parsing past races for {horse_id}: {e}")
            return pd.DataFrame()

    def extract_run_style(self, passing_str):
        """
        Converts passing order string (e.g., "1-1-1", "10-10-12") to run style (1,2,3,4).
        """
        if not isinstance(passing_str, str):
            return 3 # Default to Mid
            
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
            elif first_corner <= 9: 
                return 3 # Sashi
            else:
                return 4 # Oikomi
                
        except:
            return 3

# ==========================================
# Main Logic
# ==========================================

def fetch_race_horse_ids(rid):
    """
    Worker function to fetch horse IDs for a single race.
    Returns (race_id, {horse_name: horse_id}) or None
    """
    scraper = RaceScraper()
    try:
        url = f"https://race.netkeiba.com/race/result.html?race_id={rid}"
        soup = scraper._get_soup(url)
        if not soup: return None
        
        table = soup.find("table", id="All_Result_Table")
        if not table: return None
        
        horse_map = {}
        rows = table.find_all("tr", class_="HorseList")
        for row in rows:
            name_tag = row.select_one(".Horse_Name a")
            if name_tag:
                h_name = name_tag.text.strip()
                href = name_tag.get('href', '')
                match = re.search(r'/horse/(\d+)', href)
                if match:
                    horse_map[h_name] = match.group(1)
        return (rid, horse_map)
    except Exception as e:
        print(f"Error fetching race {rid}: {e}")
        return None

def fetch_horse_history(horse_id):
    """
    Worker to fetch history for a single horse.
    Returns (horse_id, history_df)
    """
    scraper = RaceScraper()
    try:
        # We need ONE instance per thread ideally, or simple requests
        # RaceScraper is lightweight
        df = scraper.get_past_races(str(horse_id), n_samples=None)
        return (horse_id, df)
    except Exception as e:
        print(f"Error fetching horse {horse_id}: {e}")
        return (horse_id, pd.DataFrame())

def fill_missing_past_data(csv_path="database.csv"):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Please upload 'database.csv' to Colab.")
        return

    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)

    # Ensure date column is datetime for comparison
    if '日付' in df.columns:
        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    else:
        print("Error: '日付' column not found.")
        return

    if 'horse_id' not in df.columns:
        df['horse_id'] = None

    # ==================================================
    # 1. Fill Missing Horse IDs (Parallel)
    # ==================================================
    if 'race_id' in df.columns:
        # Check masks
        missing_mask = df['horse_id'].isna() | (df['horse_id'] == '')
        
        if missing_mask.any():
            races_to_update = df.loc[missing_mask, 'race_id'].unique()
            print(f"Need to fetch IDs for {len(races_to_update)} races via Parallel Scraping...")
            
            # Using specific max_workers for Colab (usually 2-4 cores, but network bound so 10 is fine)
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(fetch_race_horse_ids, rid): rid for rid in races_to_update}
                
                completed_count = 0
                total = len(races_to_update)
                
                for future in as_completed(futures):
                    result = future.result()
                    completed_count += 1
                    if completed_count % 10 == 0:
                        print(f"  [IDs] Progress: {completed_count}/{total}")
                        
                    if result:
                        rid, horse_map = result
                        if horse_map:
                            race_indices = df[df['race_id'] == rid].index
                            for idx in race_indices:
                                h_name = df.at[idx, '馬名']
                                if h_name in horse_map:
                                    df.at[idx, 'horse_id'] = horse_map[h_name]
            
            print("Saving updated IDs to database.csv...")
            df.to_csv(csv_path, index=False)
        else:
            print("All Horse IDs present.")

    # ==================================================
    # 2. Fill Past History (Parallel)
    # ==================================================
    
    # Fields to populate
    fields_map = {
        'date': 'date',
        'rank': 'rank',
        'time': 'time',
        'run_style': 'run_style',
        'race_name': 'race_name',
        'last_3f': 'last_3f',
        'horse_weight': 'horse_weight',
        'jockey': 'jockey',
        'condition': 'condition',
        'odds': 'odds',
        'weather': 'weather',
        'distance': 'distance',
        'course_type': 'course_type'
    }

    unique_horses = df['horse_id'].dropna().unique()
    print(f"Found {len(unique_horses)} unique horses. Fetching history in parallel...")
    
    # We only need to fetch history for unique horses
    # Then populate the DF rows
    
    # Store history in a local dict first
    history_store = {}
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_horse_history, hid): hid for hid in unique_horses}
        
        completed_count = 0
        total = len(unique_horses)
        
        for future in as_completed(futures):
            hid, hist_df = future.result()
            history_store[hid] = hist_df
            
            completed_count += 1
            if completed_count % 50 == 0:
                print(f"  [History] Progress: {completed_count}/{total}")

    print("Applying history data to DataFrame...")
    
    # Apply to DF
    # Iterating DF rows is fast.
    for idx, row in df.iterrows():
        hid = row.get('horse_id')
        current_date = row.get('date_dt')
        
        if pd.notna(hid) and hid in history_store:
            hist_df = history_store[hid]
            if hist_df.empty: continue
            
            # Ensure date obj
            if 'date_obj' not in hist_df.columns and 'date' in hist_df.columns:
                 hist_df['date_obj'] = pd.to_datetime(hist_df['date'], format='%Y/%m/%d', errors='coerce')
            
            if 'date_obj' not in hist_df.columns: continue

            if pd.isna(current_date): continue
            
            # Filter
            past_races = hist_df[hist_df['date_obj'] < current_date].sort_values('date_obj', ascending=False).head(5)
            
            for i, (p_idx, p_row) in enumerate(past_races.iterrows()):
                 n = i + 1
                 if n > 5: break
                 
                 for field_key, field_col in fields_map.items():
                     val = p_row.get(field_col)
                     df.at[idx, f"past_{n}_{field_key}"] = val

    # Drop temp column
    if 'date_dt' in df.columns:
        df.drop(columns=['date_dt'], inplace=True)

    print(f"Saving final result to {csv_path}...")
    df.to_csv(csv_path, index=False)
    print("Done!")

if __name__ == "__main__":
    fill_missing_past_data()
