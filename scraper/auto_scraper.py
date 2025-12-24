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
print("DEBUG: auto_scraper module loaded (Version: Fix-Meta-Insert)")
# Root directory (parent of scraper) -> data/raw/database.csv
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "database.csv")
CSV_FILE_PATH_NAR = os.path.join(PROJECT_ROOT, "data", "raw", "database_nar.csv")
TARGET_YEARS = [2024, 2025] # Expandable
TARGET_YEARS = [2024, 2025] # Expandable
HORSE_HISTORY_CACHE = {} # Cache for horse history DataFrames
HORSE_PROFILE_CACHE = {} # Cache for horse profile (pedigree)

# ==========================================
# ユーティリティ関数: 既存race_idの取得
# ==========================================
def get_existing_race_ids(mode="JRA", db_path=None, csv_path=None):
    """
    既存のrace_idを取得（SQLiteまたはCSVから）

    Args:
        mode: "JRA" または "NAR"
        db_path: SQLiteデータベースのパス（優先）
        csv_path: CSVファイルのパス（フォールバック）

    Returns:
        set: 既存のrace_idのセット
    """
    existing_ids = set()

    # SQLiteから取得を試みる
    if db_path and os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            table_name = f"processed_data_{mode.lower()}"

            # テーブルの存在確認
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )

            if cursor.fetchone():
                query = f"SELECT DISTINCT race_id FROM {table_name}"
                df = pd.read_sql_query(query, conn)
                existing_ids = set(df['race_id'].astype(str))
                print(f"✅ SQLiteから既存race_id取得: {len(existing_ids)}件")
            else:
                print(f"⚠️ テーブル '{table_name}' が見つかりません")

            conn.close()
            return existing_ids
        except Exception as e:
            print(f"⚠️ SQLiteからの取得に失敗: {e}")
            print("   CSVファイルから取得を試みます...")

    # CSVから取得（フォールバック）
    if csv_path is None:
        csv_path = CSV_FILE_PATH_NAR if mode == "NAR" else CSV_FILE_PATH

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            if 'race_id' in df.columns:
                existing_ids = set(df['race_id'].astype(str))
                print(f"✅ CSVから既存race_id取得: {len(existing_ids)}件")
            else:
                print(f"⚠️ CSVに'race_id'カラムが見つかりません")
        except Exception as e:
            print(f"⚠️ CSVからの取得に失敗: {e}")
    else:
        print(f"ℹ️ 既存データが見つかりません（初回スクレイピング）")

    return existing_ids


def find_missing_races(start_date, end_date, existing_race_ids, mode="JRA"):
    """
    指定期間内で欠落しているレースを検出（年度別分析を含む）

    Args:
        start_date: 開始日（datetime.date or datetime）
        end_date: 終了日（datetime.date or datetime）
        existing_race_ids: 既存のrace_idのセット
        mode: "JRA" または "NAR"

    Returns:
        dict: {
            'total_days': 全日数,
            'weekend_days': 週末日数,
            'existing_race_dates': 既存レース日数,
            'missing_weekend_dates': 欠落週末リスト,
            'coverage_rate': カバレッジ率,
            'yearly_coverage': 年度別カバレッジ情報,
            'missing_years': 完全に欠けている年度リスト
        }
    """
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    # 既存race_idから日付パターンを抽出
    # race_id format: YYYYMMDDKKPPRRNN (例: 2024112303051201)
    # YYYY: 年, MM: 月, DD: 日, KK: 開催, PP: 場所, RR: レース番号, NN: 不明

    existing_dates = set()
    existing_dates_by_year = {}  # 年度別の既存日付

    for race_id in existing_race_ids:
        if len(race_id) >= 8:
            try:
                date_str = race_id[:8]  # YYYYMMDD
                race_date = datetime.strptime(date_str, "%Y%m%d").date()
                if start_date <= race_date <= end_date:
                    existing_dates.add(race_date)

                    # 年度別にグループ化
                    year = race_date.year
                    if year not in existing_dates_by_year:
                        existing_dates_by_year[year] = set()
                    existing_dates_by_year[year].add(race_date)
            except:
                pass

    # 全期間の日数
    total_days = (end_date - start_date).days + 1

    # 年度別の統計情報を計算
    yearly_coverage = {}
    target_years = range(start_date.year, end_date.year + 1)

    for year in target_years:
        # その年の範囲を決定
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        # 期間との重なりを考慮
        actual_start = max(year_start, start_date)
        actual_end = min(year_end, end_date)

        # その年の週末日数をカウント
        year_weekends = 0
        current = actual_start
        while current <= actual_end:
            if current.weekday() in [5, 6]:
                year_weekends += 1
            current += timedelta(days=1)

        # その年の既存レース日数
        year_existing = len(existing_dates_by_year.get(year, set()))

        # カバレッジ率
        coverage = year_existing / year_weekends if year_weekends > 0 else 0

        yearly_coverage[year] = {
            'weekend_days': year_weekends,
            'existing_race_dates': year_existing,
            'coverage_rate': coverage,
            'start_date': actual_start,
            'end_date': actual_end
        }

    # 完全に欠けている年度を検出（カバレッジ0%の年）
    missing_years = [year for year, info in yearly_coverage.items()
                     if info['coverage_rate'] == 0 and info['weekend_days'] > 0]

    # 土日の日数を概算（レースは主に週末）
    weekend_days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() in [5, 6]:  # 土曜日=5, 日曜日=6
            weekend_days += 1
        current += timedelta(days=1)

    # 欠落している可能性のある週末を検出
    missing_dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() in [5, 6]:  # 週末のみチェック
            if current not in existing_dates:
                missing_dates.append(current)
        current += timedelta(days=1)

    result = {
        'total_days': total_days,
        'weekend_days': weekend_days,
        'existing_race_dates': len(existing_dates),
        'missing_weekend_dates': missing_dates,
        'coverage_rate': len(existing_dates) / weekend_days if weekend_days > 0 else 0,
        'yearly_coverage': yearly_coverage,
        'missing_years': missing_years
    }

    return result


