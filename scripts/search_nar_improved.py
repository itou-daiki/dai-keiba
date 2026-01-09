#!/usr/bin/env python3
"""
NAR レースID形式を正しく理解して2022-2026年を探索
成功した2020-2021年のパターンを基に探索
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

print("🔍 NAR 2022-2026年 レースID探索(改善版)\n")
print(f"{'='*80}\n")

# 成功パターン: 門別(30)、04月、15日
# 2020: 202030041501
# 2021: 202130041501

found_races = {}

for year in [2022, 2023, 2024, 2025, 2026]:
    print(f"📅 {year}年を調査中...")
    year_prefix = str(year)[2:]
    
    # 門別の4月15-20日を試す(2020-2021年と同じパターン)
    for day in range(15, 25):
        race_id = f'{year_prefix}30041{day:02d}01'
        
        exists, horse_count = check_race_exists(race_id)
        if exists:
            print(f"  ✅ 門別 4月{day}日: {race_id} ({horse_count}頭)")
            found_races[year] = (race_id, f'{year}年 門別 4月{day}日')
            break
        
        time.sleep(0.2)
    
    if year not in found_races:
        # 他の月も試す
        for month in [5, 6, 7, 8, 9]:
            for day in [1, 15]:
                race_id = f'{year_prefix}30{month:02d}{day:02d}01'
                
                exists, horse_count = check_race_exists(race_id)
                if exists:
                    print(f"  ✅ 門別 {month}月{day}日: {race_id} ({horse_count}頭)")
                    found_races[year] = (race_id, f'{year}年 門別 {month}月{day}日')
                    break
                
                time.sleep(0.2)
            
            if year in found_races:
                break
    
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
    print("❌ 2022-2026年のNARレースは見つかりませんでした")
