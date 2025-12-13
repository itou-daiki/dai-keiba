import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import time
import re
from datetime import datetime, timedelta, date
import os
import sys

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

            # 列追加
            df.insert(0, "日付", date_text)
            df.insert(1, "会場", venue_text)
            df.insert(2, "レース番号", race_num_text)
            df.insert(3, "レース名", race_name_text)
            df.insert(4, "重賞", grade_text)
            df["race_id"] = race_id # IDも保存 (末尾に追加されることが多いが明示的に)
            
            # 不要な列が含まれることがあるので整理しても良いが、
            # ユーザー要望は「蓄積」なので、基本はそのまま保持する
            
            return df
        else:
            return None

    except Exception as e:
        print(f"Error scraping {race_id}: {e}")
        return None

# ==========================================
# 2. Upcoming/Today's Race Scraping (JSON for Web App)
# ==========================================
def scrape_todays_schedule():
    """
    Scrapes today's race list and odds from race.netkeiba.com
    Saves to 'todays_data.json' for the static web app.
    """
    import json
    
    # Target date: Today
    today = datetime.now()
    kaisai_date = today.strftime("%Y%m%d")
    
    # Use race_list_sub.html to get the actual content as race_list.html loads via AJAX
    url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" 
    }
    
    print(f"Fetching race list for {kaisai_date}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        race_list = []
        
        # Selectors based on script.js logic
        # Changed to .RaceList_DataItem as per inspection of race_list_sub.html
        items = soup.select('.RaceList_DataList .RaceList_DataItem')
        if not items:
            items = soup.select('.RaceList_Box .RaceList_DataItem')
            
        print(f"Found {len(items)} races.")
        
        for item in items:
            link_elem = item.find('a')
            if not link_elem: continue
            
            href = link_elem.get('href', '')
            # Extract race_id
            # href might be "../race/shutuba.html?race_id=2025..."
            race_id_match = re.search(r'race_id=(\d+)', href)
            if not race_id_match: continue
            
            race_id = race_id_match.group(1)
            
            # Metadata
            # Metadata
            venue_elem = item.select_one('.JyoName')
            race_num_elem = item.select_one('.Race_Num')
            race_name_elem = item.select_one('.RaceName') or item.select_one('.ItemTitle')
            
            venue = venue_elem.text.strip() if venue_elem else ""
            num = race_num_elem.text.strip() if race_num_elem else ""
            name = race_name_elem.text.strip() if race_name_elem else ""
            
            # If venue is missing, try to derive from race_id
            if not venue and len(race_id) >= 6:
                place_code = race_id[4:6]
                venue_map = {
                    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
                    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"
                }
                venue = venue_map.get(place_code, "")
                
            # Clean up num (remove newlines/spaces)
            num = re.sub(r'\s+', '', num)
            
            # Fetch Odds for this race
            odds_data = scrape_odds_for_race(race_id)
            
            race_info = {
                "id": race_id,
                "venue": venue,
                "number": num,
                "name": name,
                "horses": odds_data
            }
            race_list.append(race_info)
            print(f"  + {venue} {num} {name} ({len(odds_data)} horses)")
            time.sleep(1) # Be gentle
            
        # Save to JSON
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "todays_data.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({"date": kaisai_date, "races": race_list}, f, ensure_ascii=False, indent=2)
            
        print(f"Saved {len(race_list)} races to {output_path}")
        return True, f"{len(race_list)} races saved."
        
    except Exception as e:
        print(f"Error scraping schedule: {e}")
        return False, str(e)

def scrape_odds_for_race(race_id):
    """
    Fetches odds for a specific race_id
    Returns list of {number, odds}
    """
    # Use odds_get_form.html for single/place odds (type=b1)
    url = f"https://race.netkeiba.com/odds/odds_get_form.html?type=b1&race_id={race_id}"
    headers = { "User-Agent": "Mozilla/5.0" }
    
    horses = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Selector: #odds_tan_block .RaceOdds_HorseList_Table tbody tr (Specific to Win odds)
        rows = soup.select('#odds_tan_block .RaceOdds_HorseList_Table tbody tr')
        if not rows:
             # Fallback to generic if id not found (though unlikely for b1 type)
             rows = soup.select('.RaceOdds_HorseList_Table tbody tr')
        
        # Falls back to old selector if new one fails (for compatibility)
        if not rows:
            url_alt = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
            try:
                resp_alt = requests.get(url_alt, headers=headers, timeout=10)
                resp_alt.encoding = resp_alt.apparent_encoding
                soup_alt = BeautifulSoup(resp_alt.text, 'html.parser')
                rows = soup_alt.select('.Shutuba_Table tbody tr') or soup_alt.select('.RaceTable01 tr[class^="HorseList"]')
            except:
                pass

        for row in rows:
            # Check if it's a valid row (ignore headers)
            # Valid rows usually have numeric cells
            
            # Try to find Number and Odds
            # Strategy 1: RaceOdds_HorseList_Table (Col 2 and 6)
            if 'RaceOdds_HorseList_Table' in str(row.find_parent('table')):
                num_elem = row.select_one('td:nth-child(2)')
                odds_elem = row.select_one('td:nth-child(6)')
            else:
                # Strategy 2: Shutuba_Table / RaceTable01
                num_elem = row.select_one('.Umaban') or row.select_one('td:nth-child(2)')
                odds_elem = row.select_one('.Odds_Tan') or row.select_one('td:nth-child(14)')
            
            if num_elem and odds_elem:
                try:
                    num_txt = num_elem.text.strip()
                    if not num_txt.isdigit(): continue
                    num = int(num_txt)
                    
                    odds_txt = odds_elem.text.strip()
                    if '---' in odds_txt:
                        odds = 0.0
                    else:
                        odds = float(odds_txt)
                        
                    horses.append({"number": num, "odds": odds})
                except:
                    continue
                    
    except Exception as e:
        print(f"Error scraping odds for {race_id}: {e}")
        
    return horses

# ==========================================
# 3. 既存データ読み込みと開始地点の特定
# ==========================================
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
    # Also parse arguments for main() to avoid conflicts if they are passed
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--places", type=str, help="Target places")
    
    args, unknown = parser.parse_known_args()
    
    if args.today:
        scrape_todays_schedule()
    else:
        # Pass unknown arguments or parse them again inside main/get_start_params 
        # but get_start_params parses sys.argv again or uses its own parser.
        # Since get_start_params uses parse_known_args, it should be fine.
        main()
