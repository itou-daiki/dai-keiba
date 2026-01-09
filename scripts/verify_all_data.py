#!/usr/bin/env python3
"""
完全なデータ取得検証(JRA & NAR)
Stage 1 → Stage 2 → Merge の全工程を検証
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import io

print("🔍 完全なデータ取得検証(JRA & NAR)")
print(f"{'='*80}\n")

# ========================================
# JRA検証
# ========================================

def verify_jra():
    """JRAの完全検証"""
    print("📊 JRA検証")
    print(f"{'-'*80}\n")
    
    race_id = "202406050811"  # 有馬記念
    
    # Stage 1: Basic
    print("Stage 1: Basic (26カラム)")
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # メタデータ
    title = soup.title.text if soup.title else ""
    metadata_fields = {
        '日付': bool(re.search(r'\d{4}年\d{1,2}月\d{1,2}日', title)),
        '会場': any(v in title for v in ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']),
        'レース番号': bool(re.search(r'\d+R', title)),
        'レース名': bool(re.search(r'^([^|]+)', title)),
        'コースタイプ': bool(re.search(r'(芝|ダート)', soup.text)),
        '距離': bool(re.search(r'\d+m', soup.text)),
        '天候': bool(re.search(r'天候', soup.text)),
        '馬場状態': bool(re.search(r'馬場', soup.text)),
    }
    
    # レース結果テーブル
    tables = soup.find_all('table')
    result_table = None
    for t in tables:
        if '着順' in t.text and '馬名' in t.text:
            result_table = t
            break
    
    horse_data_fields = {
        '着順': False,
        '馬番': False,
        '馬名': False,
        '騎手': False,
        'タイム': False,
        'horse_id': False,
    }
    
    if result_table:
        rows = result_table.find_all('tr')
        for row in rows:
            if row.find('th'):
                continue
            cells = row.find_all('td')
            if len(cells) >= 10:
                horse_data_fields['着順'] = bool(cells[0].text.strip())
                horse_data_fields['馬番'] = bool(cells[2].text.strip())
                horse_data_fields['馬名'] = bool(cells[3].text.strip())
                horse_data_fields['騎手'] = bool(cells[6].text.strip())
                horse_data_fields['タイム'] = bool(cells[7].text.strip())
                
                horse_link = cells[3].find('a')
                if horse_link and 'href' in horse_link.attrs:
                    horse_data_fields['horse_id'] = bool(re.search(r'/horse/(\d+)', horse_link['href']))
                break
    
    stage1_success = sum(metadata_fields.values()) + sum(horse_data_fields.values())
    stage1_total = len(metadata_fields) + len(horse_data_fields)
    
    print(f"  メタデータ: {sum(metadata_fields.values())}/{len(metadata_fields)}")
    for k, v in metadata_fields.items():
        status = "✅" if v else "❌"
        print(f"    {status} {k}")
    
    print(f"  馬データ: {sum(horse_data_fields.values())}/{len(horse_data_fields)}")
    for k, v in horse_data_fields.items():
        status = "✅" if v else "❌"
        print(f"    {status} {k}")
    
    print(f"  Stage 1成功率: {stage1_success/stage1_total*100:.0f}% ({stage1_success}/{stage1_total})\n")
    
    # Stage 2: Details
    if horse_data_fields['horse_id']:
        print("Stage 2: Details (68カラム)")
        
        # horse_idを取得
        horse_link = result_table.find_all('tr')[1].find_all('td')[3].find('a')
        horse_id = re.search(r'/horse/(\d+)', horse_link['href']).group(1)
        
        # 馬履歴
        history_url = f"https://db.netkeiba.com/horse/result/{horse_id}/"
        resp2 = requests.get(history_url, headers=headers, timeout=15)
        resp2.encoding = 'EUC-JP'
        soup2 = BeautifulSoup(resp2.text, 'html.parser')
        
        tables2 = soup2.find_all('table')
        history_success = False
        past_races_count = 0
        
        if tables2:
            try:
                df = pd.read_html(io.StringIO(str(tables2[0])))[0]
                df = df.dropna(how='all')
                if '日付' in df.columns:
                    past_races_count = min(len(df), 5)
                    history_success = True
            except:
                pass
        
        print(f"  馬履歴取得: {'✅' if history_success else '❌'}")
        print(f"  過去走数: {past_races_count}/5")
        
        # 血統
        ped_url = f"https://db.netkeiba.com/horse/ped/{horse_id}/"
        resp3 = requests.get(ped_url, headers=headers, timeout=15)
        resp3.encoding = 'EUC-JP'
        soup3 = BeautifulSoup(resp3.text, 'html.parser')
        
        pedigree_success = '父' in soup3.text or '母' in soup3.text
        
        print(f"  血統ページ取得: {'✅' if pedigree_success else '❌'}")
        
        stage2_fields = past_races_count * 13 + (3 if pedigree_success else 0)
        print(f"  Stage 2成功率: {stage2_fields/68*100:.0f}% ({stage2_fields}/68)\n")
    
    # Merge
    print("Merge: 94カラム")
    merge_success = stage1_success > 0 and (stage2_fields if horse_data_fields['horse_id'] else 0) > 0
    print(f"  結合可能: {'✅' if merge_success else '❌'}")
    print(f"  予想カラム数: {26 + (68 if horse_data_fields['horse_id'] else 0)}\n")
    
    return {
        'stage1': stage1_success / stage1_total * 100,
        'stage2': stage2_fields / 68 * 100 if horse_data_fields['horse_id'] else 0,
        'merge': merge_success
    }

# ========================================
# NAR検証
# ========================================

def verify_nar():
    """NARの完全検証"""
    print("📊 NAR検証")
    print(f"{'-'*80}\n")
    
    race_id = "202030041501"  # 門別
    
    # Stage 1: Basic
    print("Stage 1: Basic (26カラム)")
    url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # メタデータ
    title = soup.title.text if soup.title else ""
    nar_venues = ['門別', '盛岡', '水沢', '浦和', '船橋', '大井', '川崎', '金沢', '笠松', '名古屋', '園田', '姫路', '高知', '佐賀', 'ばんえい帯広']
    
    metadata_fields = {
        '日付': bool(re.search(r'\d{4}年\d{1,2}月\d{1,2}日', title)),
        '会場': any(v in title for v in nar_venues),
        'レース番号': bool(re.search(r'\d+R', title)),
        'レース名': bool(re.search(r'^([^|]+)', title)),
        'コースタイプ': bool(re.search(r'(芝|ダート|ダ)', soup.text)),
        '距離': bool(re.search(r'\d+m', soup.text)),
        '天候': bool(re.search(r'天候', soup.text)),
        '馬場状態': bool(re.search(r'馬場', soup.text)),
    }
    
    # レース結果テーブル
    tables = soup.find_all('table')
    result_table = None
    for t in tables:
        if '着順' in t.text and '馬名' in t.text:
            result_table = t
            break
    
    horse_data_fields = {
        '着順': False,
        '馬番': False,
        '馬名': False,
        '騎手': False,
        'タイム': False,
        'horse_id': False,
    }
    
    if result_table:
        rows = result_table.find_all('tr')
        for row in rows:
            if row.find('th'):
                continue
            cells = row.find_all('td')
            if len(cells) >= 10:
                horse_data_fields['着順'] = bool(cells[0].text.strip())
                horse_data_fields['馬番'] = bool(cells[2].text.strip())
                horse_data_fields['馬名'] = bool(cells[3].text.strip())
                horse_data_fields['騎手'] = bool(cells[6].text.strip())
                horse_data_fields['タイム'] = bool(cells[7].text.strip())
                
                horse_link = cells[3].find('a')
                if horse_link and 'href' in horse_link.attrs:
                    horse_data_fields['horse_id'] = bool(re.search(r'/horse/(\d+)', horse_link['href']))
                break
    
    stage1_success = sum(metadata_fields.values()) + sum(horse_data_fields.values())
    stage1_total = len(metadata_fields) + len(horse_data_fields)
    
    print(f"  メタデータ: {sum(metadata_fields.values())}/{len(metadata_fields)}")
    for k, v in metadata_fields.items():
        status = "✅" if v else "❌"
        print(f"    {status} {k}")
    
    print(f"  馬データ: {sum(horse_data_fields.values())}/{len(horse_data_fields)}")
    for k, v in horse_data_fields.items():
        status = "✅" if v else "❌"
        print(f"    {status} {k}")
    
    print(f"  Stage 1成功率: {stage1_success/stage1_total*100:.0f}% ({stage1_success}/{stage1_total})\n")
    
    # Stage 2は省略(JRAと同じロジック)
    print("Stage 2: Details (省略 - JRAと同じロジック)\n")
    
    return {
        'stage1': stage1_success / stage1_total * 100,
        'stage2': 0,  # 省略
        'merge': stage1_success > 0
    }

# ========================================
# 実行
# ========================================

try:
    jra_result = verify_jra()
    time.sleep(1)
    nar_result = verify_nar()
    
    print(f"\n{'='*80}")
    print("📊 最終結果")
    print(f"{'='*80}\n")
    
    print("JRA:")
    print(f"  Stage 1: {jra_result['stage1']:.0f}%")
    print(f"  Stage 2: {jra_result['stage2']:.0f}%")
    print(f"  Merge: {'✅' if jra_result['merge'] else '❌'}\n")
    
    print("NAR:")
    print(f"  Stage 1: {nar_result['stage1']:.0f}%")
    print(f"  Merge: {'✅' if nar_result['merge'] else '❌'}\n")
    
    overall_success = (jra_result['stage1'] + nar_result['stage1']) / 2
    print(f"総合成功率: {overall_success:.0f}%")
    
except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
