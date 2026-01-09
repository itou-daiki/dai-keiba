#!/usr/bin/env python3
"""
複数のレースIDでランダムテスト
"""

import json
import requests
from bs4 import BeautifulSoup
import re
import time

# ノートブックから関数を抽出
notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

extract_metadata_code = None
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def extract_metadata(' in source:
            extract_metadata_code = source
            break

exec(extract_metadata_code)

# テスト用のrace_idリスト(様々な年・会場・レース)
test_ids = [
    "202001010101",  # 2020年 札幌 1R
    "202105050811",  # 2021年 東京 11R
    "202206060505",  # 2022年 中山 5R
    "202309090909",  # 2023年 阪神 9R
    "202410100303",  # 2024年 小倉 3R
    "202406050811",  # 2024年 中山 11R (有馬記念)
    "202405010111",  # 2024年 札幌 11R
    "202404040707",  # 2024年 新潟 7R
    "202003030202",  # 2020年 福島 2R
    "202107070606",  # 2021年 中京 6R
]

print(f"🎲 ランダムテスト: {len(test_ids)}レース\n")
print(f"{'='*80}\n")

results = []

for i, race_id in enumerate(test_ids, 1):
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    try:
        time.sleep(0.5)  # レート制限対策
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        metadata = extract_metadata(soup, url)
        
        # 統計
        filled = sum(1 for v in metadata.values() if v)
        total = len(metadata)
        rate = filled / total * 100
        
        print(f"{i}. {race_id}")
        print(f"   成功率: {rate:.0f}% ({filled}/{total})")
        
        # 欠損カラムを表示
        missing = [k for k, v in metadata.items() if not v]
        if missing:
            print(f"   欠損: {', '.join(missing)}")
        else:
            print(f"   ✅ 完璧!")
        
        # 主要情報を表示
        date = metadata.get('日付', '')
        venue = metadata.get('会場', '')
        race_num = metadata.get('レース番号', '')
        race_name = metadata.get('レース名', '')[:25]
        grade = f" [{metadata.get('重賞', '')}]" if metadata.get('重賞') else ""
        
        print(f"   {date} {venue} {race_num} {race_name}{grade}")
        print()
        
        results.append({
            'race_id': race_id,
            'success_rate': rate,
            'filled': filled,
            'missing_count': len(missing),
            'missing': missing
        })
        
    except Exception as e:
        print(f"{i}. {race_id}")
        print(f"   ❌ エラー: {e}\n")
        results.append({
            'race_id': race_id,
            'success_rate': 0,
            'filled': 0,
            'missing_count': 11,
            'missing': ['error']
        })

# 統計サマリー
print(f"{'='*80}")
print("📊 統計サマリー")
print(f"{'='*80}\n")

valid_results = [r for r in results if r['success_rate'] > 0]

if valid_results:
    avg_rate = sum(r['success_rate'] for r in valid_results) / len(valid_results)
    perfect_count = sum(1 for r in valid_results if r['success_rate'] == 100)
    good_count = sum(1 for r in valid_results if r['success_rate'] >= 90)
    
    print(f"テスト件数: {len(valid_results)}/{len(results)}")
    print(f"平均成功率: {avg_rate:.1f}%")
    print(f"完璧(100%): {perfect_count}/{len(valid_results)} ({perfect_count/len(valid_results)*100:.0f}%)")
    print(f"良好(90%+): {good_count}/{len(valid_results)} ({good_count/len(valid_results)*100:.0f}%)")
    
    # 最も多い欠損カラム
    all_missing = []
    for r in valid_results:
        all_missing.extend(r['missing'])
    
    if all_missing:
        from collections import Counter
        missing_counter = Counter(all_missing)
        print(f"\n最も多い欠損カラム:")
        for col, count in missing_counter.most_common(5):
            pct = count / len(valid_results) * 100
            print(f"  {col}: {count}回 ({pct:.0f}%)")
