#!/usr/bin/env python3
"""
JRAレース結果テーブル検出の検証
実際のレースIDでテーブル検出ロジックをテスト
"""

import requests
from bs4 import BeautifulSoup

def test_table_detection(race_id, description):
    """レース結果テーブルの検出をテスト"""
    
    print(f"\n{'='*80}")
    print(f"🔍 {description}")
    print(f"{'='*80}\n")
    print(f"Race ID: {race_id}\n")
    
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 全テーブルを取得
        tables = soup.find_all('table')
        print(f"📊 総テーブル数: {len(tables)}\n")
        
        # 各テーブルをチェック
        for i, table in enumerate(tables):
            text_sample = table.text.strip()[:100]
            has_chakujun = '着順' in table.text
            has_umamei = '馬名' in table.text
            
            print(f"テーブル{i+1}:")
            print(f"  着順: {'✅' if has_chakujun else '❌'}")
            print(f"  馬名: {'✅' if has_umamei else '❌'}")
            print(f"  サンプル: {text_sample}...")
            
            if has_chakujun and has_umamei:
                print(f"  ✅ レース結果テーブル候補")
            print()
        
        # 現在のロジックでテーブルを検出
        result_table = None
        for table in tables:
            if '着順' in table.text and '馬名' in table.text:
                result_table = table
                break
        
        if result_table:
            print(f"✅ レース結果テーブル検出成功")
            rows = result_table.find_all('tr')
            print(f"   行数: {len(rows)}")
        else:
            print(f"❌ レース結果テーブル検出失敗")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

# テストケース
print("🧪 JRAレース結果テーブル検出検証\n")

test_cases = [
    ("202406050811", "有馬記念(正常なレース)"),
    ("202405050511", "東京11R(正常なレース)"),
    ("202401010101", "札幌1R(正常なレース)"),
    ("202400000000", "存在しないレース"),
    ("202406050812", "次のレース"),
]

for race_id, desc in test_cases:
    test_table_detection(race_id, desc)

print(f"\n{'='*80}")
print("✅ 検証完了")
print(f"{'='*80}")
