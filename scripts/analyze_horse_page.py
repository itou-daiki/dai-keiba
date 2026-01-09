#!/usr/bin/env python3
"""
馬ページのHTML構造を分析
"""

import requests
from bs4 import BeautifulSoup

horse_id = "2018101626"
url = f"https://db.netkeiba.com/horse/{horse_id}/"

print(f"🔍 馬ページ分析: {url}\n")
print(f"{'='*80}\n")

headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers, timeout=15)
resp.encoding = 'EUC-JP'
soup = BeautifulSoup(resp.text, 'html.parser')

# 1. ページタイトル
print("📝 ページタイトル:")
print(f"  {soup.title.text if soup.title else 'なし'}\n")

# 2. 血統テーブル候補
print("📝 血統テーブル候補:")
for selector in ['table.blood_table', 'table.bloodTable', '.pedigree', 'table']:
    tables = soup.select(selector)
    if tables:
        print(f"  {selector}: {len(tables)}件")
        if len(tables) <= 3:
            for i, table in enumerate(tables):
                text = table.text.strip()[:100]
                print(f"    Table {i}: {text}")

# 3. レース結果テーブル候補
print(f"\n📝 レース結果テーブル候補:")
for selector in ['table.db_h_race_results', 'table.raceTable', '.race_results', 'table']:
    tables = soup.select(selector)
    if tables:
        print(f"  {selector}: {len(tables)}件")

# 4. 全テーブルのクラス名
print(f"\n📝 全テーブルのクラス名:")
all_tables = soup.find_all('table')
for i, table in enumerate(all_tables[:10]):
    classes = ' '.join(table.get('class', []))
    if classes:
        print(f"  Table {i}: class='{classes}'")
    else:
        print(f"  Table {i}: (クラスなし)")

# 5. テキスト検索
print(f"\n📝 重要なキーワード検索:")
keywords = ['父', '母', '母父', '血統', '着順', 'レース名', '日付']
for keyword in keywords:
    if keyword in soup.text:
        print(f"  ✅ '{keyword}' 見つかりました")
    else:
        print(f"  ❌ '{keyword}' 見つかりません")
