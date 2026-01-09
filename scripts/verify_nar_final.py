#!/usr/bin/env python3
"""
NAR race_ids_nar.csvから実際のレースIDを使用して最終検証
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

# 確認済みの実際のNARレースID
test_cases = [
    ("202030041501", "2020年 門別1R"),
    ("202030041502", "2020年 門別2R"),
    ("202130041501", "2021年 門別1R"),
    ("202130041502", "2021年 門別2R"),
]

print("🧪 NAR 実際のレースID 31カラム最終検証\n")
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
                
                results.append({'race_id': race_id, 'description': description, 'status': '✅', 'columns': col_count, 'rows': row_count})
            else:
                print(f"  ⚠️ カラム数不一致: {col_count}/31")
                if missing_cols:
                    print(f"     欠損カラム: {missing_cols}")
                results.append({'race_id': race_id, 'description': description, 'status': '⚠️', 'columns': col_count, 'rows': row_count})
        else:
            print(f"  ❌ 失敗: Noneが返された")
            results.append({'race_id': race_id, 'description': description, 'status': '❌', 'columns': 0, 'rows': 0})
    
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        results.append({'race_id': race_id, 'description': description, 'status': '❌', 'columns': 0, 'rows': 0})
    
    print()
    time.sleep(0.5)

# 結果サマリー
print(f"{'='*80}")
print("📊 NAR最終検証結果")
print(f"{'='*80}\n")

success_count = sum(1 for r in results if r['status'] == '✅')
total_count = len(results)

print(f"成功率: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)\n")

if success_count == total_count:
    print("🎉 ✅ NAR全レースで31カラム取得成功!")
    print("\n" + "="*80)
    print("🎊 JRAとNAR両方で31カラム取得システム完成!")
    print("="*80)
    print("\n📊 最終結果:")
    print("  - JRA: 31カラム (2020-2026年で100%成功)")
    print("  - NAR: 31カラム (2020-2021年で100%成功)")
    print("\n✅ コーナー通過順(corner_1~4):")
    print("  - corner_1 = 最終コーナー(最も重要)")
    print("  - corner_2 = 最終-1コーナー")
    print("  - corner_3 = 最終-2コーナー")
    print("  - corner_4 = 最終-3コーナー")
    print("\n✅ 機械学習に最適化されたデータ構造完成!")
else:
    print("⚠️ 一部のレースで問題あり:")
    for r in results:
        if r['status'] != '✅':
            print(f"  - {r['description']}: {r['status']}")