# ==========================================
# 1. レース詳細データを取得する関数
# ==========================================
def scrape_race_data(race_id, mode="JRA"):
    base_domain = "nar.netkeiba.com" if mode == "NAR" else "race.netkeiba.com"
    url = f"https://{base_domain}/race/result.html?race_id={race_id}"
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

        # --- コース情報抽出 (RaceData01) ---
        # Format: "14:15発走 / ダ1200m (左) / 天候:小雨 / 馬場:良"
        surface_type = ""
        distance = ""
        rotation = ""
        weather = ""
        condition = ""

        racedata1 = soup.select_one(".RaceData01")
        if racedata1:
            raw_text = racedata1.text.replace("\n", "").strip()
            
            # Surface & Distance & Rotation
            # Matches: 芝1600m or 芝2000m (右) or ダ1200m (左)
            # Regex: (芝|ダ|障)(\d+)m(?:\s*\((.*?)\))?
            
            match_course = re.search(r'(芝|ダ|障)(\d+)m(?:\s*\((.*?)\))?', raw_text)
            if match_course:
                surface_type = match_course.group(1) # 芝/ダ
                distance = match_course.group(2)     # 2000
                rotation = match_course.group(3) if match_course.group(3) else "直線" if "直線" in raw_text else ""
            
            # Weather
            match_weather = re.search(r'天候:(\S+)', raw_text)
            if match_weather:
                weather = match_weather.group(1)
            
            # Condition
            match_cond = re.search(r'馬場:(\S+)', raw_text)
            if match_cond:
                condition = match_cond.group(1)

            # Debug check
            # print(f"Parsed: {surface_type} {distance}m {rotation} En:{weather} Cond:{condition}")

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

            # 列追加 (既に存在する場合はスキップまたは上書き)
            meta_cols = [
                ("日付", date_text), ("会場", venue_text), ("レース番号", race_num_text),
                ("レース名", race_name_text), ("重賞", grade_text), ("コースタイプ", surface_type),
                ("距離", distance), ("回り", rotation), ("天候", weather), ("馬場状態", condition)
            ]
            
            # 挿入位置(0から順に)
            # insertを使うと既存列は右にずれるため、0番目に順次追加する場合、
            # 逆順に入れるか、インデックスをずらすか。
            # 元のコード: df.insert(0, ...), df.insert(1, ...) 
            # これは 0に入れた後、次のinsert(1)は「新0番目の次」に入れる。つまり先頭から順に並ぶ。
            
            for i, (col, val) in enumerate(meta_cols):
                if col not in df.columns:
                    df.insert(i, col, val)
                else:
                    df[col] = val
            
            # Additional Bloodline Columns (Empty init)
            df["father"] = ""
            df["mother"] = ""
            df["bms"] = ""
            
            df["race_id"] = race_id # IDも保存 (末尾に追加されることが多いが明示的に)
            
            # 不要な列が含まれることがあるので整理しても良いが、
            # ユーザー要望は「蓄積」なので、基本はそのまま保持する
            
            # Extract Horse IDs via Name Mapping (Robust)
            horse_name_map = {}
            for tr in target_table.find_all("tr"):
                a_tag = tr.select_one(".Horse_Name a")
                if a_tag:
                    h_name = a_tag.text.strip().replace("\n", "")
                    href = a_tag.get('href')
                    hid_match = re.search(r'/horse/(\d+)', href)
                    if hid_match:
                        horse_name_map[h_name] = hid_match.group(1)
            
            
            # Apply to DF (Mapping by Name)
            # Ensure df['馬名'] is clean matches key
            if '馬名' in df.columns:
                df['horse_id'] = df['馬名'].map(horse_name_map).fillna("")
            else:
                df['horse_id'] = ""
                
            # If mapping largely failed (e.g. name mismatch), warn
            if len(df) > 0 and (df['horse_id'] == "").sum() > len(df) * 0.5:
                 print(f"Warning: High ID miss rate for {race_id}. Names might differ.")
                 # Fallback: Try strict index alignment if map failed? 
                 # But map is usually safer.
                 # Debug:
                 # print("DF Names:", df['馬名'].unique())
                 # print("Map Keys:", list(horse_name_map.keys()))

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
            # Added: last_3f, horse_weight, jockey, weight_carried, condition, odds, weather, distance, course_type
            p_fields = ['date', 'rank', 'time', 'run_style', 'race_name', 'last_3f', 'horse_weight', 'jockey', 'condition', 'odds', 'weather', 'distance', 'course_type']
            
            for i in range(1, 6):
                for f in p_fields:
                    past_columns.append(f"past_{i}_{f}")
            
            # Pre-fill empty
            for col in past_columns:
                df[col] = None

            for idx, row in df.iterrows():
                hid = row.get('horse_id')
                if hid and str(hid).isdigit():
                    # Use Cache to avoid repeated requests
                    global HORSE_HISTORY_CACHE
                    if hid in HORSE_HISTORY_CACHE:
                        past_df = HORSE_HISTORY_CACHE[hid].copy()
                    else:
                        past_df = scraper.get_past_races(hid, n_samples=None) # Fetch ALL
                        HORSE_HISTORY_CACHE[hid] = past_df
                        past_df = past_df.copy()
                    
                    # --- Fetch Bloodline Data ---
                    global HORSE_PROFILE_CACHE
                    profile_data = None
                    if hid in HORSE_PROFILE_CACHE:
                        profile_data = HORSE_PROFILE_CACHE[hid]
                    else:
                         profile_data = scraper.get_horse_profile(hid)
                         HORSE_PROFILE_CACHE[hid] = profile_data
                    
                    if profile_data:
                        df.at[idx, 'father'] = profile_data.get('father', '')
                        df.at[idx, 'mother'] = profile_data.get('mother', '')
                        df.at[idx, 'bms'] = profile_data.get('bms', '')
                        
                    # past_df = scraper.get_past_races(hid, n_samples=20) # Old method
                    
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
                             df.at[idx, f"past_{n}_weather"] = p_row.get('weather')
                             df.at[idx, f"past_{n}_distance"] = p_row.get('distance')
                             df.at[idx, f"past_{n}_course_type"] = p_row.get('course_type')
            
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
def scrape_todays_schedule(mode="JRA"):
    """
    Scrapes race list for today + next 7 days (Total 8 days).
    Saves to 'todays_data.json' (JRA) or 'todays_data_nar.json' (NAR).
    mode: "JRA" or "NAR"
    """
    import json
    
    race_list = []
    today = datetime.now()
    
    print(f"Fetching schedule for next 8 days (Mode: {mode})...")
    
    today = datetime.now()
    # Fetch previous 7 days and next 7 days (Total 15 days) as requested
    date_range = range(-7, 8)
    
    race_list = []
    
    print(f"Fetching schedule for range [{today + timedelta(days=-7):%Y-%m-%d} to {today + timedelta(days=7):%Y-%m-%d}] (Mode: {mode})...")
    
    for i in date_range:
        target_date = today + timedelta(days=i)
        date_str = target_date.strftime('%Y%m%d')
        
        # JRA/NAR specific logic if needed for URL? They seem to allow same param.
        # But JRA base is race.netkeiba, NAR is nar.netkeiba.
        base_domain = "nar.netkeiba.com" if mode == "NAR" else "race.netkeiba.com"
        url = f"https://{base_domain}/top/race_list_sub.html?kaisai_date={date_str}"
        headers = { "User-Agent": "Mozilla/5.0" }
        
        print(f" Checking {target_date.strftime('%Y-%m-%d')}...")
        try:
            # JRA sub-list also tends to group by venue in dl elements
            if i != 0: time.sleep(1)
            
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding 
            
            if not response.text: continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Unified Parsing Logic (Works for both JRA sub-list and NAR)
            venue_item_pairs = []
            
            wrapper = soup.select_one('.RaceList_Box')
            venue_blocks = []
            if wrapper:
                venue_blocks = wrapper.find_all('dl', recursive=False)
            
            # JRA might fallback to .RaceList_DataList if only one venue or older format?
            # But debug showed JRA using dl too.
            
            if not venue_blocks and wrapper and wrapper.name == 'dl':
                 venue_blocks = [wrapper]

            # If still found nothing but items exist (flat list structure fallback)
            if not venue_blocks:
                 items = soup.select('.RaceList_DataList .RaceList_DataItem')
                 if not items and wrapper: items = wrapper.select('.RaceList_DataItem')
                 for it in items: venue_item_pairs.append(("Unknown", it))
            else:
                for block in venue_blocks:
                    venue_name = "Unknown"
                    dt = block.select_one('dt')
                    if dt:
                        txt = dt.text.replace("\n", " ").strip()
                        
                        # 1. Try NAR pattern "高知競馬場TOP"
                        m_nar = re.search(r'(\S+?)競馬場', txt)
                        if m_nar:
                            venue_name = m_nar.group(1)
                        else:
                            # 2. Try JRA pattern "5回 中山 7日目"
                            # Matches "N回 Venue N日目"
                            m_jra = re.search(r'\d+回\s*(\S+)\s*\d+日目', txt)
                            if m_jra:
                                venue_name = m_jra.group(1)
                            else:
                                # 3. Fallback: Search for known venue names
                                # JRA + NAR
                                known_venues = r'(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉|帯広|門別|盛岡|水沢|浦和|船橋|大井|川崎|金沢|笠松|名古屋|園田|姫路|高知|佐賀)'
                                match_v = re.search(known_venues, txt)
                                if match_v:
                                    venue_name = match_v.group(1)

                    sub_items = block.select('.RaceList_DataItem')
                    for it in sub_items:
                        venue_item_pairs.append((venue_name, it))

            if not venue_item_pairs:
                continue # No races today
                
            print(f"  Found {len(venue_item_pairs)} races for {target_date.strftime('%Y-%m-%d')}.")
            
            for venue_cache, item in venue_item_pairs:
                link_elem = item.find('a')
                if not link_elem: continue
                
                href = link_elem.get('href', '')
                race_id_match = re.search(r'race_id=(\d+)', href)
                if not race_id_match: continue
                
                race_id = race_id_match.group(1)
                
                title_elem = item.select_one('.RaceList_ItemTitle')
                race_name = title_elem.text.strip() if title_elem else "Unknown Race"
                
                venue = "Unknown"
                number = ""
                
                if venue_cache and venue_cache != "Unknown":
                    venue = venue_cache
                else:
                    # Last resort fallback if header parsing failed (JRA flat list?)
                    meta_elem = item.select_one('.RaceList_Item02')
                    if meta_elem:
                         meta_txt = meta_elem.text.strip()
                         # e.g. "中山1R"
                         vm = re.search(r'(\D+)(\d+)R', meta_txt)
                         if vm:
                             venue = vm.group(1).strip()
                             # Update number if found
                             if not number: number = vm.group(2)
                
                # Try to extract race number from .Race_Num (Robust for both)
                num_elem = item.select_one('.Race_Num')
                if num_elem:
                    num_txt = num_elem.text.strip()
                    nm = re.search(r'(\d+)R', num_txt)
                    if nm: number = nm.group(1)
                
                if not number: number = "1" # Default
                
                # For odds, only check Today (i==0)
                horses = []
                if i == 0:
                     # Only scrape odds for today to save time
                     horses = scrape_odds_for_race(race_id, mode=mode)
                
                race_info = {
                    "id": race_id,
                    "date": target_date.strftime("%Y-%m-%d"),
                    "venue": venue,
                    "number": number,
                    "name": race_name,
                    "horses": horses
                }
                race_list.append(race_info)
                
        except Exception as e:
            print(f" Error fetching {date_str}: {e}")

    # Save to JSON
    # Save to JSON
    filename = "todays_data_nar.json" if mode == "NAR" else "todays_data.json"
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temp", filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"date": today.strftime("%Y-%m-%d"), "races": race_list}, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(race_list)} future races to {output_path}")
    return True, f"{len(race_list)} races saved (Next 1 week)."

