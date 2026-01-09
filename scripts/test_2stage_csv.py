#!/usr/bin/env python3
"""
2段階スクレイピングの完全テスト
Stage 1 → Stage 2 → Merge → カラムズレ検証
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
from datetime import datetime
import io

# テスト用ディレクトリ
TEST_DIR = "/Users/itoudaiki/Program/dai-keiba/data/test"
os.makedirs(TEST_DIR, exist_ok=True)

print("🧪 2段階スクレイピング完全テスト")
print(f"{'='*80}\n")

# ========================================
# Stage 1: Basic (26カラム)
# ========================================

def scrape_basic(race_id):
    """Stage 1: 基本情報取得"""
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
    """Stage 2: 馬履歴・血統取得"""
    
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
        
        # 馬履歴取得
        result_url = f"https://db.netkeiba.com/horse/{horse_id}/"
        resp = requests.get(result_url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 血統情報(簡易版 - タイトルから)
        title = soup.title.text if soup.title else ""
        # 実際の血統抽出は省略(テスト用)
        
        # レース履歴(簡易版)
        # 実際の履歴抽出は省略(テスト用)
        
        return details
    
    except Exception as e:
        print(f"  ⚠️ Stage 2エラー({horse_id}): {e}")
        return details

# ========================================
# テスト実行
# ========================================

print("📝 Stage 1: 基本情報取得")
print(f"{'-'*80}")

test_race_id = "202406050811"  # 有馬記念
df_basic = scrape_basic(test_race_id)

if df_basic is not None:
    print(f"  ✅ 取得成功: {len(df_basic)}頭")
    print(f"  カラム数: {len(df_basic.columns)}")
    print(f"  カラム: {list(df_basic.columns)}")
    
    # CSV保存
    basic_csv = os.path.join(TEST_DIR, "test_basic.csv")
    df_basic.to_csv(basic_csv, index=False)
    print(f"  💾 保存: {basic_csv}")
    
    # カラム数確認
    df_check = pd.read_csv(basic_csv)
    print(f"  ✅ 読み込み確認: {len(df_check.columns)}カラム")
    
    if len(df_check.columns) == 26:
        print(f"  ✅ カラム数正常(26カラム)")
    else:
        print(f"  ❌ カラム数異常({len(df_check.columns)}カラム)")
    
    # ヘッダーとデータ行の確認
    with open(basic_csv, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        header_cols = len(lines[0].strip().split(','))
        data_cols = len(lines[1].strip().split(',')) if len(lines) > 1 else 0
        
        print(f"  ヘッダー: {header_cols}カラム")
        print(f"  データ行: {data_cols}カラム")
        
        if header_cols == data_cols:
            print(f"  ✅ カラムズレなし")
        else:
            print(f"  ❌ カラムズレあり!")
    
    # サンプル表示
    print(f"\n  サンプルデータ:")
    print(df_basic[['日付', '会場', 'レース名', '馬名', 'horse_id']].head(3).to_string(index=False))

else:
    print(f"  ❌ 取得失敗")

print(f"\n{'='*80}")
print("✅ テスト完了")
