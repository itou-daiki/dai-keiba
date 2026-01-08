#!/usr/bin/env python3
"""
別のアプローチ: 開催スケジュールページから直接レースIDを取得
"""

import requests
from bs4 import BeautifulSoup
import re
import time

def test_schedule_page():
    """重賞スケジュールページをテスト"""
    print("🔍 Testing Schedule Page\n")
    
    url = "https://race.netkeiba.com/top/schedule.html"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        print(f"✅ Status Code: {resp.status_code}")
        print(f"📄 Content Length: {len(resp.text)} chars\n")
        
        # race_idを含むリンクを探す
        all_links = soup.find_all('a', href=True)
        race_id_links = [link for link in all_links if 'race_id' in link.get('href', '')]
        
        print(f"🔗 Found {len(race_id_links)} links with race_id\n")
        
        race_ids = set()
        for link in race_id_links[:20]:
            href = link.get('href')
            text = link.get_text(strip=True)
            m = re.search(r'race_id=(\d+)', href)
            if m:
                rid = m.group(1)
                if len(rid) == 12:
                    race_ids.add(rid)
                    print(f"  {rid}: {text[:50]}")
        
        print(f"\n✅ Total unique race IDs: {len(race_ids)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_direct_race_result(race_id="202506010101"):
    """レース結果ページに直接アクセスしてHTMLを確認"""
    print(f"\n\n🔍 Testing Direct Race Result Page: {race_id}\n")
    
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        print(f"✅ Status Code: {resp.status_code}")
        
        # レース名を取得
        race_name = soup.find('h1', class_=re.compile('RaceName|race_name', re.I))
        if race_name:
            print(f"📋 Race Name: {race_name.get_text(strip=True)}")
        
        # 結果テーブルがあるか確認
        result_table = soup.find('table', class_=re.compile('Result|race_table', re.I))
        if result_table:
            print(f"✅ Result table found")
        else:
            print(f"⚠️  No result table found - might be a future race")
            
            # 出馬表を探す
            shutuba_table = soup.find('table', class_=re.compile('Shutuba|horse', re.I))
            if shutuba_table:
                print(f"✅ Shutuba (entry) table found")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_monthly_race_list(year=2025, month=1):
    """月間レース一覧から全レースIDを取得する別の方法を試す"""
    print(f"\n\n🔍 Testing Monthly Approach: {year}/{month}\n")
    
    # 各競馬場のコードを試す
    # JRA競馬場コード: 01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
    venues = {
        '01': '札幌', '02': '函館', '03': '福島', '04': '新潟', '05': '東京',
        '06': '中山', '07': '中京', '08': '京都', '09': '阪神', '10': '小倉'
    }
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    all_race_ids = set()
    
    # 1月の各日を試す(1-31)
    for day in range(1, 32):
        date_str = f"{year}{month:02d}{day:02d}"
        
        # 開催があるか確認するため、race_listページを試す
        list_url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}"
        
        try:
            time.sleep(0.3)
            resp = session.get(list_url, headers=headers, timeout=10)
            resp.encoding = 'EUC-JP'
            
            # ページタイトルやコンテンツで開催があるか確認
            if "開催なし" in resp.text or "レースがありません" in resp.text:
                continue
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 別のアプローチ: レース名を含むテキストからrace_idを推測
            # race_idの形式: YYYYPPKKDDRR
            # YYYY=年, PP=場所, KK=回次, DD=日次, RR=レース番号
            
            # まず、ページ内の全テキストからrace_idパターンを探す
            text_content = resp.text
            race_id_pattern = re.findall(r'\b(20\d{10})\b', text_content)
            
            for rid in race_id_pattern:
                if len(rid) == 12:
                    all_race_ids.add(rid)
            
        except:
            continue
    
    print(f"✅ Found {len(all_race_ids)} race IDs for {year}/{month}")
    if all_race_ids:
        print("\nSample IDs:")
        for rid in sorted(list(all_race_ids))[:10]:
            print(f"  {rid}")
    
    return all_race_ids


if __name__ == "__main__":
    test_schedule_page()
    test_direct_race_result("202506010101")
    race_ids = test_monthly_race_list(2025, 1)