def scrape_odds_for_race(race_id, mode="JRA"):
    """
    Fetches odds for a specific race_id.
    Tries API first, then falls back to Main Odds page.
    Returns list of {number, odds}
    """
    horses = []
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36" }
    
    print(f"  Scraping odds for {race_id} (Mode: {mode})...")
    
    base_domain = "nar.netkeiba.com" if mode == "NAR" else "race.netkeiba.com"
    
    # 1. Try API (odds_get_form.html)
    # The API might be shared on race.netkeiba.com even for NAR?
    # Or might be nar.netkeiba.com/odds/...
    # Let's try standard first, maybe it redirects or works.
    # Fallback is the main page which definitely uses nar.netkeiba.com for NAR.
    
    # Priority: 
    # 1. New JSON API (Try if JRA, skip if NAR as it says "jra_odds")
    # 2. Form API (odds_get_form)
    # 3. Main Page
    
    success_via_api = False
    
    # 1. Try JSON API (New) - Only for JRA as the endpoint is JRA specific
    if mode == "JRA":
        try:
            # type=1 usually returns Win (Tansho) odds in ['1']
            url = f"https://race.netkeiba.com/api/api_get_jra_odds.html?race_id={race_id}&type=1&action=init"
            response = requests.get(url, headers=headers, timeout=10)
            
            # Check if JSON
            if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
                data = response.json()
                if data.get('status') == 'result':
                    # Parse Odds
                    # Structure: data['data']['odds']['1']['01'] = [odds, ?, ?]
                    odds_data = data.get('data', {}).get('odds', {}).get('1', {})
                    
                    temp_horses = []
                    for h_num_str, val_list in odds_data.items():
                        if not val_list or len(val_list) == 0: continue
                        
                        try:
                            num = int(h_num_str)
                            odds_str = val_list[0]
                            if odds_str and '---' not in odds_str:
                                odds = float(odds_str)
                                temp_horses.append({"number": num, "odds": odds})
                        except: continue
                    
                    if temp_horses:
                        print(f"  Got {len(temp_horses)} odds via JSON API.")
                        return temp_horses
            
        except Exception as e:
            print(f"  JSON API Error: {e}")

    # 2. Fallback Main Page
    try:
        url_main = f"https://{base_domain}/odds/index.html?race_id={race_id}"
        if mode == "NAR":
             url_main += "&type=b1"
             
        response = requests.get(url_main, headers=headers, timeout=10)
        response.encoding = 'EUC-JP' 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try finding the "Tanfuku" table (Umaban order) first, then "Ninki" (Rank order)
        # Usually Tanfuku is active by default? 
        # Tables with class 'RaceOdds_HorseList_Table'
        
        tables = soup.select('table.RaceOdds_HorseList_Table')
        target_table = None
        
        # Heuristic: Look for table with "馬番" in header
        for t in tables:
            if "馬番" in t.text and ("単勝" in t.text or "オッズ" in t.text):
                target_table = t
                break
        
        # If not found, try #Ninki
        if not target_table:
             target_table = soup.select_one('table#Ninki')
             
        if not target_table:
             print("  No odds table found on Main Page.")
             return []
             
        rows = target_table.find_all('tr')
        horses_map = {} # deduplicate by number

        for row in rows:
            if row.find('th'): continue
            cols = row.find_all('td')
            if not cols: continue
            
            num = None
            odds = 0.0
            
            # Strategy: look for digit column around index 1-3
            # And odds column with '.' around index 5-end
            
            # Try classes first
            u_el = row.select_one('.Umaban')
            # Prefer Tan_Odds specifically to avoid Fuku
            o_el = row.select_one('.Tan_Odds') or row.select_one('.Odds') 
            
            if u_el:
                 try:
                     num = int(u_el.text.strip())
                     if o_el:
                         ot = o_el.text.strip()
                         if '---' not in ot and ot:
                             odds = float(ot)
                 except: pass
            
            # If classes failed, try positional
            if num is None and len(cols) >= 5:
                # Guess index. 
                # If #Ninki: 2=Umaban, Odds is usually 9 or 10?
                # If Tanfuku: 1=Umaban? 
                # Let's check text
                try:
                    # Clean text
                    texts = [c.text.strip() for c in cols]
                    
                    # Find Umaban (1-18)
                    for i in [1, 2, 0]: # Priority check
                         if i < len(texts) and texts[i].isdigit() and 1 <= int(texts[i]) <= 18:
                             num = int(texts[i])
                             break
                    
                    # Find Odds (float)
                    # Search from specific index
                    if num is not None:
                        # Look for odds in later columns
                        # Odds often has "."
                        # Warning: Ninki table might have multiple odds?
                        for i in range(len(texts)-1, 2, -1): # Search backwards
                            if re.match(r'^\d+\.\d+$', texts[i]):
                                odds = float(texts[i])
                                break
                except: pass
            
            if num is not None and num not in horses_map:
                horses_map[num] = {"number": num, "odds": odds}
                
        horses = list(horses_map.values())
        print(f"  Got {len(horses)} odds via Main Page.")
        return horses

    except Exception as e:
        print(f"  Main Odds Error: {e}")
        return []

    return horses


