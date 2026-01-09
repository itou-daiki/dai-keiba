#!/usr/bin/env python3
"""
修正されたNAR Basic v2ノートブックのテスト
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# ノートブックから関数を抽出
import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# メタデータ抽出関数を取得
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def extract_metadata(' in source:
            exec(source)
            break

# テスト用NAR race_id
test_race_ids = [
    ("202030041501", "2020年 門別1R"),
    ("202130041501", "2021年 門別1R"),
]

print("🧪 NAR Basic v2 修正版テスト\n")
print(f"{'='*80}\n")

for race_id, description in test_race_ids:
    url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"
    
    print(f"🏇 {description} (ID: {race_id})")
    print(f"{'-'*80}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        metadata = extract_metadata(soup, url)
        
        print(f"📊 抽出結果:")
        for key, value in metadata.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value}")
        
        filled = sum(1 for v in metadata.values() if v)
        rate = filled / 11 * 100
        print(f"\n成功率: {rate:.0f}% ({filled}/11)")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    print()
