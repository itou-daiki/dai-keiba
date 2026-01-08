#!/usr/bin/env python3
"""
ID Fetcher デバッグスクリプト
Colab_ID_Fetcher.ipynb の問題を診断します
"""

import requests
from bs4 import BeautifulSoup
import re
import time

def test_jra_calendar(year=2025, month=1):
    """JRAカレンダーページのテスト"""
    print(f"\n🔍 Testing JRA Calendar: {year}/{month}")
    
    base_domain = "race.netkeiba.com"
    cal_url = f"https://{base_domain}/top/calendar.html?year={year}&month={month}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(cal_url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        print(f"  ✅ Status Code: {resp.status_code}")
        print(f"  📄 Content Length: {len(resp.text)} chars")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # カレンダーリンクを探す
        day_links = soup.select('a[href*="race_list.html?kaisai_date="]')
        print(f"  🔗 Found {len(day_links)} day links")
        
        dates = []
        for link in day_links[:5]:  # 最初の5つだけ表示
            href = link.get('href')
            m = re.search(r'kaisai_date=(\d{8})', href)
            if m:
                date_str = m.group(1)
                dates.append(date_str)
                print(f"    - {date_str}: {href}")
        
        if not dates:
            print("  ⚠️  No dates found! Checking HTML structure...")
            # HTMLの一部を表示
            print("\n  📋 Sample HTML (first 1000 chars):")
            print(resp.text[:1000])
            
            # 全てのリンクを確認
            all_links = soup.find_all('a', href=True)
            print(f"\n  🔗 Total links found: {len(all_links)}")
            if all_links:
                print("  Sample links:")
                for link in all_links[:10]:
                    print(f"    - {link.get('href')}")
        
        return dates
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []


def test_race_list(date_str="20250105"):
    """レースリストページのテスト"""
    print(f"\n🔍 Testing JRA Race List: {date_str}")
    
    base_domain = "race.netkeiba.com"
    list_url = f"https://{base_domain}/top/race_list.html?kaisai_date={date_str}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(list_url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        print(f"  ✅ Status Code: {resp.status_code}")
        print(f"  📄 Content Length: {len(resp.text)} chars")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # レースIDリンクを探す
        race_links = soup.select('a[href*="race_id="]')
        print(f"  🔗 Found {len(race_links)} race links")
        
        race_ids = set()
        for link in race_links[:10]:  # 最初の10個だけ表示
            href = link.get('href')
            m = re.search(r'race_id=(\d+)', href)
            if m:
                race_id = m.group(1)
                if len(race_id) == 12:
                    race_ids.add(race_id)
                    print(f"    - {race_id}: {href}")
        
        if not race_ids:
            print("  ⚠️  No race IDs found! Checking HTML structure...")
            print("\n  📋 Sample HTML (first 1000 chars):")
            print(resp.text[:1000])
            
            # 全てのリンクを確認
            all_links = soup.find_all('a', href=True)
            print(f"\n  🔗 Total links found: {len(all_links)}")
            if all_links:
                print("  Sample links:")
                for link in all_links[:10]:
                    print(f"    - {link.get('href')}")
        
        return list(race_ids)
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []


def test_nar_calendar(year=2025, month=12):
    """NARカレンダーページのテスト"""
    print(f"\n🔍 Testing NAR Calendar: {year}/{month}")
    
    base_domain = "nar.netkeiba.com"
    cal_url = f"https://{base_domain}/top/calendar.html?year={year}&month={month}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(cal_url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        print(f"  ✅ Status Code: {resp.status_code}")
        print(f"  📄 Content Length: {len(resp.text)} chars")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # カレンダーリンクを探す
        day_links = soup.select('a[href*="race_list.html?kaisai_date="]')
        print(f"  🔗 Found {len(day_links)} day links")
        
        dates = []
        for link in day_links[:5]:  # 最初の5つだけ表示
            href = link.get('href')
            m = re.search(r'kaisai_date=(\d{8})', href)
            if m:
                date_str = m.group(1)
                dates.append(date_str)
                print(f"    - {date_str}: {href}")
        
        if not dates:
            print("  ⚠️  No dates found! Checking HTML structure...")
            print("\n  📋 Sample HTML (first 1000 chars):")
            print(resp.text[:1000])
        
        return dates
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 ID Fetcher Diagnostic Tool")
    print("=" * 60)
    
    # JRAテスト
    print("\n" + "=" * 60)
    print("📊 JRA Testing")
    print("=" * 60)
    
    jra_dates = test_jra_calendar(2025, 1)
    if jra_dates:
        print(f"\n✅ Found {len(jra_dates)} dates in JRA calendar")
        # 最初の日付でレースリストをテスト
        test_race_list(jra_dates[0])
    else:
        print("\n❌ No dates found in JRA calendar - HTML structure may have changed")
    
    # NARテスト
    print("\n" + "=" * 60)
    print("📊 NAR Testing")
    print("=" * 60)
    
    nar_dates = test_nar_calendar(2025, 12)
    if nar_dates:
        print(f"\n✅ Found {len(nar_dates)} dates in NAR calendar")
    else:
        print("\n❌ No dates found in NAR calendar - HTML structure may have changed")
    
    print("\n" + "=" * 60)
    print("🏁 Diagnostic Complete")
    print("=" * 60)
