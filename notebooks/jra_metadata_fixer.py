import pandas as pd
import sys
import os
import re
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ==========================================
# CONFIGURATION
# ==========================================
# Adjust this path if running locally or on Colab
# On Colab: '/content/drive/MyDrive/dai-keiba'
# On Local: Current directory or specific path
PROJECT_PATH = '.' 
if os.path.exists('/content/drive/MyDrive/dai-keiba'):
    PROJECT_PATH = '/content/drive/MyDrive/dai-keiba'

sys.path.append(os.path.join(PROJECT_PATH, 'scraper'))

# TQDM progress bar
try:
    from tqdm.auto import tqdm
except ImportError:
    # Fallback if not installed
    def tqdm(iterable, total=None, desc=""):
        return iterable

# Ensure scraper path and import
try:
    from scraper.race_scraper import RaceScraper
except ImportError:
    # Try local import if relative
    try:
        from scraper.race_scraper import RaceScraper
    except:
        print("Warning: Could not import RaceScraper. Make sure you are in the project root.")

# ==========================================
# ROBUST METADATA FETCHER
# ==========================================
def local_get_race_metadata(rid):
    """
    Fetches Turn, Weather, Course, Condition from Netkeiba Race Page.
    Designed to be robust and self-contained.
    """
    url = f"https://race.netkeiba.com/race/result.html?race_id={rid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        import requests
        from bs4 import BeautifulSoup
        
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP' # Netkeiba Race usually EUC-JP
        if resp.status_code != 200: return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        data = {'race_id': rid}
        
        rd1 = soup.select_one(".RaceData01")
        if rd1:
            txt = rd1.text.strip()
            
            # Weather
            if "天候:晴" in txt: data["weather"] = "晴"
            elif "天候:曇" in txt: data["weather"] = "曇"
            elif "天候:小雨" in txt: data["weather"] = "小雨"
            elif "天候:雨" in txt: data["weather"] = "雨"
            elif "天候:雪" in txt: data["weather"] = "雪"
            
            # Condition
            if "馬場:良" in txt: data["condition"] = "良"
            elif "馬場:稍" in txt: data["condition"] = "稍重"
            elif "馬場:重" in txt: data["condition"] = "重"
            elif "馬場:不良" in txt: data["condition"] = "不良"
            
            # Course
            match = re.search(r'(芝|ダ|障)(\d+)m', txt)
            if match:
                ctype_raw = match.group(1)
                if ctype_raw == "芝": data["course_type"] = "芝"
                elif ctype_raw == "ダ": data["course_type"] = "ダート"
                elif ctype_raw == "障": data["course_type"] = "障害"
                data["distance"] = match.group(2)
            
            # Turn
            if "右" in txt: data["turn"] = "右"
            elif "左" in txt: data["turn"] = "左"
            elif "直線" in txt: data["turn"] = "直"
            
        return data
    except Exception as e:
        return None

