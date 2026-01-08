#!/usr/bin/env python3
"""
修正版のID取得ロジックをテスト
race_list_sub.htmlを使用
"""

import requests
from bs4 import BeautifulSoup
import re

def test_race_list_sub(date_str="20250105", mode='JRA'):
    """race_list_sub.htmlからレースIDを取得"""
    print(f"🔍 Testing race_list_sub.html for {mode} on {date_str}\n")
    
    base_domain = "race.netkeiba.com" if mode == 'JRA' else "nar.netkeiba.com"
    sub_url = f"https://{base_domain}/top/race_list_sub.html?kaisai_date={date_str}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(sub_url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        
        print(f"✅ Status Code: {resp.status_code}")
        print(f"📄 Content Length: {len(resp.text)} chars\n")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # race_idを含むリンクを探す
        race_links = soup.find_all('a', href=re.compile(r'race_id=\d+'))
        
        print(f"🔗 Found {len(race_links)} race links\n")
        
        race_ids = set()
        for link in race_links[:20]:  # 最初の20個を表示
            href = link.get('href')
            text = link.get_text(strip=True)
            m = re.search(r'race_id=(\d+)', href)
            if m:
                rid = m.group(1)
                if len(rid) == 12:
                    race_ids.add(rid)
                    print(f"  {rid}: {text[:50]}")
        
        print(f"\n✅ Total unique race IDs: {len(race_ids)}")
        
        if not race_ids:
            print("\n⚠️  No race IDs found! Showing HTML sample:")
            print(resp.text[:1000])
        
        return sorted(list(race_ids))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Testing race_list_sub.html Endpoint")
    print("=" * 60)
    
    # JRAテスト
    print("\n📊 JRA Test (2025-01-05)")
    print("=" * 60)
    jra_ids = test_race_list_sub("20250105", "JRA")
    
    # NARテスト
    print("\n" + "=" * 60)
    print("📊 NAR Test (2025-01-05)")
    print("=" * 60)
    nar_ids = test_race_list_sub("20250105", "NAR")
    
    # 別の日もテスト
    print("\n" + "=" * 60)
    print("📊 JRA Test (2025-01-06)")
    print("=" * 60)
    jra_ids_2 = test_race_list_sub("20250106", "JRA")
    
    print("\n" + "=" * 60)
    print("🏁 Test Complete")
    print("=" * 60)
    print(f"JRA 2025-01-05: {len(jra_ids)} IDs")
    print(f"NAR 2025-01-05: {len(nar_ids)} IDs")
    print(f"JRA 2025-01-06: {len(jra_ids_2)} IDs")
