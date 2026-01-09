#!/usr/bin/env python3
"""
コーナー通過順の分析
JRAとNARの複数レースでコーナー通過順のデータ構造を確認
"""

import requests
from bs4 import BeautifulSoup
import re

def analyze_corner_passing(race_id, url_base, race_type, description):
    """コーナー通過順のデータ構造を分析"""
    
    print(f"\n{'='*80}")
    print(f"🔍 {race_type}: {description}")
    print(f"{'='*80}\n")
    print(f"Race ID: {race_id}\n")
    
    url = f"{url_base}/race/result.html?race_id={race_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # レース結果テーブル
    tables = soup.find_all('table')
    result_table = None
    for t in tables:
        if '着順' in t.text and '馬名' in t.text:
            result_table = t
            break
    
    if not result_table:
        print("❌ レース結果テーブルなし")
        return
    
    # ヘッダー確認
    rows = result_table.find_all('tr')
    header_row = rows[0]
    headers = [th.text.strip() for th in header_row.find_all('th')]
    
    print(f"📋 ヘッダー({len(headers)}カラム):")
    for i, h in enumerate(headers):
        if 'コーナー' in h or '通過' in h:
            print(f"  ✅ {i}: {h}")
        else:
            print(f"  {i}: {h}")
    
    # コーナー通過順のカラムインデックスを探す
    corner_index = None
    for i, h in enumerate(headers):
        if 'コーナー' in h or '通過' in h:
            corner_index = i
            break
    
    if corner_index is None:
        print("\n❌ コーナー通過順カラムなし")
        return
    
    print(f"\n📊 コーナー通過順データ(最初の5頭):")
    print(f"{'-'*80}")
    
    # データ行を解析
    for row in rows[1:6]:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        umaban = cells[2].text.strip() if len(cells) > 2 else ''
        horse_name = cells[3].text.strip() if len(cells) > 3 else ''
        
        if corner_index < len(cells):
            corner_data = cells[corner_index].text.strip()
            print(f"  馬番{umaban} ({horse_name}): {corner_data}")
        else:
            print(f"  馬番{umaban} ({horse_name}): データなし")
    
    # 1頭目の詳細解析
    print(f"\n📊 1頭目の詳細解析:")
    print(f"{'-'*80}")
    
    first_data_row = None
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) >= 3:
            first_data_row = row
            break
    
    if first_data_row and corner_index < len(first_data_row.find_all('td')):
        cells = first_data_row.find_all('td')
        umaban = cells[2].text.strip()
        corner_text = cells[corner_index].text.strip()
        
        print(f"  馬番: {umaban}")
        print(f"  コーナー通過順(生データ): '{corner_text}'")
        
        # パース
        # 形式: "1-2-3-4" または "1-2" など
        if corner_text and '-' in corner_text:
            positions = corner_text.split('-')
            print(f"  コーナー数: {len(positions)}")
            for i, pos in enumerate(positions, 1):
                print(f"    {i}コーナー: {pos}")
        else:
            print(f"  ⚠️ パース不可")

# テストケース
test_cases = [
    # JRA
    ("202406050811", "https://race.netkeiba.com", "JRA", "有馬記念(芝2500m)"),
    ("202405050511", "https://race.netkeiba.com", "JRA", "東京11R(芝1600m)"),
    ("202401010101", "https://race.netkeiba.com", "JRA", "札幌1R(ダート1000m)"),
    
    # NAR
    ("202030041501", "https://nar.netkeiba.com", "NAR", "門別1R(ダート1200m)"),
    ("202130041501", "https://nar.netkeiba.com", "NAR", "門別1R(ダート1000m)"),
]

print("🧪 コーナー通過順データ構造分析\n")

for race_id, url_base, race_type, description in test_cases:
    analyze_corner_passing(race_id, url_base, race_type, description)

print(f"\n{'='*80}")
print("✅ 分析完了")
print(f"{'='*80}")
