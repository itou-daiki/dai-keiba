#!/usr/bin/env python3
"""
実際のレースページから全ての要素を詳細に分析
"""

import requests
from bs4 import BeautifulSoup
import re

def deep_analyze(race_id):
    """徹底的にHTML構造を分析"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    print(f"\n{'='*80}")
    print(f"🔍 徹底分析: {race_id}")
    print(f"{'='*80}\n")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 1. タイトルから情報抽出
    print("📝 ページタイトル:")
    title = soup.title.text if soup.title else ""
    print(f"  {title}\n")
    
    # タイトルから解析
    if title:
        # レース名
        race_name_match = re.search(r'^([^|]+)', title)
        if race_name_match:
            print(f"  レース名: {race_name_match.group(1).strip()}")
        
        # 日付
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title)
        if date_match:
            print(f"  日付: {date_match.group(0)}")
        
        # 会場
        venue_match = re.search(r'(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)', title)
        if venue_match:
            print(f"  会場: {venue_match.group(1)}")
        
        # レース番号
        race_num_match = re.search(r'(\d+)R', title)
        if race_num_match:
            print(f"  レース番号: {race_num_match.group(0)}")
    
    # 2. 全divクラスを列挙
    print("\n📝 主要なdivクラス:")
    for div in soup.find_all('div', class_=True)[:20]:
        classes = ' '.join(div.get('class', []))
        text = div.text.strip()[:50]
        if text:
            print(f"  .{classes}: {text}")
    
    # 3. データテーブル
    print("\n📝 データテーブル:")
    for elem in soup.select('dl.racedata, .race_otherdata, p.smalltxt'):
        print(f"  {elem.name}.{' '.join(elem.get('class', []))}: {elem.text.strip()[:100]}")
    
    # 4. 正規表現で全体から抽出
    print("\n📝 正規表現マッチ:")
    full_text = soup.text
    
    # 天候
    weather_match = re.search(r'天候\s*[:：]\s*(\S+)', full_text)
    if weather_match:
        print(f"  天候: {weather_match.group(1)}")
    
    # 馬場
    condition_match = re.search(r'馬場\s*[:：]\s*(\S+)', full_text)
    if condition_match:
        print(f"  馬場: {condition_match.group(1)}")
    
    # 芝/ダート状態
    turf_match = re.search(r'芝\s*[:：]\s*(\S+)', full_text)
    if turf_match:
        print(f"  芝: {turf_match.group(1)}")
    
    dirt_match = re.search(r'ダート\s*[:：]\s*(\S+)', full_text)
    if dirt_match:
        print(f"  ダート: {dirt_match.group(1)}")
    
    # コース
    course_match = re.search(r'(芝|ダート|ダ|障害)\s*(\d+)m', full_text)
    if course_match:
        print(f"  コース: {course_match.group(1)} {course_match.group(2)}m")
    
    # 回り
    if '右' in full_text:
        print(f"  回り: 右")
    elif '左' in full_text:
        print(f"  回り: 左")

if __name__ == "__main__":
    # 複数のrace_idでテスト
    test_ids = [
        "202001010101",  # 2020年 札幌
        "202405050811",  # 2024年 東京(より新しい)
        "202030041501",  # NAR
    ]
    
    for rid in test_ids:
        deep_analyze(rid)