# ==========================================
# MAIN EXECUTION
# ==========================================
def fill_missing_past_data_robust():
    csv_path = os.path.join(PROJECT_PATH, 'data/raw/database.csv')
    if not os.path.exists(csv_path):
        # Driver-specific path fallback
        csv_path = os.path.join(PROJECT_PATH, 'database.csv')
        
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found.')
        return

    print(f'Reading {csv_path}...')
    df = pd.read_csv(csv_path, low_memory=False, dtype={'race_id': str})
    
    # Ensure columns exist
    print('Checking Metadata (Course, Distance, Weather, Turn)...')
    meta_cols = ['コースタイプ', '距離', '天候', '馬場状態', '回り']
    for c in meta_cols:
        if c not in df.columns: df[c] = None

    # Identify missing rows
    missing_meta_mask = (df['コースタイプ'].isna()) | (df['コースタイプ'] == '') | (df['回り'].isna())
    if 'race_id' in df.columns:
         rids_missing = df.loc[missing_meta_mask, 'race_id'].astype(str).unique()
    else:
         rids_missing = []

    print(f'Found {len(rids_missing)} races with missing metadata.')

    if len(rids_missing) > 0:
        BATCH_SIZE = 50 
        batch_buffer = {}
        processed_count = 0
        
        print("Starting batch processing... (Saving every 50 races)")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(local_get_race_metadata, rid): rid for rid in rids_missing}
            
            for future in tqdm(as_completed(futures), total=len(rids_missing), desc="Fetching Metadata"):
                try:
                    data = future.result()
                    if data and data.get('course_type'):
                        batch_buffer[str(data['race_id'])] = data
                except: pass
                
                processed_count += 1
                
                # BATCH SAVE
                if len(batch_buffer) >= BATCH_SIZE:
                    print(f'  Saving batch... ({processed_count}/{len(rids_missing)})')
                    
                    df['race_id_str'] = df['race_id'].astype(str)
                    mask = df['race_id_str'].isin(batch_buffer.keys())
                    
                    # Create maps
                    c_map = {rid: d.get('course_type') for rid, d in batch_buffer.items()}
                    d_map = {rid: d.get('distance') for rid, d in batch_buffer.items()}
                    w_map = {rid: d.get('weather') for rid, d in batch_buffer.items()}
                    cond_map = {rid: d.get('condition') for rid, d in batch_buffer.items()}
                    t_map = {rid: d.get('turn') for rid, d in batch_buffer.items()}

                    # Update DataFrame
                    df.loc[mask, 'コースタイプ'] = df.loc[mask, 'race_id_str'].map(c_map).fillna(df.loc[mask, 'コースタイプ'])
                    df.loc[mask, '距離'] = df.loc[mask, 'race_id_str'].map(d_map).fillna(df.loc[mask, '距離'])
                    df.loc[mask, '天候'] = df.loc[mask, 'race_id_str'].map(w_map).fillna(df.loc[mask, '天候'])
                    df.loc[mask, '馬場状態'] = df.loc[mask, 'race_id_str'].map(cond_map).fillna(df.loc[mask, '馬場状態'])
                    df.loc[mask, '回り'] = df.loc[mask, 'race_id_str'].map(t_map).fillna(df.loc[mask, '回り'])
                    
                    # Save to CSV
                    temp_df = df.drop(columns=['race_id_str'], errors='ignore')
                    temp_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    
                    # Clear buffer
                    batch_buffer = {}
            
            # FINAL SAVE
            if batch_buffer:
                print('  Saving final batch...')
                df['race_id_str'] = df['race_id'].astype(str)
                mask = df['race_id_str'].isin(batch_buffer.keys())
                
                c_map = {rid: d.get('course_type') for rid, d in batch_buffer.items()}
                d_map = {rid: d.get('distance') for rid, d in batch_buffer.items()}
                w_map = {rid: d.get('weather') for rid, d in batch_buffer.items()}
                cond_map = {rid: d.get('condition') for rid, d in batch_buffer.items()}
                t_map = {rid: d.get('turn') for rid, d in batch_buffer.items()}

                df.loc[mask, 'コースタイプ'] = df.loc[mask, 'race_id_str'].map(c_map).fillna(df.loc[mask, 'コースタイプ'])
                df.loc[mask, '距離'] = df.loc[mask, 'race_id_str'].map(d_map).fillna(df.loc[mask, '距離'])
                df.loc[mask, '天候'] = df.loc[mask, 'race_id_str'].map(w_map).fillna(df.loc[mask, '天候'])
                df.loc[mask, '馬場状態'] = df.loc[mask, 'race_id_str'].map(cond_map).fillna(df.loc[mask, '馬場状態'])
                df.loc[mask, '回り'] = df.loc[mask, 'race_id_str'].map(t_map).fillna(df.loc[mask, '回り'])
                
                df.drop(columns=['race_id_str'], inplace=True, errors='ignore')
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')

        print('Done filling metadata.')
    else:
        print('All metadata present.')

if __name__ == "__main__":
    fill_missing_past_data_robust()
