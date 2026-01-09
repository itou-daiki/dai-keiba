#!/usr/bin/env python3
"""
NAR 2022-2026年の実際のrace_idを収集
netkeibaのトップページやカレンダーから実際のIDを取得
"""

import requests
from bs4 import BeautifulSoup
import re
import time

def get_race_ids_from_url(url):
    """URLからrace_idを抽出"""
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        race_ids = set()
        
        for link in links:
            href = link['href']
            match = re.search(r'race_id=(\d+)', href)
            if match:
                race_ids.add(match.group(1))
        
        return race_ids
    except:
        return set()

print("🔍 NAR 2022-2026年 実際のrace_id収集\n")
print(f"{'='*80}\n")

# 収集するURL
urls = [
    'https://nar.netkeiba.com/',
    'https://nar.netkeiba.com/top/race_list.html',
]

all_race_ids = set()

for url in urls:
    print(f"📊 {url} を調査中...")
    race_ids = get_race_ids_from_url(url)
    print(f"   見つかったrace_id: {len(race_ids)}件")
    all_race_ids.update(race_ids)
    time.sleep(1)

print(f"\n合計: {len(all_race_ids)}件のrace_id\n")

# 年度別に分類
by_year = {}
for race_id in all_race_ids:
    if len(race_id) >= 2:
        year = '20' + race_id[:2]
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(race_id)

print("年度別:")
for year in sorted(by_year.keys(), reverse=True):
    ids = by_year[year]
    print(f"  {year}年: {len(ids)}件")
    if len(ids) <= 5:
        for race_id in sorted(ids):
            print(f"    - {race_id}")

# 2022-2026年のrace_idを保存
recent_ids = []
for year in ['2022', '2023', '2024', '2025', '2026']:
    if year in by_year:
        recent_ids.extend(by_year[year])

if recent_ids:
    print(f"\n💾 2022-2026年のrace_id: {len(recent_ids)}件")
    with open('/Users/itoudaiki/Program/dai-keiba/scripts/nar_race_ids_2022_2026.txt', 'w') as f:
        for race_id in sorted(recent_ids, reverse=True):
            f.write(f'{race_id}\n')
    print("   保存: nar_race_ids_2022_2026.txt")
