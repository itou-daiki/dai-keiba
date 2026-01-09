#!/usr/bin/env python3
"""
枠と厩舎のセル位置を確認
"""

import requests
from bs4 import BeautifulSoup
import re

# JRAレース
jra_race_id = "202406050811"
jra_url = f"https://race.netkeiba.com/race/result.html?race_id={jra_race_id}"

print("🔍 JRAレース結果テーブル分析")
print(f"{'='*80}\n")

headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(jra_url, headers=headers, timeout=15)
resp.encoding = 'EUC-JP'
soup = BeautifulSoup(resp.text, 'html.parser')

# レース結果テーブル
tables = soup.find_all('table')
result_table = None
for t in tables:
    if '着順' in t.text and '馬名' in t.text:
        result_table = t
        break

if result_table:
    rows = result_table.find_all('tr')
    
    # ヘッダー行
    header_row = rows[0]
    headers_cells = header_row.find_all('th')
    print("📋 ヘッダー:")
    for i, th in enumerate(headers_cells):
        print(f"  {i}: {th.text.strip()}")
    
    # データ行(最初の馬)
    print(f"\n📋 データ行(最初の馬):")
    data_row = None
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) >= 10:
            data_row = row
            break
    
    if data_row:
        cells = data_row.find_all('td')
        print(f"  総セル数: {len(cells)}\n")
        
        for i, cell in enumerate(cells):
            text = cell.text.strip()[:50]
            
            # 枠番を探す
            if cell.find('img'):
                img = cell.find('img')
                if 'alt' in img.attrs:
                    print(f"  {i}: {text} (画像alt: {img['alt']})")
                else:
                    print(f"  {i}: {text} (画像あり)")
            else:
                print(f"  {i}: {text}")
        
        # 枠番の位置を特定
        print(f"\n🔍 枠番:")
        for i, cell in enumerate(cells):
            img = cell.find('img')
            if img and 'alt' in img.attrs and '枠' in img['alt']:
                print(f"  セル{i}: {img['alt']}")
        
        # 厩舎の位置を特定
        print(f"\n🔍 厩舎:")
        for i, cell in enumerate(cells):
            text = cell.text.strip()
            if '美浦' in text or '栗東' in text or '北海道' in text or '兵庫' in text:
                print(f"  セル{i}: {text}")

# NARレース
print(f"\n{'='*80}\n")
print("🔍 NARレース結果テーブル分析")
print(f"{'='*80}\n")

nar_race_id = "202030041501"
nar_url = f"https://nar.netkeiba.com/race/result.html?race_id={nar_race_id}"

resp2 = requests.get(nar_url, headers=headers, timeout=15)
resp2.encoding = 'EUC-JP'
soup2 = BeautifulSoup(resp2.text, 'html.parser')

tables2 = soup2.find_all('table')
result_table2 = None
for t in tables2:
    if '着順' in t.text and '馬名' in t.text:
        result_table2 = t
        break

if result_table2:
    rows2 = result_table2.find_all('tr')
    
    # ヘッダー行
    header_row2 = rows2[0]
    headers_cells2 = header_row2.find_all('th')
    print("📋 ヘッダー:")
    for i, th in enumerate(headers_cells2):
        print(f"  {i}: {th.text.strip()}")
    
    # データ行
    print(f"\n📋 データ行(最初の馬):")
    data_row2 = None
    for row in rows2[1:]:
        cells = row.find_all('td')
        if len(cells) >= 10:
            data_row2 = row
            break
    
    if data_row2:
        cells2 = data_row2.find_all('td')
        print(f"  総セル数: {len(cells2)}\n")
        
        for i, cell in enumerate(cells2):
            text = cell.text.strip()[:50]
            
            if cell.find('img'):
                img = cell.find('img')
                if 'alt' in img.attrs:
                    print(f"  {i}: {text} (画像alt: {img['alt']})")
                else:
                    print(f"  {i}: {text} (画像あり)")
            else:
                print(f"  {i}: {text}")
