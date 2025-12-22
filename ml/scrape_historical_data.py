"""
過去3年分の履歴データスクレイピング

目的: JRAデータを656件→5000件以上に増やす
期間: 2023年1月1日 - 2025年12月31日
データソース: netkeiba.com (JRA競馬)

使用方法:
    python ml/scrape_historical_data.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--dry-run]

    --start: 開始日（デフォルト: 2023-01-01）
    --end: 終了日（デフォルト: 今日）
    --dry-run: テストモード（実際のスクレイピングなし）
"""

import os
import sys
from datetime import datetime, timedelta
import logging
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper.auto_scraper import scrape_race_data

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml/historical_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")
TARGET_RECORDS = 5000  # 目標レコード数


def get_existing_race_ids():
    """既存のrace_idを取得して重複を避ける"""
    if not os.path.exists(CSV_FILE_PATH):
        return set()

    try:
        df = pd.read_csv(CSV_FILE_PATH)
        if 'race_id' in df.columns:
            return set(df['race_id'].astype(str))
    except Exception as e:
        logger.warning(f"Failed to load existing race IDs: {e}")

    return set()


def get_current_record_count():
    """現在のレコード数を取得"""
    if not os.path.exists(CSV_FILE_PATH):
        return 0

    try:
        df = pd.read_csv(CSV_FILE_PATH)
        return len(df)
    except:
        return 0


def save_race_data(df_new):
    """レースデータを保存（追記モード）"""
    if df_new is None or df_new.empty:
        return

    if os.path.exists(CSV_FILE_PATH):
        try:
            existing_df = pd.read_csv(CSV_FILE_PATH)
            combined_df = pd.concat([existing_df, df_new], ignore_index=True)
        except Exception as e:
            logger.warning(f"Failed to read existing CSV: {e}")
            combined_df = df_new
    else:
        combined_df = df_new

    # 重複排除 (race_id + 馬名)
    subset_cols = ['race_id', '馬名']
    subset_cols = [c for c in subset_cols if c in combined_df.columns]

    if subset_cols:
        before_count = len(combined_df)
        combined_df.drop_duplicates(subset=subset_cols, keep='last', inplace=True)
        after_count = len(combined_df)
        if before_count != after_count:
            logger.info(f"  Removed {before_count - after_count} duplicates")

    # 日付ソート
    try:
        combined_df['date_obj'] = pd.to_datetime(combined_df['日付'], format='%Y年%m月%d日', errors='coerce')
        combined_df = combined_df.sort_values(['date_obj', 'race_id'])
        combined_df = combined_df.drop(columns=['date_obj'])
    except:
        pass

    combined_df.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
    logger.info(f"  Saved {len(df_new)} new rows. Total: {len(combined_df)}")

    return len(combined_df)


