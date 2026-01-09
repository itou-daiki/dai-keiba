#!/usr/bin/env python3
"""
重賞と馬場状態の情報を探す
"""

import requests
from bs4 import BeautifulSoup
import re

def find_grade_and_condition(race_id):
    """重賞と馬場状態の情報を徹底的に探す"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    print(f"\n{'='*80}")
    print(f"🔍 分析: {race_id}")
    print(f"{'='*80}\n")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    full_text = soup.text
    
    # 1. 重賞情報
    print("📝 重賞情報:")
    
    # パターン1: レース名に含まれる
    title = soup.title.text if soup.title else ""
    print(f"  タイトル: {title}")
    
    if 'G1' in title or 'GⅠ' in title or 'GI' in title:
        print(f"  ✅ 重賞: G1 (タイトルから)")
    elif 'G2' in title or 'GⅡ' in title or 'GII' in title:
        print(f"  ✅ 重賞: G2 (タイトルから)")
    elif 'G3' in title or 'GⅢ' in title or 'GIII' in title:
        print(f"  ✅ 重賞: G3 (タイトルから)")
    else:
        print(f"  ❌ 重賞: なし (タイトルから)")
    
    # パターン2: 本文から
    grade_patterns = [
        r'(G[IⅠ123])',
        r'(重賞)',
        r'(オープン)',
    ]
    
    for pattern in grade_patterns:
        matches = re.findall(pattern, full_text)
        if matches:
            print(f"  パターン '{pattern}': {set(matches)}")
    
    # 2. 馬場状態
    print("\n📝 馬場状態:")
    
    # パターン1: "芝:良" "ダート:稍重"
    condition_patterns = [
        r'芝\s*[:：]\s*(\S+)',
        r'ダート\s*[:：]\s*(\S+)',
        r'馬場\s*[:：]\s*(\S+)',
        r'馬場状態\s*[:：]\s*(\S+)',
    ]
    
    for pattern in condition_patterns:
        match = re.search(pattern, full_text)
        if match:
            print(f"  ✅ パターン '{pattern}': {match.group(1)}")
    
    # パターン2: HTMLタグから
    for selector in ['dd.baba', '.race_otherdata dd', 'span.turf', 'span.dirt']:
        elem = soup.select_one(selector)
        if elem:
            print(f"  ✅ セレクタ '{selector}': {elem.text.strip()}")
    
    # 3. 全体から関連テキストを抽出
    print("\n📝 関連テキスト:")
    lines = full_text.split('\n')
    for line in lines:
        if any(keyword in line for keyword in ['芝', 'ダート', '馬場', '良', '稍重', '重', '不良']):
            clean_line = line.strip()
            if clean_line and len(clean_line) < 100:
                print(f"  {clean_line}")

if __name__ == "__main__":
    # JRA(通常レース)
    find_grade_and_condition("202001010101")
    
    # JRA(重賞レース - 例: 有馬記念)
    find_grade_and_condition("202406050811")
