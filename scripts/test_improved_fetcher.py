#!/usr/bin/env python3
"""
レースIDを生成してバリデーションする方法
カレンダーページから開催日を取得し、その日のレースIDを推測して確認
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from tqdm.auto import tqdm

def get_kaisai_dates_from_calendar(year, month, mode='JRA'):
    """カレンダーページから開催日を取得"""
    base_domain = "race.netkeiba.com" if mode == 'JRA' else "nar.netkeiba.com"
    cal_url = f"https://{base_domain}/top/calendar.html?year={year}&month={month}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(cal_url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # カレンダーリンクを探す
        day_links = soup.select('a[href*="race_list.html?kaisai_date="]')
        
        dates = set()
        for link in day_links:
            href = link.get('href')
            m = re.search(r'kaisai_date=(\d{8})', href)
            if m:
                dates.add(m.group(1))
        
        return sorted(list(dates))
        
    except Exception as e:
        print(f"  Error fetching calendar {year}/{month}: {e}")
        return []


def extract_race_ids_from_page(date_str, mode='JRA'):
    """
    開催日のページから実際のレースIDを抽出
    ページのHTMLソース内に埋め込まれているrace_idを全て探す
    """
    base_domain = "race.netkeiba.com" if mode == 'JRA' else "nar.netkeiba.com"
    list_url = f"https://{base_domain}/top/race_list.html?kaisai_date={date_str}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        time.sleep(0.3)
        resp = session.get(list_url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        
        # HTMLソース全体から12桁の数字パターンを探す
        # race_idの形式: YYYYPPKKDDRR (年4桁 + 8桁)
        # 年の部分で絞り込む
        year = date_str[:4]
        pattern = rf'\b({year}\d{{8}})\b'
        
        race_ids = set()
        matches = re.findall(pattern, resp.text)
        
        for match in matches:
            if len(match) == 12:
                # さらにフィルタリング: 場所コードが妥当か確認
                place_code = match[4:6]
                # JRA: 01-10, NAR: 30-65くらい
                if mode == 'JRA':
                    if place_code in [f"{i:02d}" for i in range(1, 11)]:
                        race_ids.add(match)
                else:
                    if int(place_code) >= 30:
                        race_ids.add(match)
        
        return sorted(list(race_ids))
        
    except Exception as e:
        return []


def fetch_race_ids_improved(mode='JRA', start_year=2025, end_year=2026):
    """改良版のレースID取得"""
    print(f"\n🚀 {mode} Race ID Fetching ({start_year}-{end_year})...")
    
    all_ids = set()
    
    for year in range(start_year, end_year + 1):
        print(f"  📅 Processing {year}...")
        
        for month in range(1, 13):
            # カレンダーから開催日を取得
            dates = get_kaisai_dates_from_calendar(year, month, mode)
            
            if not dates:
                continue
            
            # 各開催日からレースIDを抽出
            for date_str in tqdm(dates, desc=f"{year}/{month:02}", leave=False):
                race_ids = extract_race_ids_from_page(date_str, mode)
                all_ids.update(race_ids)
    
    print(f"\n✅ Total IDs collected: {len(all_ids)}")
    return sorted(list(all_ids))


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Improved ID Fetcher Test")
    print("=" * 60)
    
    # テスト: 2025年1月のみ
    print("\n📊 Testing JRA (2025/1 only)...")
    jra_ids = fetch_race_ids_improved(mode='JRA', start_year=2025, end_year=2025)
    
    if jra_ids:
        print(f"\n✅ Sample JRA IDs (first 20):")
        for rid in jra_ids[:20]:
            print(f"  {rid}")
    else:
        print("\n❌ No JRA IDs found")
    
    print("\n" + "=" * 60)
    print("\n📊 Testing NAR (2025/12 only)...")
    
    # NAR: 2025年12月のみテスト
    nar_dates = get_kaisai_dates_from_calendar(2025, 12, 'NAR')
    print(f"Found {len(nar_dates)} NAR dates in 2025/12")
    
    if nar_dates:
        print("\nTesting first NAR date...")
        nar_ids = extract_race_ids_from_page(nar_dates[0], 'NAR')
        print(f"Found {len(nar_ids)} NAR IDs on {nar_dates[0]}")
        if nar_ids:
            for rid in nar_ids[:10]:
                print(f"  {rid}")