def scrape_historical_jra_data(start_date, end_date, dry_run=False):
    """
    JRAの履歴データをスクレイピング

    Args:
        start_date: 開始日 (datetime)
        end_date: 終了日 (datetime)
        dry_run: テストモード（実際のスクレイピングなし）

    戦略:
        - JRAの10競馬場を全てカバー
        - 各年ごとに開催回・日数を探索
        - 既存データはスキップ
        - 目標5000レコードに到達したら完了
    """
    logger.info("=" * 60)
    logger.info("JRA Historical Data Scraping Started")
    logger.info(f"Target Period: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Target Records: {TARGET_RECORDS}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info("=" * 60)

    # 現在のレコード数
    initial_count = get_current_record_count()
    logger.info(f"Current records: {initial_count}")

    if initial_count >= TARGET_RECORDS:
        logger.info(f"✅ Already reached target ({initial_count} >= {TARGET_RECORDS})")
        return

    # 既存のrace_idを取得
    existing_ids = get_existing_race_ids()
    logger.info(f"Existing race IDs: {len(existing_ids)}")

    # JRA 10競馬場
    # Place codes: 01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京,
    #              06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
    places = range(1, 11)

    # 探索範囲
    years = range(start_date.year, end_date.year + 1)
    kais = range(1, 7)      # 開催回 (通常1-6回)
    days = range(1, 13)     # 開催日数 (通常1-12日)
    races = range(1, 13)    # レース番号 (1-12R)

    total_scraped = 0
    total_skipped = 0
    total_errors = 0

    import time

    for year in years:
        logger.info(f"\n{'='*60}")
        logger.info(f"Year: {year}")
        logger.info(f"{'='*60}")

        for place in places:
            place_name_map = {
                1: "札幌", 2: "函館", 3: "福島", 4: "新潟", 5: "東京",
                6: "中山", 7: "中京", 8: "京都", 9: "阪神", 10: "小倉"
            }
            place_name = place_name_map.get(place, f"Place{place}")

            logger.info(f"\n{place_name} ({place:02})")

            for kai in kais:
                for day in days:
                    # 1Rをチェックして開催日が存在するか確認
                    check_race_id = f"{year}{place:02}{kai:02}{day:02}01"

                    # 既存データチェック
                    if check_race_id in existing_ids:
                        total_skipped += 1
                        continue

                    # Dry runモード
                    if dry_run:
                        logger.info(f"  [DRY RUN] Would scrape: {check_race_id}")
                        continue

                    logger.info(f"  Checking: {check_race_id} ({year}/{kai}回{day}日) ... ", end="")

                    # サーバー負荷軽減 (0.5秒待機)
                    time.sleep(0.5)

                    try:
                        # 1Rを取得
                        first_race_df = scrape_race_data(check_race_id, mode="JRA")

                        if first_race_df is None or first_race_df.empty:
                            logger.info("Miss")
                            # 1Rがない = この開催日はない
                            if day == 1:
                                # 1日目がない = この開催回は存在しない
                                break
                            else:
                                # 途中の日がない = この回は終了
                                break

                        # 開催日が存在する
                        race_date_str = first_race_df.iloc[0]["日付"]

                        try:
                            race_date = datetime.strptime(race_date_str, '%Y年%m月%d日')
                        except:
                            race_date = datetime(year, 1, 1)

                        # 対象期間チェック
                        if race_date < start_date:
                            logger.info(f"Skip (Old: {race_date_str})")
                            continue

                        if race_date > end_date:
                            logger.info(f"Skip (Future: {race_date_str})")
                            break

                        logger.info(f"Hit! ({race_date_str})")

                        # 1Rを保存
                        total_count = save_race_data(first_race_df)
                        total_scraped += len(first_race_df)
                        existing_ids.add(check_race_id)

                        # 2R-12Rを取得
                        for r in range(2, 13):
                            race_id = f"{year}{place:02}{kai:02}{day:02}{r:02}"

                            if race_id in existing_ids:
                                total_skipped += 1
                                continue

                            time.sleep(0.5)

                            try:
                                df = scrape_race_data(race_id, mode="JRA")
                                if df is not None and not df.empty:
                                    total_count = save_race_data(df)
                                    total_scraped += len(df)
                                    existing_ids.add(race_id)
                                    logger.info(f"    {r}R OK", end=" ")
                                else:
                                    # このレースはない（開催終了）
                                    break
                            except Exception as e:
                                logger.error(f"    {r}R Error: {e}")
                                total_errors += 1
                                break

                        logger.info("")

                        # 目標達成チェック
                        if total_count >= TARGET_RECORDS:
                            logger.info(f"\n🎉 Target reached! {total_count} >= {TARGET_RECORDS}")
                            logger.info(f"Total scraped: {total_scraped} records")
                            logger.info(f"Skipped: {total_skipped}, Errors: {total_errors}")
                            return

                        # 進捗表示
                        if total_scraped > 0 and total_scraped % 100 == 0:
                            logger.info(f"\n📊 Progress: {total_count}/{TARGET_RECORDS} records ({total_count/TARGET_RECORDS*100:.1f}%)")

                    except Exception as e:
                        logger.error(f"Error: {e}")
                        total_errors += 1

    # 最終結果
    final_count = get_current_record_count()
    logger.info("\n" + "=" * 60)
    logger.info("Scraping Completed")
    logger.info(f"Initial records: {initial_count}")
    logger.info(f"Final records: {final_count}")
    logger.info(f"New records: {final_count - initial_count}")
    logger.info(f"Total scraped: {total_scraped}")
    logger.info(f"Skipped: {total_skipped}")
    logger.info(f"Errors: {total_errors}")
    logger.info(f"Target: {TARGET_RECORDS}")

    if final_count >= TARGET_RECORDS:
        logger.info(f"✅ Target reached!")
    else:
        logger.warning(f"⚠️ Target not reached. Need {TARGET_RECORDS - final_count} more records.")

    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='JRA過去3年分データスクレイピング')
    parser.add_argument('--start', type=str, default='2023-01-01',
                       help='開始日 (YYYY-MM-DD, デフォルト: 2023-01-01)')
    parser.add_argument('--end', type=str, default=None,
                       help='終了日 (YYYY-MM-DD, デフォルト: 今日)')
    parser.add_argument('--dry-run', action='store_true',
                       help='テストモード（実際のスクレイピングなし）')

    args = parser.parse_args()

    # Parse dates
    try:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
    except ValueError:
        logger.error(f"Invalid start date format: {args.start}. Use YYYY-MM-DD")
        sys.exit(1)

    if args.end:
        try:
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
        except ValueError:
            logger.error(f"Invalid end date format: {args.end}. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        end_date = datetime.now()

    # Validate date range
    if start_date > end_date:
        logger.error(f"Start date ({start_date}) is after end date ({end_date})")
        sys.exit(1)

    # Run scraping
    scrape_historical_jra_data(start_date, end_date, dry_run=args.dry_run)

    print("\n✅ Historical data scraping script completed.")
    print(f"📁 Data saved to: {CSV_FILE_PATH}")
    print(f"📋 Log saved to: ml/historical_scraping.log")
