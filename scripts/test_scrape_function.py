#!/usr/bin/env python3
"""
JRA Basic v2のscrape_race_basic関数を直接テスト
"""

import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# ノートブックから関数を抽出
notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# メタデータ抽出関数とスクレイピング関数を取得
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def extract_metadata(' in source:
            exec(source)
            print("✅ Metadata extraction function loaded")
        if 'def scrape_race_basic(' in source:
            exec(source)
            print("✅ Scraping function loaded")

# テスト
race_id = "202001010201"
print(f"\n🧪 Testing race_id: {race_id}\n")

try:
    df = scrape_race_basic(race_id)
    
    if df is not None:
        print(f"✅ スクレイピング成功")
        print(f"   取得行数: {len(df)}")
        print(f"   カラム数: {len(df.columns)}")
        print(f"\n📊 最初の馬:")
        print(df[['馬名', '着順', 'corner_1', 'corner_2', 'corner_3', 'corner_4']].head(1))
    else:
        print(f"❌ スクレイピング失敗: Noneが返された")
        
except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
