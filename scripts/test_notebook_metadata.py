#!/usr/bin/env python3
"""
ノートブックから直接関数を抽出してテスト
"""

import json
import requests
from bs4 import BeautifulSoup
import re

# ノートブックから関数を抽出
notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# メタデータ抽出関数のコードを取得
extract_metadata_code = None
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def extract_metadata(' in source:
            extract_metadata_code = source
            break

if not extract_metadata_code:
    print("❌ 関数が見つかりません")
    exit(1)

# 関数を実行環境に読み込み
exec(extract_metadata_code)

# テスト実行
def test_race(race_id):
    """1レースをテスト"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    
    print(f"\n{'='*80}")
    print(f"🧪 テスト: {race_id}")
    print(f"{'='*80}\n")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'EUC-JP'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # メタデータ抽出
    metadata = extract_metadata(soup, url)
    
    print("📊 抽出結果:")
    for key, value in metadata.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    # 統計
    missing = [k for k, v in metadata.items() if not v]
    success_count = 11 - len(missing)
    success_rate = success_count / 11 * 100
    
    print(f"\n📈 成功率: {success_rate:.0f}% ({success_count}/11)")
    
    if missing:
        print(f"⚠️  欠損: {missing}")
    else:
        print(f"✅ 全メタデータ取得成功!")
    
    return success_count == 11

if __name__ == "__main__":
    print("🏇 JRA Basic v2 ノートブックのテスト\n")
    
    # テストケース
    test_cases = [
        ("202001010101", "2020年 札幌 通常レース"),
        ("202406050811", "2024年 中山 重賞レース(有馬記念)"),
    ]
    
    results = []
    for race_id, description in test_cases:
        print(f"\n📝 {description}")
        success = test_race(race_id)
        results.append((description, success))
    
    # 最終結果
    print(f"\n{'='*80}")
    print("📊 最終結果")
    print(f"{'='*80}\n")
    
    for desc, success in results:
        status = "✅" if success else "⚠️"
        print(f"  {status} {desc}")
    
    all_success = all(r[1] for r in results)
    if all_success:
        print(f"\n🎉 全テスト成功! ノートブックは正常に動作します")
    else:
        print(f"\n⚠️  一部のテストで欠損があります")
