#!/usr/bin/env python3
"""
NAR 2022-2025年のレースを正しい形式で探索
YYYYVVMMDDNN (12桁)
"""

import requests
from bs4 import BeautifulSoup
import time

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
                if len(rows) > 2:
                    return True, len(rows) - 1
        return False, 0
    except:
        return False, 0

print("🔍 NAR 2022-2025年 レース探索(正しい形式)\n")
print(f"{'='*80}\n")

found_races = {}

# 浦和(42)で探索
for year in [2022, 2023, 2024, 2025]:
    print(f"📅 {year}年を調査中...")
    
    # 1月の最初の数日を試す
    for day in range(1, 10):
        race_id = f'{year}42010{day:02d}01'  # 浦和、1月、1R
        
        exists, horse_count = check_race_exists(race_id)
        if exists:
            print(f"  ✅ 浦和 1月{day}日: {race_id} ({horse_count}頭)")
            found_races[year] = (race_id, f'{year}年 浦和 1月{day}日')
            break
        
        time.sleep(0.2)
    
    if year not in found_races:
        print(f"  ❌ {year}年: レースが見つかりませんでした")
    
    print()

print(f"{'='*80}")
print(f"📊 調査結果\n")

if found_races:
    print(f"✅ 見つかったレース: {len(found_races)}年分\n")
    for year, (race_id, desc) in sorted(found_races.items()):
        print(f"  {year}年: {race_id} ({desc})")
else:
    print("❌ 2022-2025年のNARレースは見つかりませんでした")
