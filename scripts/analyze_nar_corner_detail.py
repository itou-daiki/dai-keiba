#!/usr/bin/env python3
"""
NAR コーナー通過順の詳細分析
レース結果ページの全体構造を確認
"""

import requests
from bs4 import BeautifulSoup

race_id = "202030041501"
url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"

print(f"🔍 NAR コーナー通過順の詳細分析")
print(f"{'='*80}\n")
print(f"Race ID: {race_id}")
print(f"URL: {url}\n")

headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers, timeout=15)
resp.encoding = 'EUC-JP'
soup = BeautifulSoup(resp.text, 'html.parser')

# 全テーブルを確認
tables = soup.find_all('table')
print(f"📊 テーブル数: {len(tables)}\n")

for i, table in enumerate(tables):
    print(f"テーブル{i+1}:")
    print(f"{'-'*80}")
    
    # テーブルのテキストの一部を表示
    text = table.text.strip()[:200]
    print(f"  内容: {text}...")
    
    # ヘッダー確認
    headers_cells = table.find_all('th')
    if headers_cells:
        print(f"  ヘッダー: {[th.text.strip() for th in headers_cells[:10]]}")
    
    # コーナー関連のキーワード検索
    if 'コーナー' in table.text or '通過' in table.text:
        print(f"  ✅ コーナー関連あり")
    
    print()

# ページ全体でコーナー関連のテキストを検索
print(f"\n{'='*80}")
print(f"📊 ページ全体でのコーナー関連キーワード検索:")
print(f"{'='*80}\n")

full_text = soup.text

keywords = ['コーナー', '通過順', '1コーナー', '2コーナー', '3コーナー', '4コーナー']
for keyword in keywords:
    if keyword in full_text:
        # キーワード周辺のテキストを抽出
        index = full_text.find(keyword)
        context = full_text[max(0, index-50):min(len(full_text), index+100)]
        print(f"✅ '{keyword}' 発見:")
        print(f"   {context.strip()}")
        print()
