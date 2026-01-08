#!/usr/bin/env python3
"""
レースリストページのHTML構造を詳しく調査
"""

import requests
from bs4 import BeautifulSoup
import re

def analyze_race_list_html(date_str="20250105"):
    """レースリストページのHTML構造を分析"""
    print(f"🔍 Analyzing Race List HTML: {date_str}\n")
    
    base_domain = "race.netkeiba.com"
    list_url = f"https://{base_domain}/top/race_list.html?kaisai_date={date_str}"
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(list_url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. race_idを含む全てのリンクを探す
        print("=" * 60)
        print("1️⃣  Links containing 'race_id':")
        print("=" * 60)
        all_links = soup.find_all('a', href=True)
        race_id_links = [link for link in all_links if 'race_id' in link.get('href', '')]
        
        if race_id_links:
            for i, link in enumerate(race_id_links[:20], 1):
                href = link.get('href')
                text = link.get_text(strip=True)[:50]
                print(f"{i:2}. {href}")
                print(f"    Text: {text}")
                
                # race_idを抽出
                m = re.search(r'race_id=(\d+)', href)
                if m:
                    print(f"    ID: {m.group(1)}")
                print()
        else:
            print("⚠️  No links with 'race_id' found!\n")
        
        # 2. レース関連のクラスやIDを持つ要素を探す
        print("=" * 60)
        print("2️⃣  Elements with race-related classes:")
        print("=" * 60)
        
        # よくあるクラス名を探す
        race_classes = ['RaceList', 'Race_Item', 'RaceData', 'race-list', 'race_list']
        for cls in race_classes:
            elements = soup.find_all(class_=re.compile(cls, re.I))
            if elements:
                print(f"\nClass '{cls}': {len(elements)} elements found")
                for elem in elements[:3]:
                    print(f"  Tag: {elem.name}")
                    print(f"  Classes: {elem.get('class')}")
                    # 内部のリンクを探す
                    links = elem.find_all('a', href=True)
                    if links:
                        print(f"  Links: {len(links)}")
                        for link in links[:2]:
                            print(f"    - {link.get('href')}")
        
        # 3. HTMLの構造を表示(レース情報がありそうな部分)
        print("\n" + "=" * 60)
        print("3️⃣  HTML Structure Sample:")
        print("=" * 60)
        
        # bodyの中身を少し表示
        body = soup.find('body')
        if body:
            # レース情報がありそうなdivやtableを探す
            main_content = soup.find('div', class_=re.compile('main|content|race', re.I))
            if main_content:
                print("\nMain content area found:")
                print(str(main_content)[:2000])
            else:
                print("\nNo main content area found. Showing body sample:")
                print(str(body)[:2000])
        
        # 4. JavaScriptで動的に生成されている可能性をチェック
        print("\n" + "=" * 60)
        print("4️⃣  JavaScript Detection:")
        print("=" * 60)
        
        scripts = soup.find_all('script')
        print(f"Found {len(scripts)} script tags")
        
        for script in scripts:
            script_text = script.string or ''
            if 'race_id' in script_text:
                print("\n⚠️  Found 'race_id' in JavaScript!")
                print("This might indicate dynamic content loading.")
                # race_idを含む行を表示
                lines = script_text.split('\n')
                for line in lines:
                    if 'race_id' in line:
                        print(f"  {line.strip()[:100]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    analyze_race_list_html("20250105")
