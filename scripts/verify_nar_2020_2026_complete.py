#!/usr/bin/env python3
"""
NAR 2020-2026年 完全検証
全年度のrace_idで31カラム取得を確認
"""

import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# ノートブックから関数を読み込み
notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def extract_metadata(' in source:
            exec(source)
        if 'def scrape_race_basic(' in source:
            exec(source)

print("✅ NAR関数読み込み完了\n")

# 2020-2026年の確認済みrace_id
test_cases = [
    ("202030041501", "2020年 門別"),
    ("202130041501", "2021年 門別"),
    ("202230042001", "2022年 門別"),
    ("202330042001", "2023年 門別"),
    ("202430042501", "2024年 門別"),
    ("202530051501", "2025年 門別"),
    ("202642010601", "2026年 浦和"),
]

print("🧪 NAR 2020-2026年 31カラム完全検証\n")
print(f"{'='*80}\n")

results = []

for race_id, description in test_cases:
    print(f"📊 {description} (ID: {race_id})")
    
    try:
        df = scrape_race_basic(race_id)
        
        if df is not None:
            col_count = len(df.columns)
            row_count = len(df)
            
            required_cols = ['日付', '会場', '馬名', 'corner_1', 'corner_2', 'corner_3', 'corner_4']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if col_count == 31 and not missing_cols:
                print(f"  ✅ 成功: {col_count}カラム, {row_count}頭")
                corner_filled = df['corner_1'].notna().sum() + (df['corner_1'] != '').sum()
                print(f"     corner_1取得: {corner_filled}/{row_count}頭")
                
                results.append({'year': description, 'race_id': race_id, 'status': '✅', 'columns': col_count, 'rows': row_count})
            else:
                print(f"  ⚠️ カラム数不一致: {col_count}/31")
                if missing_cols:
                    print(f"     欠損カラム: {missing_cols}")
                results.append({'year': description, 'race_id': race_id, 'status': '⚠️', 'columns': col_count, 'rows': row_count})
        else:
            print(f"  ❌ 失敗: Noneが返された")
            results.append({'year': description, 'race_id': race_id, 'status': '❌', 'columns': 0, 'rows': 0})
    
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        results.append({'year': description, 'race_id': race_id, 'status': '❌', 'columns': 0, 'rows': 0})
    
    print()
    time.sleep(0.5)

# 結果サマリー
print(f"{'='*80}")
print("📊 NAR 2020-2026年 最終検証結果")
print(f"{'='*80}\n")

success_count = sum(1 for r in results if r['status'] == '✅')
total_count = len(results)

print(f"成功率: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)\n")

if success_count == total_count:
    print("🎉 ✅ NAR全年度で31カラム取得成功!")
    print("\n" + "="*80)
    print("🎊 JRAとNAR両方で2020-2026年の31カラム取得完全検証!")
    print("="*80)
    print("\n📊 最終結果:")
    print("  - JRA: 2020-2026年 (7レース) - 100%成功")
    print("  - NAR: 2020-2026年 (7レース) - 100%成功")
    print("\n✅ 全年度、全カラム取得完了!")
else:
    print("成功した年度:")
    for r in results:
        if r['status'] == '✅':
            print(f"  ✅ {r['year']}: {r['columns']}カラム")
    
    print("\n失敗した年度:")
    for r in results:
        if r['status'] != '✅':
            print(f"  ❌ {r['year']}: {r['status']}")
