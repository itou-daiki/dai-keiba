#!/usr/bin/env python3
"""
NAR用メタデータ抽出関数のテスト
"""

import requests
from bs4 import BeautifulSoup
import re

def extract_nar_metadata(soup, url):
    """NAR用メタデータ抽出"""
    metadata = {
        '日付': '', '会場': '', 'レース番号': '', 'レース名': '', '重賞': '',
        'コースタイプ': '', '距離': '', '回り': '', '天候': '', '馬場状態': '', 'race_id': ''
    }
    
    try:
        title = soup.title.text if soup.title else ""
        full_text = soup.text
        
        print(f"タイトル: {title}\n")
        
        if title:
            # レース名(タイトルの最初の部分)
            race_name_match = re.search(r'^([^|]+)', title)
            if race_name_match:
                race_name_full = race_name_match.group(1).strip()
                race_name = re.sub(r'\s*(結果|払戻|払い戻し).*$', '', race_name_full).strip()
                metadata['レース名'] = race_name
                print(f"✅ レース名: {race_name}")
            
            # 日付(タイトルから)
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title)
            if date_match:
                year = date_match.group(1)
                month = f"{int(date_match.group(2)):02d}"
                day = f"{int(date_match.group(3)):02d}"
                metadata['日付'] = f"{year}/{month}/{day}"
                print(f"✅ 日付: {metadata['日付']}")
            
            # 会場(NAR会場リスト)
            nar_venues = [
                '門別', '盛岡', '水沢', '浦和', '船橋', '大井', '川崎', '金沢', 
                '笠松', '名古屋', '園田', '姫路', '高知', '佐賀', 'ばんえい帯広'
            ]
            for venue in nar_venues:
                if venue in title:
                    metadata['会場'] = venue
                    print(f"✅ 会場: {venue}")
                    break
            
            # レース番号
            race_num_match = re.search(r'(\d+)R', title)
            if race_num_match:
                metadata['レース番号'] = race_num_match.group(0)
                print(f"✅ レース番号: {metadata['レース番号']}")
        
        # 本文から
        # コースタイプ・距離
        course_match = re.search(r'(芝|ダート|ダ)\s*(\d+)m', full_text)
        if course_match:
            course_type = course_match.group(1)
            metadata['コースタイプ'] = '芝' if '芝' in course_type else 'ダート'
            metadata['距離'] = course_match.group(2)
            print(f"✅ コース: {metadata['コースタイプ']} {metadata['距離']}m")
        else:
            # NAR特有のパターン
            # 「ダ1200m」のような表記を探す
            course_match2 = re.search(r'(ダ)(\d{3,4})', full_text)
            if course_match2:
                metadata['コースタイプ'] = 'ダート'
                metadata['距離'] = course_match2.group(2)
                print(f"✅ コース(NAR): {metadata['コースタイプ']} {metadata['距離']}m")
        
        # 天候
        weather_match = re.search(r'天候\s*[:：]?\s*(\S+)', full_text)
        if weather_match:
            metadata['天候'] = weather_match.group(1)
            print(f"✅ 天候: {metadata['天候']}")
        
        # 馬場状態
        baba_match = re.search(r'馬場\s*[:：]?\s*(\S+)', full_text)
        if baba_match:
            metadata['馬場状態'] = baba_match.group(1)
            print(f"✅ 馬場状態: {metadata['馬場状態']}")
        
        # race_id(URLから)
        race_id_match = re.search(r'race_id=(\d+)', url)
        if race_id_match:
            metadata['race_id'] = race_id_match.group(1)
            print(f"✅ race_id: {metadata['race_id']}")
        
        return metadata
    
    except Exception as e:
        print(f"❌ エラー: {e}")
        return metadata

# テスト
if __name__ == "__main__":
    race_id = '202030041501'
    url = f'https://nar.netkeiba.com/race/result.html?race_id={race_id}'
    
    print(f"🧪 NAR メタデータ抽出テスト")
    print(f"{'='*80}\n")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    metadata = extract_nar_metadata(soup, url)
    
    print(f"\n{'='*80}")
    print(f"📊 抽出結果:")
    for key, value in metadata.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    filled = sum(1 for v in metadata.values() if v)
    print(f"\n成功率: {filled}/11 ({filled/11*100:.0f}%)")
