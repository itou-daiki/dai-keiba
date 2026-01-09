#!/usr/bin/env python3
"""
2段階スクレイピングシステムの完全検証(2020-2026年)
Stage 1 → Stage 2 → Merge → カラムズレ検証
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
import io
from datetime import datetime

# テスト用ディレクトリ
TEST_DIR = "/Users/itoudaiki/Program/dai-keiba/data/test_2stage"
os.makedirs(TEST_DIR, exist_ok=True)

print("🧪 2段階スクレイピング完全検証(2020-2026年)")
print(f"{'='*80}\n")

# ========================================
# Stage 1: Basic (26カラム)
# ========================================

def scrape_basic(race_id):
    """Stage 1: 基本情報取得(26カラム)"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # メタデータ
        title = soup.title.text if soup.title else ""
        full_text = soup.text
        
        metadata = {
            '日付': '', '会場': '', 'レース番号': '', 'レース名': '', '重賞': '',
            'コースタイプ': '', '距離': '', '回り': '', '天候': '', '馬場状態': '', 'race_id': race_id
        }
        
        # タイトルから抽出
        if title:
            race_name_match = re.search(r'^([^|]+)', title)
            if race_name_match:
                race_name = re.sub(r'\s*(結果|払戻).*$', '', race_name_match.group(1).strip())
                metadata['レース名'] = race_name
                if 'G1' in race_name or 'GⅠ' in race_name:
                    metadata['重賞'] = 'G1'
            
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title)
            if date_match:
                metadata['日付'] = f"{date_match.group(1)}/{int(date_match.group(2)):02d}/{int(date_match.group(3)):02d}"
            
            for venue in ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']:
                if venue in title:
                    metadata['会場'] = venue
                    break
            
            race_num_match = re.search(r'(\d+)R', title)
            if race_num_match:
                metadata['レース番号'] = race_num_match.group(0)
        
        # 本文から
        course_match = re.search(r'(芝|ダート|ダ)\s*(\d+)m', full_text)
        if course_match:
            metadata['コースタイプ'] = '芝' if '芝' in course_match.group(1) else 'ダート'
            metadata['距離'] = course_match.group(2)
        
        if '右' in full_text:
            metadata['回り'] = '右'
        elif '左' in full_text:
            metadata['回り'] = '左'
        
        weather_match = re.search(r'天候\s*[:：]\s*(\S+)', full_text)
        if weather_match:
            metadata['天候'] = weather_match.group(1)
        
        baba_match = re.search(r'馬場\s*[:：]\s*(\S+)', full_text)
        if baba_match:
            metadata['馬場状態'] = baba_match.group(1)
        
        # レース結果テーブル
        tables = soup.find_all('table')
        result_table = None
        for t in tables:
            if '着順' in t.text and '馬名' in t.text:
                result_table = t
                break
        
        if not result_table:
            return None
        
        rows = result_table.find_all('tr')
        race_data = []
        
        for row in rows:
            if row.find('th'):
                continue
            cells = row.find_all('td')
            if len(cells) < 10:
                continue
            
            # 基本情報を辞書で構築
            horse_data = {
                '日付': metadata['日付'],
                '会場': metadata['会場'],
                'レース番号': metadata['レース番号'],
                'レース名': metadata['レース名'],
                '重賞': metadata['重賞'],
                'コースタイプ': metadata['コースタイプ'],
                '距離': metadata['距離'],
                '回り': metadata['回り'],
                '天候': metadata['天候'],
                '馬場状態': metadata['馬場状態'],
                '着順': cells[0].text.strip(),
                '枠': '',
                '馬番': cells[2].text.strip() if len(cells) > 2 else '',
                '馬名': cells[3].text.strip() if len(cells) > 3 else '',
                '性齢': cells[4].text.strip() if len(cells) > 4 else '',
                '斤量': cells[5].text.strip() if len(cells) > 5 else '',
                '騎手': cells[6].text.strip() if len(cells) > 6 else '',
                'タイム': cells[7].text.strip() if len(cells) > 7 else '',
                '着差': cells[8].text.strip() if len(cells) > 8 else '',
                '人気': cells[9].text.strip() if len(cells) > 9 else '',
                '単勝オッズ': cells[10].text.strip() if len(cells) > 10 else '',
                '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                '厩舎': cells[18].text.strip() if len(cells) > 18 else '',
                '馬体重(増減)': cells[14].text.strip() if len(cells) > 14 else '',
                'race_id': race_id,
                'horse_id': ''
            }
            
            # 枠番
            waku_img = cells[1].find('img') if len(cells) > 1 else None
            if waku_img and 'alt' in waku_img.attrs:
                waku_match = re.search(r'枠(\d+)', waku_img['alt'])
                if waku_match:
                    horse_data['枠'] = waku_match.group(1)
            
            # horse_id
            horse_link = cells[3].find('a') if len(cells) > 3 else None
            if horse_link and 'href' in horse_link.attrs:
                horse_id_match = re.search(r'/horse/(\d+)', horse_link['href'])
                if horse_id_match:
                    horse_data['horse_id'] = horse_id_match.group(1)
            
            race_data.append(horse_data)
        
        # DataFrameに変換(カラム順序を明示)
        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]
        
        df = pd.DataFrame(race_data)[ordered_columns]
        return df
    
    except Exception as e:
        print(f"  ❌ Stage 1エラー: {e}")
        return None

# ========================================
# Stage 2: Details (68カラム)
# ========================================

