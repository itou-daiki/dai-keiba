#!/usr/bin/env python3
"""
修正後の枠・厩舎取得をテスト
"""

import json
import requests
from bs4 import BeautifulSoup
import re

# ノートブックから関数を抽出してテスト
notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# メタデータ抽出関数とスクレイピング関数を取得
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def extract_metadata(' in source or 'def scrape_race_basic(' in source:
            exec(source)

# テスト
race_id = "202406050811"
print(f"🧪 枠・厩舎取得テスト (JRA)")
print(f"{'='*80}\n")
print(f"Race ID: {race_id}\n")

df = scrape_race_basic(race_id)

if df is not None:
    print(f"✅ スクレイピング成功: {len(df)}頭\n")
    
    # 枠と厩舎の取得状況
    waku_filled = df['枠'].notna().sum() + (df['枠'] != '').sum()
    stable_filled = df['厩舎'].notna().sum() + (df['厩舎'] != '').sum()
    
    print(f"📊 取得状況:")
    print(f"  枠: {waku_filled}/{len(df)} ({waku_filled/len(df)*100:.0f}%)")
    print(f"  厩舎: {stable_filled}/{len(df)} ({stable_filled/len(df)*100:.0f}%)\n")
    
    # サンプル表示
    print(f"📊 サンプルデータ(最初の3頭):")
    print(df[['馬名', '枠', '厩舎']].head(3).to_string(index=False))
    
    if waku_filled == len(df) and stable_filled == len(df):
        print(f"\n✅ 枠・厩舎ともに100%取得成功!")
    else:
        print(f"\n⚠️ 一部欠損あり")
else:
    print(f"❌ スクレイピング失敗")
