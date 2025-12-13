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
# 2. 既存データ読み込みと開始地点の特定
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
def main(start_date_arg=None, end_date_arg=None, places_arg=None):
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

    if start_date > end_date:
        print("指定期間が不正、または最新データまで取得済みです。")
        return

    print(f"取得対象期間: {start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}")
    print(f"対象会場: {list(places)}")

    all_data = []
    
    # 年ごとのループ
    years_to_scan = range(start_date.year, end_date.year + 1)

    # 探索ロジック
    # netkeibaのrace_id構造: YYYY(4) + 場所(2) + 回(2) + 日(2) + R(2)
    # これを全探索するのは非効率だが、開催日が不規則なので
    # 「開催されているかどうか」を効率よく探る必要がある。
    # ここではユーザー提供のループ構造をベースにしつつ、日付チェックを入れる。

    # places = range(1, 11) # Argument used instead
    kais = range(1, 7)    # 開催回
    days = range(1, 13)   # 開催日数
    
    # 既に取得済みのrace_idを除外するためにセットを用意してもいいが
    # 日付ベースでフィルタリングしているので、再取得は基本的に発生しないはず。
    # ただし同じ日に複数レースがあるので、既存CSVのIDチェックも念の為入れても良い。
    existing_ids = set()
    if os.path.exists(CSV_FILE_PATH):
        try:
            df_ex = pd.read_csv(CSV_FILE_PATH)
            if 'race_id' in df_ex.columns:
                existing_ids = set(df_ex['race_id'].astype(str))
        except:
            pass

    for year in years_to_scan:
        # start_dateとtodayの範囲外の年はスキップ（years_to_scanで制限済みだが念の為）
        
        for place in places:
            for kai in kais:
                for day in days:
                    # まず1Rをチェックして、そのレースの日付を確認する
                    check_race_id = f"{year}{place:02}{kai:02}{day:02}01"
                    
                    # 既に持っているデータならスキップするか？
                    # -> 1RのIDを持っているなら、その日は取得済みとみなして良いかもしれない
                    # しかし、12Rまで全部取れているか保証はないので、
                    # 「開催日」を取得して、その日が start_date 以降かどうかを確認するのが確実。
                    
                    if check_race_id in existing_ids:
                        # 1Rが既にあるなら、その日の存在確認は省略して、続き(2R以降)がないかチェックすべきか？
                        # シンプルにするため、チェックは飛ばすが、
                        # リトライ性を持たせるなら「IDがないレースだけ叩く」のがベスト。
                        # ここでは「日付判定」のために一度アクセスする必要があるかもしれないが、
                        # IDでアクセスして日付を取る＝アクセス発生。
                        # なので、1RがCSVにある場合、その行の日付を見て対象外ならスキップするロジックが可能。
                        pass

                    # サーバー負荷軽減
                    time.sleep(1)
                    
                    print(f"Search: {check_race_id} ... ", end="")
                    first_race_df = scrape_race_data(check_race_id)
                    
                    if first_race_df is None:
                        # 1Rがない -> この開催日はない、または終了
                        print("Miss")
                        if day == 1:
                            # 1日目がないならこの回(Kai)は終了の可能性が高い
                            # ただし、場所ごとの開催スケジュールは複雑なので、
                            # breakして次のKaiへ行くのは安全
                            break 
                        else:
                            # 途中まであって次がないなら、この回の日程終了
                            break
                    else:
                        # 開催あり。日付をチェック
                        race_date_str = first_race_df.iloc[0]["日付"] # "2024年1月5日"
                        try:
                            race_date = datetime.strptime(race_date_str, '%Y年%m月%d日')
                        except:
                            race_date = datetime(year, 1, 1) # Fallback

                        # 対象期間チェック
                        if race_date < start_date:
                            print(f"Skip (Old Data: {race_date_str})")
                            # この日が古いなら、次以降のDayは新しい可能性があるか？
                            # 通常、Dayが進めば日付も進むので、
                            # もし start_date より前なら、このデータは不要だが、
                            # 続きのDayには新しいデータが来るかもしれないので continue
                            continue
                        
                        if race_date > end_date:
                            print(f"Skip (Future/Outside Range: {race_date_str})")
                            # 未来ならこれ以上探索不要だが、並行開催の他場があるかもなので
                            # このループ(Day)はbreakでいいかも
                            break

                        print(f"Hit ({race_date_str}) -> 取得開始")
                        
                        # 1Rを保存 (重複チェック)
                        if check_race_id not in existing_ids:
                             all_data.append(first_race_df)
                        
                        # 2R〜12R
                        for r in range(2, 13):
                            race_id = f"{year}{place:02}{kai:02}{day:02}{r:02}"
                            if race_id in existing_ids:
                                continue
                                
                            time.sleep(1) # Wait
                            df = scrape_race_data(race_id)
                            if df is not None:
                                all_data.append(df)
                                print(f".", end="", flush=True) # Progress dot
                            else:
                                break # その日のレース終了
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
    main()