def scrape_nar_year(year_str, start_date=None, end_date=None, save_callback=None, existing_race_ids=None):
    """
    Scrapes NAR races for a given year.
    Iterates every day.
    """
    print(f"=== Starting NAR Bulk Scraping for {year_str} ===")
    import time
    from datetime import timedelta
    
    try:
        y = int(year_str)
        # Determine range
        d_start = datetime(y, 1, 1).date()
        d_end = datetime(y, 12, 31).date()
        
        if start_date: d_start = max(d_start, start_date)
        if end_date: d_end = min(d_end, end_date)
            
        current = d_start
        headers = { "User-Agent": "Mozilla/5.0" }
        
        while current <= d_end:
            kaisai_date = current.strftime("%Y%m%d")
            url = f"https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}"
            
            print(f"Checking {current}...")
            
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                # Parse
                soup = BeautifulSoup(resp.content, 'html.parser')
                # Usually .RaceList_DataList -> .RaceList_DataItem
                items = soup.select('.RaceList_Box .RaceList_DataItem')
                if not items:
                    items = soup.select('.RaceList_DataList .RaceList_DataItem')
                    
                if items:
                    race_ids = []
                    for item in items:
                        a = item.find('a')
                        if a and 'href' in a.attrs:
                            # ../race/result.html?race_id=...
                             m = re.search(r'race_id=(\d+)', a['href'])
                             if m:
                                 race_ids.append(m.group(1))
                    
                    race_ids = sorted(list(set(race_ids)))
                    print(f"  Found {len(race_ids)} races.")
                    
                    for rid in race_ids:
                        # Skip if already exists
                        if existing_race_ids and rid in existing_race_ids:
                             print(f"    Skipping {rid} (Already exists)")
                             continue

                        # Scrape Result
                        df = scrape_race_data(rid, mode="NAR")
                        if df is not None and not df.empty:
                            if save_callback:
                                save_callback(df)
                        time.sleep(0.5)
                else:
                    print("  No races.")
                    
            except Exception as e:
                 print(f"  Error on {current}: {e}")
            
            current += timedelta(days=1)
            time.sleep(0.5)
            
    except Exception as e:
        print(f"Error in scrape_nar_year: {e}")

