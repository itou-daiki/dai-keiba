#!/usr/bin/env python3
"""
NAR 2022-2026年のレースIDを徹底調査
全競馬場、全月を体系的に探索
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime

# NAR競馬場コード
venues = {
    '30': '門別', '35': '盛岡', '36': '水沢', '42': '浦和',
    '43': '船橋', '44': '大井', '45': '川崎', '46': '金沢',
    '47': '笠松', '48': '名古屋', '50': '園田', '51': '姫路',
    '54': '高知', '55': '佐賀'
}

def check_race_exists(race_id):
    """レースIDが有効か確認"""
    url = f'https://nar.netkeiba.com/race/result.html?race_id={race_id}'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        tables = soup.find_all('table')
        for table in tables:
            if '着順' in table.text and '馬名' in table.text:
                rows = table.find_all('tr')
                if len(rows) > 2:  # ヘッダー+データ
                    return True, len(rows) - 1
        return False, 0
    except:
        return False, 0

print("🔍 NAR 2022-2026年 レースID徹底調査\n")
print(f"{'='*80}\n")

found_races = {}

for year in [2022, 2023, 2024, 2025, 2026]:
    print(f"📅 {year}年を調査中...")
    year_prefix = str(year)[2:]
    year_found = []
    
    # 各競馬場を調査
    for venue_code, venue_name in venues.items():
        # 各月の1日を試す
        for month in range(1, 13):
            race_id = f'{year_prefix}{venue_code}{month:02d}0101'  # 月の1日、1R
            
            exists, horse_count = check_race_exists(race_id)
            if exists:
                print(f"  ✅ {venue_name} {month}月: {race_id} ({horse_count}頭)")
                year_found.append((race_id, f'{year}年 {venue_name} {month}月'))
                break  # この年度で1つ見つかれば次の年へ
            
            time.sleep(0.1)
        
        if year_found:
            break
    
    if year_found:
        found_races[year] = year_found[0]
    else:
        print(f"  ❌ {year}年: レースが見つかりませんでした")
    
    print()

print(f"{'='*80}")
print(f"📊 調査結果\n")

if found_races:
    print(f"見つかったレース: {len(found_races)}年分\n")
    for year, (race_id, desc) in found_races.items():
        print(f"  {year}年: {race_id} ({desc})")
    
    # 見つかったレースIDをファイルに保存
    with open('/Users/itoudaiki/Program/dai-keiba/scripts/nar_found_races_2022_2026.txt', 'w') as f:
        for year, (race_id, desc) in sorted(found_races.items()):
            f.write(f'{race_id},{desc}\n')
    
    print(f"\n💾 レースIDを保存: nar_found_races_2022_2026.txt")
else:
    print("❌ 2022-2026年のNARレースは見つかりませんでした")
    print("\n💡 可能性:")
    print("  - NARデータは2021年までしか公開されていない")
    print("  - レースID形式が変更された")
    print("  - データ公開に時間差がある")
