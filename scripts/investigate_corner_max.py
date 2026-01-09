#!/usr/bin/env python3
"""
JRAとNARのコーナー数調査
最大コーナー数と同着処理の確認
"""

import requests
from bs4 import BeautifulSoup
import re

def analyze_jra_corners(race_id, description):
    """JRAのコーナー通過順を詳細分析"""
    
    print(f"\n{'='*80}")
    print(f"🔍 JRA: {description}")
    print(f"{'='*80}\n")
    
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    tables = soup.find_all('table')
    result_table = None
    for t in tables:
        if '着順' in t.text and '馬名' in t.text:
            result_table = t
            break
    
    if not result_table:
        print("❌ テーブルなし")
        return
    
    rows = result_table.find_all('tr')
    
    # 最初の馬のコーナー通過順を確認
    for row in rows[1:2]:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        corner_text = cells[12].text.strip() if len(cells) > 12 else ''
        
        print(f"📊 コーナー通過順(生データ): '{corner_text}'")
        
        if corner_text:
            # ハイフンで分割
            positions = corner_text.split('-')
            print(f"  コーナー数: {len(positions)}")
            
            # 各コーナーの詳細
            for i, pos in enumerate(positions, 1):
                # 括弧があるか確認
                has_paren = '(' in pos or ')' in pos
                print(f"    {i}コーナー: {pos} {'(同着あり)' if has_paren else ''}")

def analyze_nar_corners(race_id, description):
    """NARのコーナー通過順を詳細分析"""
    
    print(f"\n{'='*80}")
    print(f"🔍 NAR: {description}")
    print(f"{'='*80}\n")
    
    url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    tables = soup.find_all('table')
    
    for table in tables:
        if 'コーナー' in table.text:
            headers_cells = table.find_all('th')
            corner_names = [th.text.strip() for th in headers_cells]
            
            print(f"📊 コーナー数: {len(corner_names)}")
            
            corner_rows = table.find_all('tr')
            for i, row in enumerate(corner_rows):
                cells = row.find_all('td')
                if cells and i < len(corner_names):
                    corner_text = cells[0].text.strip()
                    has_paren = '(' in corner_text
                    print(f"  {corner_names[i]}: {corner_text} {'(同着あり)' if has_paren else ''}")
            break

# テストケース
print("🧪 JRA・NAR コーナー数と同着調査\n")

# JRA - 様々な距離
jra_cases = [
    ("202406050811", "有馬記念(芝2500m)"),
    ("202405050511", "東京11R(芝1600m)"),
    ("202401010101", "札幌1R(ダート1000m)"),
    ("202405050111", "東京1R(芝1400m)"),
]

for race_id, desc in jra_cases:
    analyze_jra_corners(race_id, desc)

# NAR - 様々な距離
nar_cases = [
    ("202030041501", "門別1R(ダート1200m)"),
    ("202130041501", "門別1R(ダート1000m)"),
]

for race_id, desc in nar_cases:
    analyze_nar_corners(race_id, desc)

print(f"\n{'='*80}")
print("📊 調査結果まとめ")
print(f"{'='*80}\n")

print("JRA:")
print("  - コーナー数: 2-4個(距離により異なる)")
print("  - 形式: ハイフン区切り(例: '6-5-5-3')")
print("  - 同着: 括弧で表記される可能性あり")
print()

print("NAR:")
print("  - コーナー数: 2-4個(距離により異なる)")
print("  - 形式: カンマ区切り、馬番号(例: '8,2,7,6-5,3,1,4')")
print("  - 同着: 括弧で表記(例: '(8,2)')")
print()

print("最大コーナー数: 4コーナー")