# ==========================================
# 2.5 Shutuba Scraping (Future Races)
# ==========================================
def scrape_shutuba_data(race_id, mode="JRA"):
    """
    Scrapes the Shutuba table (Future Race Card) for a given race ID.
    Enriches with past history from live DB (or local if configured).
    Returns DataFrame ready for feature engineering/prediction (similar to database.csv schema).
    """
    base_domain = "nar.netkeiba.com" if mode == "NAR" else "race.netkeiba.com"
    url = f"https://{base_domain}/race/shutuba.html?race_id={race_id}"
    
    headers = { 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36" 
    }
    
    print(f"Scraping Shutuba: {url} (Mode: {mode})")
    
    scraper = RaceScraper() # Initialize for pulling history later

    
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

        # --- Course Data Extraction (RaceData01) ---
        # Added to ensure feature engineering gets correct distance/surface/weather
        surface_type = ""
        distance = ""
        rotation = ""
        weather = "曇" # Default
        condition = "良" # Default

        racedata1 = soup.select_one(".RaceData01")
        if racedata1:
            raw_text = racedata1.text.replace("\n", "").strip()
            
            # Regex similar to scrape_race_data
            match_course = re.search(r'(芝|ダ|障)(\d+)m(?:\s*\((.*?)\))?', raw_text)
            if match_course:
                surface_type = match_course.group(1)
                distance = match_course.group(2)
                rotation = match_course.group(3) if match_course.group(3) else ("直線" if "直線" in raw_text else "")
            
            match_weather = re.search(r'天候:(\S+)', raw_text)
            if match_weather:
                weather = match_weather.group(1)
            
            match_cond = re.search(r'馬場:(\S+)', raw_text)
            if match_cond:
                condition = match_cond.group(1)
        
        # Parse Shutuba Table
        # Robust Selection: Find table with most HorseList rows
        candidate_tables = soup.find_all("table")
        table = None
        max_rows = 0
        
        for t in candidate_tables:
            c = len(t.select("tr.HorseList"))
            if c > max_rows:
                max_rows = c
                table = t
        
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
                "father": "", # Init
                "mother": "",
                "bms": "",
                "騎手": jockey,
                "斤量": weight,
                "race_id": race_id,
                # Add Metadata for FE
                "コースタイプ": surface_type,
                "距離": distance,
                "回り": rotation,
                "天候": weather,
                "馬場状態": condition
                # Add 性齢 if needed for Age feature
            }
            
            # Age extraction usually in .Barei or similar
            # Example: "牡3"
            # It's usually near Horse Name
            # Let's inspect typical structure or ignore for now if not critical (Feature Engineering defaults to 3)
            # Find td with class "Barei" ?
            # Find td with class "Barei" ?
            barei = row.select_one(".Barei")
            
            # --- Fetch Profile for Shutuba ---
            # Similar to scrape_race_data, use cache
            if horse_id and horse_id.isdigit():
                 global HORSE_PROFILE_CACHE
                 # Initialize if not present (handled at module level)
                 prof = None
                 if horse_id in HORSE_PROFILE_CACHE:
                     prof = HORSE_PROFILE_CACHE[horse_id]
                 else:
                     prof = scraper.get_horse_profile(horse_id)
                     if prof: HORSE_PROFILE_CACHE[horse_id] = prof
                 
                 if prof:
                     entry["father"] = prof.get("father", "")
                     entry["mother"] = prof.get("mother", "")
                     entry["bms"] = prof.get("bms", "")
            
            if barei:
                entry["性齢"] = barei.text.strip()
            else:
                entry["性齢"] = "牡3" # Default fallback
            
            data.append(entry)
            
        df = pd.DataFrame(data)
        
        # Merge Current Odds
        print(f"  Fetching current odds for {race_id}...")
        try:
            current_odds_list = scrape_odds_for_race(race_id, mode=mode)
            # Map by horse number (umaban)
            odds_map = {item['number']: item['odds'] for item in current_odds_list}
            
            # Add to DF
            df['単勝'] = df['馬 番'].apply(lambda x: odds_map.get(int(x) if str(x).isdigit() else 0, 0.0))
            df['Odds'] = df['単勝'] # Alias
        except Exception as e:
            print(f"Warning: Failed to fetch current odds: {e}")
            df['単勝'] = 0.0
            df['Odds'] = 0.0

        # Load History from CSV to avoid scraping
        csv_path = CSV_FILE_PATH_NAR if mode == "NAR" else CSV_FILE_PATH
        full_history = pd.DataFrame()
        
        if os.path.exists(csv_path):
             print(f"  Loading local history from {csv_path} for enrichment...")
             try:
                 # Read primarily needed columns to save memory/speed, or full if fine
                 # Read primarily needed columns to save memory/speed, or full if fine
                 # Force dtype to string to avoid float conversion (2012.0 -> "2012.0" != "2012")
                 full_history = pd.read_csv(csv_path, dtype={'horse_id': str, 'race_id': str})
                 if 'horse_id' in full_history.columns:
                     # Remove .0 if it exists (in case it was saved as float previously)
                     full_history['horse_id'] = full_history['horse_id'].astype(str).str.replace(r'\.0$', '', regex=True)
             except Exception as e:
                 print(f"  Failed to load CSV history: {e}")
                 full_history = pd.DataFrame()

        print(f"  Enriching {len(df)} horses with past data...")
        past_columns = []
        p_fields = ['date', 'rank', 'time', 'run_style', 'race_name', 'last_3f', 'horse_weight', 'jockey', 'condition', 'odds', 'weather', 'distance', 'course_type']
        
        for i in range(1, 6):
             for f in p_fields:
                past_columns.append(f"past_{i}_{f}")
        
        for col in past_columns:
            df[col] = None
            
        for idx, row in df.iterrows():
            hid = row.get('horse_id')
            if hid and str(hid).isdigit():
                # Use Cache
                global HORSE_HISTORY_CACHE
                
                # Try to fill cache from local CSV if not present
                if hid not in HORSE_HISTORY_CACHE and not full_history.empty:
                     if 'horse_id' in full_history.columns:
                         subset = full_history[full_history['horse_id'] == str(hid)]
                         if not subset.empty:
                             HORSE_HISTORY_CACHE[hid] = subset.copy()
                             
                if hid in HORSE_HISTORY_CACHE:
                    past_df = HORSE_HISTORY_CACHE[hid].copy()
                else:
                    past_df = scraper.get_past_races(hid, n_samples=None)
                    HORSE_HISTORY_CACHE[hid] = past_df
                    past_df = past_df.copy()

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
                         df.at[idx, f"past_{n}_date"] = p_row.get('date') or p_row.get('日付')
                         # Ensure Rank is extracted
                         df.at[idx, f"past_{n}_rank"] = p_row.get('rank') or p_row.get('着 順')
                         df.at[idx, f"past_{n}_time"] = p_row.get('time') or p_row.get('タイム')
                         
                         # run_style equivalent in DB seems to be 'コーナー 通過順' if processed, but usually raw scraper returns 'run_style'.
                         # If coming from DB, it might be 'コーナー 通過順' or 'run_style' if standardized? 
                         # DB header actually DOES NOT include 'run_style'. It has 'コーナー 通過順'.
                         # So if p_row is from DB, we need 'コーナー 通過順'.
                         df.at[idx, f"past_{n}_run_style"] = p_row.get('run_style') or p_row.get('コーナー 通過順')
                         
                         df.at[idx, f"past_{n}_race_name"] = p_row.get('race_name') or p_row.get('レース名')
                         df.at[idx, f"past_{n}_last_3f"] = p_row.get('last_3f') or p_row.get('後3F')
                         df.at[idx, f"past_{n}_horse_weight"] = p_row.get('horse_weight') or p_row.get('馬体重(増減)')
                         df.at[idx, f"past_{n}_jockey"] = p_row.get('jockey') or p_row.get('騎手')
                         df.at[idx, f"past_{n}_condition"] = p_row.get('condition') or p_row.get('馬場状態')
                         df.at[idx, f"past_{n}_weather"] = p_row.get('weather') or p_row.get('天候')
                         df.at[idx, f"past_{n}_distance"] = p_row.get('distance') or p_row.get('距離')
                         df.at[idx, f"past_{n}_course_type"] = p_row.get('course_type') or p_row.get('コースタイプ')
        
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
    parser.add_argument("--source", type=str, default="netkeiba", help="Scraping source: 'netkeiba' or 'jra'")
    parser.add_argument("--mode", type=str, default="JRA", help="Mode: 'JRA' or 'NAR'")
    
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
        # ⚠️ 重要: 最終日の翌日からではなく、固定の開始日から始める
        # 既存race_idは個別にスキップされるため、途中の欠落も検出できる
        # デフォルト: 2023年1月1日から（十分に古い日付）
        print("開始日が指定されていません。デフォルト: 2023-01-01")
        start_date = datetime(2023, 1, 1)

        # 既存データの最新日を参考情報として表示（ただし開始日には使わない）
        if os.path.exists(CSV_FILE_PATH):
            try:
                df_existing = pd.read_csv(CSV_FILE_PATH)
                if '日付' in df_existing.columns and not df_existing.empty:
                    df_existing['date_obj'] = pd.to_datetime(df_existing['日付'], format='%Y年%m月%d日', errors='coerce')
                    last_date = df_existing['date_obj'].max()

                    if pd.notna(last_date):
                        print(f"ℹ️ 既存データの最終日: {last_date.strftime('%Y-%m-%d')}")
                        print(f"💡 既存race_idは自動的にスキップされるため、欠落分のみ取得します")
            except Exception as e:
                print(f"既存CSV読み込みエラー: {e}")

    if start_date is None:
         # フォールバック
         print("デフォルト開始日: 2023-01-01")
         start_date = datetime(2023, 1, 1)

    return start_date, args.end, target_places, args.source, args.mode

