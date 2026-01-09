#!/usr/bin/env python3
"""
JRA Basic v2ノートブックを完全に再構築
31カラム(27 + corner_1~4)を確実に取得
"""

import json
import re

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

print("🔧 JRA Basic v2ノートブック再構築\n")
print(f"{'='*80}\n")

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def scrape_race_basic(' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見\n")
            
            # 1. ordered_columnsを31カラムに修正
            # 既存のordered_columnsを探して置換
            columns_pattern = r"ordered_columns = \[(.*?)\]"
            match = re.search(columns_pattern, source, re.DOTALL)
            
            if match:
                print("📝 Step 1: ordered_columnsを31カラムに更新")
                
                new_ordered_columns = """ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', 'コーナー通過順', 'corner_1', 'corner_2', 'corner_3', 'corner_4',
            '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]"""
                
                source = re.sub(columns_pattern, new_ordered_columns, source, flags=re.DOTALL)
                print("  ✅ 31カラムに更新\n")
            
            # 2. 辞書初期化部分を修正
            print("📝 Step 2: 辞書初期化にcorner_1~4を追加")
            
            # horse_data辞書の構築部分を探す
            if "'コーナー通過順':" in source:
                # コーナー通過順の後にcorner_1~4を追加
                old_pattern = r"('コーナー通過順': cells\[12\]\.text\.strip\(\) if len\(cells\) > 12 else '',\s*'厩舎':)"
                new_replacement = r"'コーナー通過順': cells[12].text.strip() if len(cells) > 12 else '',\n                'corner_1': '',\n                'corner_2': '',\n                'corner_3': '',\n                'corner_4': '',\n                '厩舎':"
                
                source = re.sub(old_pattern, new_replacement, source)
                print("  ✅ corner_1~4を辞書に追加\n")
            
            # 3. コーナー抽出ロジックを追加
            print("📝 Step 3: コーナー抽出ロジック(逆順)を追加")
            
            # horse_idの後、race_data.append()の前に挿入
            if "race_data.append(horse_data)" in source:
                old_append = r"(\s+)race_data\.append\(horse_data\)"
                new_append = r"""\1# コーナー通過順の個別カラム抽出(最終から逆順)
\1corner_text = cells[12].text.strip() if len(cells) > 12 else ''
\1if corner_text and '-' in corner_text:
\1    positions = corner_text.split('-')
\1    for j, pos in enumerate(reversed(positions)):
\1        if j < 4:
\1            horse_data[f'corner_{j+1}'] = pos.strip()
\1
\1race_data.append(horse_data)"""
                
                source = re.sub(old_append, new_append, source)
                print("  ✅ 逆順抽出ロジックを追加\n")
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"{'='*80}")
print(f"💾 保存完了: {notebook_path}\n")
print("📊 最終構成:")
print("  - 総カラム数: 31")
print("  - メタデータ: 11カラム")
print("  - 馬データ: 16カラム")
print("  - コーナー: 4カラム (corner_1~4, 最終から逆順)")
print("  - ID: 2カラム (race_id, horse_id)")
