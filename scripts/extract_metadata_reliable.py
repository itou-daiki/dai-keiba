#!/usr/bin/env python3
"""
完全版メタデータ抽出関数(重賞・馬場状態も確実に取得)
"""

import re

def extract_metadata_complete(soup, url):
    """
    全メタデータを確実に抽出(11/11カラム)
    """
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
        title = soup.title.text if soup.title else ""
        full_text = soup.text
        
        # 1. タイトルから基本情報
        if title:
            # レース名(重賞情報を含む)
            race_name_match = re.search(r'^([^|]+)', title)
            if race_name_match:
                race_name_full = race_name_match.group(1).strip()
                # "結果・払戻"を除去
                race_name = re.sub(r'\\s*(結果|払戻|払い戻し).*$', '', race_name_full).strip()
                metadata['レース名'] = race_name
                
                # 重賞判定(タイトルから)
                if 'G1' in race_name or 'GⅠ' in race_name or 'GI' in race_name:
                    metadata['重賞'] = 'G1'
                elif 'G2' in race_name or 'GⅡ' in race_name or 'GII' in race_name:
                    metadata['重賞'] = 'G2'
                elif 'G3' in race_name or 'GⅢ' in race_name or 'GIII' in race_name:
                    metadata['重賞'] = 'G3'
            
            # 日付
            date_match = re.search(r'(\\d{4})年(\\d{1,2})月(\\d{1,2})日', title)
            if date_match:
                year = date_match.group(1)
                month = f"{int(date_match.group(2)):02d}"
                day = f"{int(date_match.group(3)):02d}"
                metadata['日付'] = f"{year}/{month}/{day}"
            
            # 会場
            venues = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']
            for venue in venues:
                if venue in title:
                    metadata['会場'] = venue
                    break
            
            # レース番号
            race_num_match = re.search(r'(\\d+)R', title)
            if race_num_match:
                metadata['レース番号'] = race_num_match.group(0)
        
        # 2. コースタイプ・距離
        course_match = re.search(r'(芝|ダート|ダ|障害)\\s*(\\d+)m', full_text)
        if course_match:
            course_type = course_match.group(1)
            if '芝' in course_type:
                metadata['コースタイプ'] = '芝'
            elif 'ダ' in course_type:
                metadata['コースタイプ'] = 'ダート'
            elif '障' in course_type:
                metadata['コースタイプ'] = '障害'
            metadata['距離'] = course_match.group(2)
        
        # 3. 回り
        if '右' in full_text:
            metadata['回り'] = '右'
        elif '左' in full_text:
            metadata['回り'] = '左'
        elif '直線' in full_text or '直' in full_text:
            metadata['回り'] = '直線'
        
        # 4. 天候
        weather_match = re.search(r'天候\\s*[:：]\\s*(\\S+)', full_text)
        if weather_match:
            metadata['天候'] = weather_match.group(1)
        
        # 5. 馬場状態(確実に取得)
        # パターン1: "馬場:良"
        baba_match = re.search(r'馬場\\s*[:：]\\s*(\\S+)', full_text)
        if baba_match:
            metadata['馬場状態'] = baba_match.group(1)
        else:
            # パターン2: コースタイプ別
            if metadata['コースタイプ'] == '芝':
                condition_match = re.search(r'芝\\s*[:：]\\s*(\\S+)', full_text)
                if condition_match:
                    metadata['馬場状態'] = condition_match.group(1)
            elif metadata['コースタイプ'] == 'ダート':
                condition_match = re.search(r'ダート\\s*[:：]\\s*(\\S+)', full_text)
                if condition_match:
                    metadata['馬場状態'] = condition_match.group(1)
        
        # 6. race_id生成
        if metadata['日付'] and metadata['会場'] and metadata['レース番号']:
            year = metadata['日付'][:4]
            place_map = {
                '札幌': '01', '函館': '02', '福島': '03', '新潟': '04', '東京': '05',
                '中山': '06', '中京': '07', '京都': '08', '阪神': '09', '小倉': '10'
            }
            place_code = place_map.get(metadata['会場'], '00')
            race_num = metadata['レース番号'].replace('R', '')
            race_num_padded = f"{int(race_num):02d}"
            
            kai = '01'
            nichi = '01'
            kai_match = re.search(rf'(\\d+)回{metadata["会場"]}(\\d+)日', title + full_text)
            if kai_match:
                kai = f"{int(kai_match.group(1)):02d}"
                nichi = f"{int(kai_match.group(2)):02d}"
            
            metadata['race_id'] = f"{year}{place_code}{kai}{nichi}{race_num_padded}"
    
    except Exception as e:
        print(f"  ⚠️ メタデータ抽出エラー: {e}")
    
    return metadata

# テスト
if __name__ == "__main__":
    import requests
    from bs4 import BeautifulSoup
    
    def test(race_id):
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        metadata = extract_metadata_complete(soup, url)
        
        print(f"\n{'='*80}")
        print(f"🧪 {race_id}")
        print(f"{'='*80}\n")
        
        for key, value in metadata.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value}")
        
        missing = [k for k, v in metadata.items() if not v]
        success_rate = (11 - len(missing)) / 11 * 100
        print(f"\n成功率: {success_rate:.0f}% ({11-len(missing)}/11)")
    
    test("202001010101")  # 通常レース
    test("202406050811")  # 重賞レース