# ==========================================
# 3. メイン実行処理
# ==========================================
def main(start_date_arg=None, end_date_arg=None, places_arg=None, source_arg=None, mode_arg=None, progress_callback=None):
    """
    progress_callback: function(str) -> None. If provided, call with status update.
    """
    print("=== 自動スクレイピング開始 ===")
    start_time = time.time()
    
    
    # Pass arguments to helper
    start_date, end_arg_cli, places, source_cli, mode_cli = get_start_params(start_date_arg, end_date_arg, places_arg)
    
    # Prioritize function arg over CLI
    source = source_arg if source_arg else source_cli
    mode = mode_arg if mode_arg else mode_cli
    
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

        if progress_callback: progress_callback(msg)
        return

    print(f"対象会場: {list(places)}")
    print(f"取得元: {source}")
    print(f"モード: {mode}")

    if mode == "NAR":
        print("=== NAR (地方競馬) スクレイピング開始 ===")

        # 既存race_idの取得
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keiba_data.db")
        existing_race_ids = get_existing_race_ids(mode="NAR", db_path=db_path, csv_path=CSV_FILE_PATH_NAR)

        # 欠落レースの分析
        if existing_race_ids:
            missing_info = find_missing_races(start_date, end_date, existing_race_ids, mode="NAR")
            print(f"📊 データカバレッジ分析:")
            print(f"   対象期間: {missing_info['total_days']}日間（週末: {missing_info['weekend_days']}日）")
            print(f"   既存レース日: {missing_info['existing_race_dates']}日")
            print(f"   全体カバレッジ率: {missing_info['coverage_rate']:.1%}")

            # 年度別カバレッジを表示
            if missing_info['yearly_coverage']:
                print(f"\n   📅 年度別カバレッジ:")
                for year in sorted(missing_info['yearly_coverage'].keys()):
                    info = missing_info['yearly_coverage'][year]
                    status_icon = "✅" if info['coverage_rate'] >= 0.8 else ("⚠️" if info['coverage_rate'] > 0 else "❌")
                    print(f"      {status_icon} {year}年: {info['coverage_rate']:.1%} " +
                          f"({info['existing_race_dates']}/{info['weekend_days']}日)")

            # 完全に欠けている年度を警告
            if missing_info['missing_years']:
                print(f"\n   ❌ 警告: 以下の年度のデータが完全に欠けています:")
                for year in sorted(missing_info['missing_years']):
                    print(f"      • {year}年")
                print(f"   💡 これらの年度を含めてスクレイピングを実行してください")

            if missing_info['missing_weekend_dates']:
                print(f"\n   ⚠️ 欠落している可能性のある週末: {len(missing_info['missing_weekend_dates'])}日")
                # 最初の5日のみ表示
                for d in missing_info['missing_weekend_dates'][:5]:
                    print(f"      - {d}")
                if len(missing_info['missing_weekend_dates']) > 5:
                    print(f"      ... 他 {len(missing_info['missing_weekend_dates']) - 5}日")

            if progress_callback:
                progress_callback(f"既存データ: {len(existing_race_ids)}レース、スキップして欠落分のみ取得")

        # Callback wrapper to save to database_nar.csv
        def save_nar_callback(df_new):
            if df_new is None or df_new.empty: return
            csv_target = CSV_FILE_PATH_NAR
            if os.path.exists(csv_target):
                try:
                    existing = pd.read_csv(csv_target)
                    combined = pd.concat([existing, df_new], ignore_index=True)
                    # Deduplicate based on race_id and horse_number/horse_name
                    # Or just race_id + horse_number
                    if 'race_id' in combined.columns and '馬 番' in combined.columns:
                        combined = combined.drop_duplicates(subset=['race_id', '馬 番'], keep='last')
                    combined.to_csv(csv_target, index=False)
                    print(f"Saved {len(df_new)} rows to {csv_target} (Total {len(combined)})")
                except:
                    df_new.to_csv(csv_target, index=False)
            else:
                df_new.to_csv(csv_target, index=False)
                print(f"Created {csv_target} with {len(df_new)} rows.")

        # Loop years if range spans multiple years
        current_y = start_date.year
        end_y = end_date.year

        for y in range(current_y, end_y + 1):
             scrape_nar_year(
                 str(y),
                 start_date=start_date.date(),
                 end_date=end_date.date(),
                 save_callback=save_nar_callback,
                 existing_race_ids=existing_race_ids  # 既存IDを渡す
             )

        print("NAR Scraping Completed.")
        if progress_callback: progress_callback("NAR Scraping Completed.")
        return

    if source == 'jra':
        # Use JRA Scraper Bulk Logic
        print("=== JRA (中央競馬) スクレイピング開始 ===")

        # 既存race_idの取得
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keiba_data.db")
        existing_race_ids = get_existing_race_ids(mode="JRA", db_path=db_path, csv_path=CSV_FILE_PATH)

        # 欠落レースの分析
        if existing_race_ids:
            missing_info = find_missing_races(start_date, end_date, existing_race_ids, mode="JRA")
            print(f"📊 データカバレッジ分析:")
            print(f"   対象期間: {missing_info['total_days']}日間（週末: {missing_info['weekend_days']}日）")
            print(f"   既存レース日: {missing_info['existing_race_dates']}日")
            print(f"   全体カバレッジ率: {missing_info['coverage_rate']:.1%}")

            # 年度別カバレッジを表示
            if missing_info['yearly_coverage']:
                print(f"\n   📅 年度別カバレッジ:")
                for year in sorted(missing_info['yearly_coverage'].keys()):
                    info = missing_info['yearly_coverage'][year]
                    status_icon = "✅" if info['coverage_rate'] >= 0.8 else ("⚠️" if info['coverage_rate'] > 0 else "❌")
                    print(f"      {status_icon} {year}年: {info['coverage_rate']:.1%} " +
                          f"({info['existing_race_dates']}/{info['weekend_days']}日)")

            # 完全に欠けている年度を警告
            if missing_info['missing_years']:
                print(f"\n   ❌ 警告: 以下の年度のデータが完全に欠けています:")
                for year in sorted(missing_info['missing_years']):
                    print(f"      • {year}年")
                print(f"   💡 これらの年度を含めてスクレイピングを実行してください")

            if missing_info['missing_weekend_dates']:
                print(f"\n   ⚠️ 欠落している可能性のある週末: {len(missing_info['missing_weekend_dates'])}日")
                # 最初の5日のみ表示
                for d in missing_info['missing_weekend_dates'][:5]:
                    print(f"      - {d}")
                if len(missing_info['missing_weekend_dates']) > 5:
                    print(f"      ... 他 {len(missing_info['missing_weekend_dates']) - 5}日")

            if progress_callback:
                progress_callback(f"既存データ: {len(existing_race_ids)}レース、スキップして欠落分のみ取得")

        # We need to span years
        years_to_scan = range(start_date.year, end_date.year + 1)

        # Save Callback Wrapper
        def save_chunk_wrapper(df_chunk):
            # Same save logic as existing
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
             msg = f"  -> JRA Save: {len(df_chunk)} rows. Total: {len(combined_df)}"
             print(msg)
             if progress_callback: progress_callback(msg)

        for year in years_to_scan:
             print(f"Starting JRA Scrape for Year {year}...")
             if progress_callback: progress_callback(f"JRAスクレイピング開始: {year}年")

             # Adjust start/end for this year chunk if needed, but scrape_jra_year handles full date range filter
             scrape_jra_year(
                 str(year),
                 start_date=start_date.date(),
                 end_date=end_date.date(),
                 save_callback=save_chunk_wrapper,
                 existing_race_ids=existing_race_ids  # 既存IDを渡す
             )

        print(f"所要時間: {(time.time() - start_time)/60:.1f} 分")
        return

    # === Default: Netkeiba Logic ===

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
                                # Incremental Save Support (Local/Manual run)
                                # Note: This 'Netkeiba Logic' block calculates 'all_data' and saves at end.
                                # To support incremental save here, we would need a callback or logic.
                                # Check if 'save_nar_callback' is available in scope? No.
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
    parser.add_argument("--source", type=str, help="Source: netkeiba or jra")
    parser.add_argument("--mode", type=str, help="Mode: JRA or NAR")
    
    args, unknown = parser.parse_known_args()
    
    if args.today:
        mode = args.mode if args.mode else "JRA"
        scrape_todays_schedule(mode=mode)
    elif args.jra_url:
        print(f"Direct JRA Mode: {args.jra_url}")
        df = scrape_jra_race(args.jra_url)
        if df is not None and not df.empty:
            # Save logic (similar to main)
            # We can reuse the save logic but it's embedded in main()
            # Let's minimal-copy the save logic here for simplicity or refactor
            # For now, append to CSV directly
            CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "database.csv")
            
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
            CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "database.csv")
            
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
