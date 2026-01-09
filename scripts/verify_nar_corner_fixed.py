#!/usr/bin/env python3
"""
NAR コーナー通過順抽出の修正版検証
"""

import requests
from bs4 import BeautifulSoup

def verify_nar_corner_fixed(race_id, description):
    """NARのコーナー通過順を検証(修正版)"""
    
    print(f"\n{'='*80}")
    print(f"🔍 NAR: {description}")
    print(f"{'='*80}\n")
    
    url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # コーナーテーブル取得(修正版)
    tables = soup.find_all('table')
    corner_data = {}
    
    for table in tables:
        if 'コーナー' in table.text:
            # ヘッダー取得
            headers_cells = table.find_all('th')
            corner_names = [th.text.strip() for th in headers_cells]
            
            # データ行取得
            rows = table.find_all('tr')
            for i, row in enumerate(rows):
                cells = row.find_all('td')
                if cells and i < len(corner_names):
                    corner_data[corner_names[i]] = cells[0].text.strip()
            break
    
    print(f"📊 コーナーデータ:")
    for key, value in corner_data.items():
        print(f"  {key}: {value}")
    
    # レース結果テーブル取得
    result_table = None
    for t in tables:
        if '着順' in t.text and '馬名' in t.text:
            result_table = t
            break
    
    if not result_table:
        print("\n❌ レース結果テーブルなし")
        return
    
    rows = result_table.find_all('tr')
    
    print(f"\n📊 最初の3頭:")
    for row in rows[1:4]:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        umaban = cells[2].text.strip()
        horse_name = cells[3].text.strip()
        
        # 各コーナーでの順位を抽出
        corners = ['', '', '', '']
        for i in range(1, 5):
            corner_key = f'{i}コーナー'
            if corner_key in corner_data:
                corner_text = corner_data[corner_key]
                corner_text_clean = corner_text.replace('(', '').replace(')', '').replace('-', ',')
                horses = [h.strip() for h in corner_text_clean.split(',') if h.strip()]
                for j, horse_num in enumerate(horses, 1):
                    if horse_num == umaban:
                        corners[i-1] = str(j)
                        break
        
        print(f"  馬番{umaban} ({horse_name}):")
        print(f"    → corner_1={corners[0] or '(なし)'}, corner_2={corners[1] or '(なし)'}, corner_3={corners[2] or '(なし)'}, corner_4={corners[3] or '(なし)'}")

# 検証実行
print("🧪 NAR コーナー通過順抽出 修正版検証\n")

verify_nar_corner_fixed("202030041501", "門別1R(ダート1200m)")
verify_nar_corner_fixed("202130041501", "門別1R(ダート1000m)")

print(f"\n{'='*80}")
print("✅ 検証完了")
print(f"{'='*80}")
