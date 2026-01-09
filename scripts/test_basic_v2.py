#!/usr/bin/env python3
"""
Stage 1 Basic ノートブックのテスト(1レース)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# メタデータ抽出関数(ノートブックと同じ)
def extract_metadata(soup, url):
    metadata = {
        '日付': '',
        '会場': '',
        'レース番号': '',
        'レース名': '',
        '重賞': '',
        'コースタイプ': '',
        '距離': '',
        '回り': '',
        '天候': '',
        '馬場状態': '',
        'race_id': ''
    }
    
    try:
        # レース名
        race_name_elem = soup.select_one('div.race_name')
        if race_name_elem:
            metadata['レース名'] = race_name_elem.text.strip()
        
        # ヘッダー情報
        header_elem = soup.select_one('div.header_line')
        if header_elem:
            header_text = header_elem.text.strip()
        else:
            header_text = soup.text
        
        # 日付
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', header_text)
        if date_match:
            year = date_match.group(1)
            month = f"{int(date_match.group(2)):02d}"
            day = f"{int(date_match.group(3)):02d}"
            metadata['日付'] = f"{year}/{month}/{day}"
        
        # 会場、回、日
        venues = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']
        venue_pattern = '|'.join(venues)
        meta_match = re.search(rf'(\d+)回({venue_pattern})(\d+)日', header_text)
        
        kai = '01'
        nichi = '01'
        
        if meta_match:
            kai = f"{int(meta_match.group(1)):02d}"
            metadata['会場'] = meta_match.group(2)
            nichi = f"{int(meta_match.group(3)):02d}"
        
        # レース番号
        race_num_match = re.search(r'(\d+)R', header_text)
        if race_num_match:
            race_num = f"{int(race_num_match.group(1)):02d}"
            metadata['レース番号'] = f"{race_num_match.group(1)}R"
        else:
            race_num = '10'
        
        # race_id生成
        place_map = {
            '札幌': '01', '函館': '02', '福島': '03', '新潟': '04', '東京': '05',
            '中山': '06', '中京': '07', '京都': '08', '阪神': '09', '小倉': '10'
        }
        place_code = place_map.get(metadata['会場'], '00')
        
        if date_match:
            metadata['race_id'] = f"{year}{place_code}{kai}{nichi}{race_num}"
        
        # 重賞
        if 'G1' in metadata['レース名'] or 'GⅠ' in metadata['レース名']:
            metadata['重賞'] = 'G1'
        elif 'G2' in metadata['レース名'] or 'GⅡ' in metadata['レース名']:
            metadata['重賞'] = 'G2'
        elif 'G3' in metadata['レース名'] or 'GⅢ' in metadata['レース名']:
            metadata['重賞'] = 'G3'
        
        # コースタイプ・距離
        course_match = re.search(r'(芝|ダート|ダ|障害)[^0-9]*(\d+)m', header_text)
        if course_match:
            course_type = course_match.group(1)
            if '芝' in course_type:
                metadata['コースタイプ'] = '芝'
            elif 'ダ' in course_type:
                metadata['コースタイプ'] = 'ダート'
            elif '障' in course_type:
                metadata['コースタイプ'] = '障害'
            metadata['距離'] = course_match.group(2)
        
        # 回り
        if '右' in header_text:
            metadata['回り'] = '右'
        elif '左' in header_text:
            metadata['回り'] = '左'
        elif '直線' in header_text or '直' in header_text:
            metadata['回り'] = '直線'
        
        # 天候
        weather_match = re.search(r'天候\s*[:：]\s*(\S+)', soup.text)
        if weather_match:
            metadata['天候'] = weather_match.group(1)
        
        # 馬場状態
        condition_match = re.search(r'(?:芝|ダート)\s*[:：]\s*(\S+)', soup.text)
        if condition_match:
            metadata['馬場状態'] = condition_match.group(1)
    
    except Exception as e:
        print(f"  ⚠️ メタデータ抽出エラー: {e}")
    
    return metadata

# テスト実行
def test_scraping(race_id):
    """1レースのテスト"""
    print(f"\n{'='*80}")
    print(f"🧪 テスト: {race_id}")
    print(f"{'='*80}\n")
    
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    # ページ取得
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # メタデータ抽出
    metadata = extract_metadata(soup, url)
    
    print("📊 メタデータ:")
    for key, value in metadata.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    # 欠損チェック
    missing = [k for k, v in metadata.items() if not v]
    if missing:
        print(f"\n⚠️  欠損: {missing}")
    else:
        print(f"\n✅ 全メタデータ取得成功")
    
    return metadata

if __name__ == "__main__":
    # JRAテスト
    print("🏇 JRA テスト")
    jra_metadata = test_scraping("202001010101")
    
    # NARテスト
    print("\n\n🏇 NAR テスト")
    nar_metadata = test_scraping("202030041501")
    
    print(f"\n{'='*80}")
    print("✅ テスト完了")
    print(f"{'='*80}")
