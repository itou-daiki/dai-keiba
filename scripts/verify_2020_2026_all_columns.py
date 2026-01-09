#!/usr/bin/env python3
"""
2020-2026年のレースで31カラム全取得を検証
各年から複数レースをサンプリング
"""

import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# ノートブックから関数を読み込み
notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def extract_metadata(' in source:
            exec(source)
        if 'def scrape_race_basic(' in source:
            exec(source)

print("✅ 関数読み込み完了\n")

# テストケース: 2020-2026年の各年から1レースずつ
test_cases = [
    ("202001010201", "2020年 札幌1R"),
    ("202101010101", "2021年 札幌1R"),
    ("202201010101", "2022年 札幌1R"),
    ("202301010101", "2023年 札幌1R"),
    ("202401010101", "2024年 札幌1R"),
    ("202405050511", "2024年 東京11R"),
    ("202406050811", "2024年 有馬記念"),
]

print("🧪 2020-2026年 31カラム取得検証\n")
print(f"{'='*80}\n")

results = []

for race_id, description in test_cases:
    print(f"📊 {description} (ID: {race_id})")
    
    try:
        df = scrape_race_basic(race_id)
        
        if df is not None:
            col_count = len(df.columns)
            row_count = len(df)
            
            # 必須カラムの確認
            required_cols = ['日付', '会場', '馬名', 'corner_1', 'corner_2', 'corner_3', 'corner_4']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if col_count == 31 and not missing_cols:
                print(f"  ✅ 成功: {col_count}カラム, {row_count}頭")
                
                # corner_1の取得状況
                corner_filled = df['corner_1'].notna().sum() + (df['corner_1'] != '').sum()
                print(f"     corner_1取得: {corner_filled}/{row_count}頭")
                
                results.append({
                    'race_id': race_id,
                    'description': description,
                    'status': '✅',
                    'columns': col_count,
                    'rows': row_count
                })
            else:
                print(f"  ⚠️ カラム数不一致: {col_count}/31")
                if missing_cols:
                    print(f"     欠損カラム: {missing_cols}")
                results.append({
                    'race_id': race_id,
                    'description': description,
                    'status': '⚠️',
                    'columns': col_count,
                    'rows': row_count
                })
        else:
            print(f"  ❌ 失敗: Noneが返された")
            results.append({
                'race_id': race_id,
                'description': description,
                'status': '❌',
                'columns': 0,
                'rows': 0
            })
    
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        results.append({
            'race_id': race_id,
            'description': description,
            'status': '❌',
            'columns': 0,
            'rows': 0
        })
    
    print()
    time.sleep(0.5)

# 結果サマリー
print(f"{'='*80}")
print("📊 検証結果サマリー")
print(f"{'='*80}\n")

success_count = sum(1 for r in results if r['status'] == '✅')
total_count = len(results)

print(f"成功率: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)\n")

if success_count == total_count:
    print("✅ 全レースで31カラム取得成功!")
else:
    print("⚠️ 一部のレースで問題あり:")
    for r in results:
        if r['status'] != '✅':
            print(f"  - {r['description']}: {r['status']}")
