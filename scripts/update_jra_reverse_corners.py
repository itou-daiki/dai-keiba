#!/usr/bin/env python3
"""
JRA Basic v2を逆順コーナー抽出に更新
"""

import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def scrape_race_basic(' in source and 'corner_1' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見")
            
            # コーナー抽出部分を逆順に変更
            old_corner_logic = """            # コーナー通過順の個別カラム抽出(LightGBM用)
            corner_text = cells[12].text.strip() if len(cells) > 12 else ''
            if corner_text and '-' in corner_text:
                positions = corner_text.split('-')
                for j, pos in enumerate(positions[:4], 1):
                    horse_data[f'corner_{j}'] = pos.strip()"""
            
            new_corner_logic = """            # コーナー通過順の個別カラム抽出(LightGBM用、最終から逆順)
            corner_text = cells[12].text.strip() if len(cells) > 12 else ''
            if corner_text and '-' in corner_text:
                positions = corner_text.split('-')
                # 逆順に格納(corner_1=最終コーナー)
                for j, pos in enumerate(reversed(positions)):
                    if j < 4:
                        horse_data[f'corner_{j+1}'] = pos.strip()"""
            
            source = source.replace(old_corner_logic, new_corner_logic)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ コーナー抽出を逆順に変更")
            print("  ✅ corner_1 = 最終コーナー(ゴール直前)")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 JRA更新内容:")
print("  - corner_1: 最終コーナー(最も重要)")
print("  - corner_2: 最終-1コーナー")
print("  - corner_3: 最終-2コーナー")
print("  - corner_4: 最終-3コーナー")