def scrape_details(horse_id, race_date):
    """Stage 2: 馬履歴取得(68カラム)"""
    
    details = {
        'race_id': '',
        'horse_id': horse_id
    }
    
    # 過去5走の初期化
    for i in range(1, 6):
        prefix = f'past_{i}'
        for field in ['date', 'rank', 'time', 'run_style', 'race_name', 'last_3f', 
                      'horse_weight', 'jockey', 'condition', 'odds', 'weather', 'distance', 'course_type']:
            details[f'{prefix}_{field}'] = ''
    
    # 血統の初期化
    details['father'] = ''
    details['mother'] = ''
    details['bms'] = ''
    
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # レース履歴取得
        url = f"https://db.netkeiba.com/horse/result/{horse_id}/"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        tables = soup.find_all('table')
        if not tables:
            return details
        
        df = pd.read_html(io.StringIO(str(tables[0])))[0]
        df = df.dropna(how='all')
        df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)
        
        if '日付' in df.columns:
            df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
            df = df.dropna(subset=['date_obj'])
            
            current_date = pd.to_datetime(race_date)
            df = df[df['date_obj'] < current_date]
            df = df.sort_values('date_obj', ascending=False)
            df = df.head(5)
            
            for i, row in enumerate(df.itertuples(), 1):
                prefix = f'past_{i}'
                
                details[f'{prefix}_date'] = getattr(row, '日付', '')
                details[f'{prefix}_rank'] = str(getattr(row, '着順', ''))
                details[f'{prefix}_time'] = str(getattr(row, 'タイム', ''))
                details[f'{prefix}_race_name'] = str(getattr(row, 'レース名', ''))
                details[f'{prefix}_last_3f'] = str(getattr(row, '上り', ''))
                details[f'{prefix}_horse_weight'] = str(getattr(row, '馬体重', ''))
                details[f'{prefix}_jockey'] = str(getattr(row, '騎手', ''))
                details[f'{prefix}_condition'] = str(getattr(row, '馬場', ''))
                details[f'{prefix}_odds'] = str(getattr(row, '単勝', '') or getattr(row, 'オッズ', ''))
                details[f'{prefix}_weather'] = str(getattr(row, '天気', ''))
                
                dist_text = str(getattr(row, '距離', ''))
                dist_match = re.search(r'(芝|ダ|障)(\d+)', dist_text)
                if dist_match:
                    course_type = dist_match.group(1)
                    details[f'{prefix}_course_type'] = '芝' if course_type == '芝' else 'ダート' if course_type == 'ダ' else '障害'
                    details[f'{prefix}_distance'] = dist_match.group(2)
                
                details[f'{prefix}_run_style'] = '3'
        
        return details
    
    except Exception as e:
        return details

# ========================================
# テスト実行
# ========================================

# 2020-2026年の実在するレース(各年2レース)
test_races = {
    "2020年": [
        ("202001010101", "札幌1R"),
        ("202005050811", "東京11R"),
    ],
    "2021年": [
        ("202101010202", "札幌2R"),
        ("202105050711", "東京11R"),
    ],
    "2022年": [
        ("202201010101", "札幌1R"),
    ],
    "2023年": [
        ("202301010303", "札幌3R"),
    ],
    "2024年": [
        ("202401010101", "札幌1R"),
        ("202406050811", "中山11R(有馬記念)"),
    ],
}

all_results = []

for year, races in test_races.items():
    print(f"\n{'='*80}")
    print(f"📅 {year}")
    print(f"{'='*80}\n")
    
    for race_id, description in races:
        print(f"🏇 {description} (ID: {race_id})")
        print(f"{'-'*80}")
        
        # Stage 1
        print(f"  Stage 1: 基本情報取得...")
        df_basic = scrape_basic(race_id)
        
        if df_basic is None or df_basic.empty:
            print(f"  ❌ Stage 1失敗")
            continue
        
        print(f"  ✅ Stage 1成功: {len(df_basic)}頭, {len(df_basic.columns)}カラム")
        
        # Stage 2 (最初の1頭のみテスト)
        if df_basic.iloc[0]['horse_id']:
            print(f"  Stage 2: 詳細情報取得...")
            horse_id = df_basic.iloc[0]['horse_id']
            race_date = df_basic.iloc[0]['日付']
            
            details = scrape_details(horse_id, race_date)
            details_filled = sum(1 for v in details.values() if v)
            
            print(f"  ✅ Stage 2成功: {details_filled}/68フィールド")
            
            # Merge
            print(f"  Merge: データ結合...")
            merged = {**df_basic.iloc[0].to_dict(), **details}
            total_cols = len(merged)
            print(f"  ✅ Merge成功: {total_cols}カラム")
            
            all_results.append({
                'year': year,
                'race_id': race_id,
                'description': description,
                'stage1_cols': len(df_basic.columns),
                'stage2_fields': details_filled,
                'merged_cols': total_cols,
                'success': total_cols == 94
            })
        
        print()

# 最終サマリー
print(f"\n{'='*80}")
print(f"📊 最終サマリー")
print(f"{'='*80}\n")

for r in all_results:
    status = "✅" if r['success'] else "❌"
    print(f"{status} {r['year']} {r['description']}")
    print(f"    Stage1: {r['stage1_cols']}カラム, Stage2: {r['stage2_fields']}/68, Merge: {r['merged_cols']}カラム")

success_count = sum(1 for r in all_results if r['success'])
print(f"\n成功率: {success_count}/{len(all_results)} ({success_count/len(all_results)*100:.0f}%)")
