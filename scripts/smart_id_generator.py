#!/usr/bin/env python3
"""
実用的な解決策: レースIDを生成して存在確認
JRAのレースID構造を利用して、可能性のあるIDを生成し、
実際にアクセスして存在するかチェックする
"""

import requests
from bs4 import BeautifulSoup
import time
from tqdm.auto import tqdm
import pandas as pd

class RaceIDGenerator:
    """レースIDを生成して検証するクラス"""
    
    def __init__(self, mode='JRA'):
        self.mode = mode
        self.session = requests.Session()
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # JRA競馬場コード
        self.jra_venues = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟', '05': '東京',
            '06': '中山', '07': '中京', '08': '京都', '09': '阪神', '10': '小倉'
        }
        
        # NAR競馬場コード(主要なもの)
        self.nar_venues = {
            '30': '門別', '35': '盛岡', '36': '水沢', '42': '浦和', '43': '船橋',
            '44': '大井', '45': '川崎', '46': '金沢', '47': '笠松', '48': '名古屋',
            '50': '園田', '51': '姫路', '54': '高知', '55': '佐賀'
        }
    
    def check_race_exists(self, race_id):
        """レースIDが存在するかチェック"""
        base_domain = "race.netkeiba.com" if self.mode == 'JRA' else "nar.netkeiba.com"
        
        # 結果ページと出馬表の両方を試す
        urls = [
            f"https://{base_domain}/race/result.html?race_id={race_id}",
            f"https://{base_domain}/race/shutuba.html?race_id={race_id}"
        ]
        
        for url in urls:
            try:
                time.sleep(0.1)  # レート制限対策
                resp = self.session.get(url, headers=self.headers, timeout=5)
                
                if resp.status_code == 200:
                    # ページが存在し、エラーページでないことを確認
                    if "レースが見つかりません" not in resp.text and "該当するレースがありません" not in resp.text:
                        return True
            except:
                continue
        
        return False
    
    def generate_and_validate_ids(self, year, month, max_races_per_day=12):
        """
        指定年月のレースIDを生成して検証
        
        レースID形式: YYYYPPKKDDRR
        - YYYY: 年
        - PP: 場所コード
        - KK: 回次 (01-06くらい)
        - DD: 日次 (01-12くらい)
        - RR: レース番号 (01-12)
        """
        print(f"  Generating IDs for {year}/{month:02}...")
        
        venues = self.jra_venues if self.mode == 'JRA' else self.nar_venues
        valid_ids = set()
        
        # 各競馬場について
        for venue_code in venues.keys():
            # 回次 (通常1-6回くらい)
            for kai in range(1, 7):
                # 日次 (通常1-12日くらい)
                for day in range(1, 13):
                    # レース番号 (通常1-12R)
                    for race_num in range(1, max_races_per_day + 1):
                        race_id = f"{year}{venue_code}{kai:02d}{day:02d}{race_num:02d}"
                        
                        # 存在チェック
                        if self.check_race_exists(race_id):
                            valid_ids.add(race_id)
                            print(f"    ✓ Found: {race_id}")
        
        return sorted(list(valid_ids))
    
    def fetch_ids_smart(self, start_year, end_year):
        """
        スマートにIDを取得
        カレンダーから開催日を取得し、その日のレースのみチェック
        """
        print(f"\n🚀 {self.mode} Race ID Fetching (Smart Method) ({start_year}-{end_year})...")
        
        all_ids = set()
        
        for year in range(start_year, end_year + 1):
            print(f"  📅 Processing {year}...")
            
            for month in range(1, 13):
                # カレンダーから開催日を取得
                dates = self._get_kaisai_dates(year, month)
                
                if not dates:
                    continue
                
                print(f"    {month:02}: {len(dates)} race days")
                
                # 各開催日について、可能性のあるレースIDを生成してチェック
                for date_str in tqdm(dates, desc=f"{year}/{month:02}", leave=False):
                    day_ids = self._generate_ids_for_date(date_str)
                    all_ids.update(day_ids)
        
        return sorted(list(all_ids))
    
    def _get_kaisai_dates(self, year, month):
        """カレンダーから開催日を取得"""
        base_domain = "race.netkeiba.com" if self.mode == 'JRA' else "nar.netkeiba.com"
        cal_url = f"https://{base_domain}/top/calendar.html?year={year}&month={month}"
        
        try:
            resp = self.session.get(cal_url, headers=self.headers, timeout=10)
            resp.encoding = 'EUC-JP'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            import re
            day_links = soup.select('a[href*="race_list.html?kaisai_date="]')
            
            dates = set()
            for link in day_links:
                href = link.get('href')
                m = re.search(r'kaisai_date=(\d{8})', href)
                if m:
                    dates.add(m.group(1))
            
            return sorted(list(dates))
        except:
            return []
    
    def _generate_ids_for_date(self, date_str):
        """
        特定の日付のレースIDを生成してチェック
        date_str: YYYYMMDD
        """
        year = date_str[:4]
        venues = self.jra_venues if self.mode == 'JRA' else self.nar_venues
        
        valid_ids = set()
        
        # 各競馬場について
        for venue_code in venues.keys():
            # 回次と日次の組み合わせを試す(範囲を絞る)
            for kai in range(1, 7):
                for day in range(1, 13):
                    # レース番号 1-12
                    for race_num in range(1, 13):
                        race_id = f"{year}{venue_code}{kai:02d}{day:02d}{race_num:02d}"
                        
                        # 簡易チェック: race_idが存在するか
                        if self.check_race_exists(race_id):
                            valid_ids.add(race_id)
        
        return valid_ids


def main():
    """テスト実行"""
    print("=" * 60)
    print("🔧 Smart Race ID Generator Test")
    print("=" * 60)
    
    # JRAの1ヶ月分だけテスト
    generator = RaceIDGenerator(mode='JRA')
    
    # 2025年1月の開催日を取得
    dates = generator._get_kaisai_dates(2025, 1)
    print(f"\n📅 Found {len(dates)} race days in 2025/1")
    
    if dates:
        # 最初の1日だけテスト
        print(f"\n🔍 Testing {dates[0]}...")
        test_ids = generator._generate_ids_for_date(dates[0])
        print(f"\n✅ Found {len(test_ids)} race IDs")
        
        for rid in sorted(test_ids)[:10]:
            print(f"  {rid}")


if __name__ == "__main__":
    main()
