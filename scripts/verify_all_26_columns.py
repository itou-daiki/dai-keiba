#!/usr/bin/env python3
"""
全26カラムの完全検証(JRA & NAR)
各フィールドのセル位置を確認し、取得状況を検証
"""

import requests
from bs4 import BeautifulSoup
import re

def verify_all_fields(race_id, url, race_type):
    """全フィールドの取得を検証"""
    
    print(f"\n{'='*80}")
    print(f"🔍 {race_type} 全フィールド検証")
    print(f"{'='*80}\n")
    print(f"Race ID: {race_id}")
    print(f"URL: {url}\n")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # メタデータ
    title = soup.title.text if soup.title else ""
    full_text = soup.text
    
    print("📊 メタデータ:")
    print(f"{'-'*80}")
    
    metadata_results = {}
    
    # 日付
    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title)
    if date_match:
        date_val = f"{date_match.group(1)}/{int(date_match.group(2)):02d}/{int(date_match.group(3)):02d}"
        metadata_results['日付'] = date_val
        print(f"  ✅ 日付: {date_val}")
    else:
        metadata_results['日付'] = None
        print(f"  ❌ 日付: 取得失敗")
    
    # 会場
    if race_type == "JRA":
        venues = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']
    else:
        venues = ['門別', '盛岡', '水沢', '浦和', '船橋', '大井', '川崎', '金沢', '笠松', '名古屋', '園田', '姫路', '高知', '佐賀', 'ばんえい帯広']
    
    venue = None
    for v in venues:
        if v in title:
            venue = v
            break
    
    if venue:
        metadata_results['会場'] = venue
        print(f"  ✅ 会場: {venue}")
    else:
        metadata_results['会場'] = None
        print(f"  ❌ 会場: 取得失敗")
    
    # レース番号
    race_num_match = re.search(r'(\d+)R', title)
    if race_num_match:
        race_num = race_num_match.group(0)
        metadata_results['レース番号'] = race_num
        print(f"  ✅ レース番号: {race_num}")
    else:
        metadata_results['レース番号'] = None
        print(f"  ❌ レース番号: 取得失敗")
    
    # レース名
    race_name_match = re.search(r'^([^|]+)', title)
    if race_name_match:
        race_name = re.sub(r'\s*(結果|払戻|払い戻し).*$', '', race_name_match.group(1).strip())
        metadata_results['レース名'] = race_name
        print(f"  ✅ レース名: {race_name}")
    else:
        metadata_results['レース名'] = None
        print(f"  ❌ レース名: 取得失敗")
    
    # コースタイプ・距離
    course_match = re.search(r'(芝|ダート|ダ)\s*(\d+)m', full_text)
    if course_match:
        course_type = '芝' if '芝' in course_match.group(1) else 'ダート'
        distance = course_match.group(2)
        metadata_results['コースタイプ'] = course_type
        metadata_results['距離'] = distance
        print(f"  ✅ コースタイプ: {course_type}")
        print(f"  ✅ 距離: {distance}m")
    else:
        metadata_results['コースタイプ'] = None
        metadata_results['距離'] = None
        print(f"  ❌ コースタイプ: 取得失敗")
        print(f"  ❌ 距離: 取得失敗")
    
    # 天候
    weather_match = re.search(r'天候\s*[:：]?\s*(\S+)', full_text)
    if weather_match:
        weather = weather_match.group(1)
        metadata_results['天候'] = weather
        print(f"  ✅ 天候: {weather}")
    else:
        metadata_results['天候'] = None
        print(f"  ❌ 天候: 取得失敗")
    
    # 馬場状態
    baba_match = re.search(r'馬場\s*[:：]?\s*(\S+)', full_text)
    if baba_match:
        baba = baba_match.group(1)
        metadata_results['馬場状態'] = baba
        print(f"  ✅ 馬場状態: {baba}")
    else:
        metadata_results['馬場状態'] = None
        print(f"  ❌ 馬場状態: 取得失敗")
    
    # レース結果テーブル
    print(f"\n📊 馬データ(最初の1頭):")
    print(f"{'-'*80}")
    
    tables = soup.find_all('table')
    result_table = None
    for t in tables:
        if '着順' in t.text and '馬名' in t.text:
            result_table = t
            break
    
    if not result_table:
        print(f"  ❌ レース結果テーブルが見つかりません")
        return
    
    # ヘッダー確認
    rows = result_table.find_all('tr')
    header_row = rows[0]
    headers_cells = header_row.find_all('th')
    
    print(f"  ヘッダー({len(headers_cells)}カラム):")
    for i, th in enumerate(headers_cells):
        print(f"    {i}: {th.text.strip()}")
    
    # データ行
    data_row = None
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) >= 10:
            data_row = row
            break
    
    if not data_row:
        print(f"  ❌ データ行が見つかりません")
        return
    
    cells = data_row.find_all('td')
    print(f"\n  データセル({len(cells)}個):")
    
    # 各セルの内容を表示
    field_map = {
        0: '着順',
        1: '枠',
        2: '馬番',
        3: '馬名',
        4: '性齢',
        5: '斤量',
        6: '騎手',
        7: 'タイム',
        8: '着差',
        9: '人気',
        10: '単勝オッズ',
        11: '後3F',
    }
    
    # JRAとNARでセル位置が異なる
    if race_type == "JRA":
        field_map[13] = '厩舎'
        field_map[14] = '馬体重(増減)'
    else:  # NAR
        field_map[12] = '厩舎'
        field_map[13] = '馬体重(増減)'
    
    for i, cell in enumerate(cells):
        text = cell.text.strip()[:50]
        field_name = field_map.get(i, f'セル{i}')
        
        if text:
            print(f"    ✅ {i}: {field_name} = {text}")
        else:
            print(f"    ⚠️ {i}: {field_name} = (空)")
    
    # 馬体重(増減)の確認
    weight_cell_index = 14 if race_type == "JRA" else 13
    if len(cells) > weight_cell_index:
        weight_text = cells[weight_cell_index].text.strip()
        if weight_text:
            print(f"\n  ✅ 馬体重(増減): {weight_text}")
        else:
            print(f"\n  ❌ 馬体重(増減): 空")
    else:
        print(f"\n  ❌ 馬体重(増減): セル{weight_cell_index}が存在しません")
    
    # horse_id
    horse_link = cells[3].find('a') if len(cells) > 3 else None
    if horse_link and 'href' in horse_link.attrs:
        horse_id_match = re.search(r'/horse/(\d+)', horse_link['href'])
        if horse_id_match:
            print(f"  ✅ horse_id: {horse_id_match.group(1)}")
        else:
            print(f"  ❌ horse_id: 抽出失敗")
    else:
        print(f"  ❌ horse_id: リンクなし")

# JRA検証
verify_all_fields(
    "202406050811",
    "https://race.netkeiba.com/race/result.html?race_id=202406050811",
    "JRA"
)

# NAR検証
verify_all_fields(
    "202030041501",
    "https://nar.netkeiba.com/race/result.html?race_id=202030041501",
    "NAR"
)

print(f"\n{'='*80}")
print("✅ 検証完了")
print(f"{'='*80}")
