#!/usr/bin/env python3
"""
NAR Basic v2のコーナー抽出ロジックを完全に書き直し
JRAと同様のシンプルな逆順抽出に変更
"""

import json
import re

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def scrape_race_basic(' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見\n")
            
            # 古いコーナー抽出ロジック全体を削除
            # race_data.append(horse_data)の前の部分を探す
            old_corner_logic = re.search(
                r'(# コーナー通過順位の抽出.*?)(race_data\.append\(horse_data\))',
                source,
                re.DOTALL
            )
            
            if old_corner_logic:
                print("📝 古いコーナー抽出ロジックを削除\n")
                
                # 新しいシンプルなロジック
                new_corner_logic = """# コーナー通過順位の抽出(NAR: 馬番号形式、同着考慮、逆順)
            umaban = horse_data['馬番']
            
            # 全コーナーの順位を収集(1コーナー→4コーナーの順)
            corner_positions_forward = []
            
            for corner_num in range(1, 5):
                corner_key = f'{corner_num}コーナー'
                if corner_key in corner_data:
                    corner_text = corner_data[corner_key]
                    
                    # 括弧(同着)を考慮してパース
                    corner_text = corner_text.replace('-', ',')
                    parts = []
                    current = ''
                    paren_depth = 0
                    
                    for char in corner_text:
                        if char == '(':
                            paren_depth += 1
                            current += char
                        elif char == ')':
                            paren_depth -= 1
                            current += char
                        elif char == ',' and paren_depth == 0:
                            if current.strip():
                                parts.append(current.strip())
                            current = ''
                        else:
                            current += char
                    
                    if current.strip():
                        parts.append(current.strip())
                    
                    # 各パートから順位を計算
                    current_position = 1
                    found_position = ''
                    
                    for part in parts:
                        if part.startswith('(') and part.endswith(')'):
                            horses_in_group = part[1:-1].split(',')
                            for horse_num in horses_in_group:
                                if horse_num.strip() == umaban:
                                    found_position = str(current_position)
                                    break
                            current_position += len([h for h in horses_in_group if h.strip()])
                        else:
                            if part.strip() == umaban:
                                found_position = str(current_position)
                            current_position += 1
                        
                        if found_position:
                            break
                    
                    corner_positions_forward.append(found_position)
            
            # 逆順に格納(corner_1=最終コーナー)
            for j, pos in enumerate(reversed(corner_positions_forward)):
                if j < 4:
                    horse_data[f'corner_{j+1}'] = pos
            
            race_data.append(horse_data)"""
                
                # 置換
                source = re.sub(
                    r'# コーナー通過順位の抽出.*?race_data\.append\(horse_data\)',
                    new_corner_logic,
                    source,
                    flags=re.DOTALL
                )
                
                print("✅ 新しいシンプルなコーナー抽出ロジックを追加\n")
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"💾 保存完了: {notebook_path}")
print("\n📝 変更内容:")
print("  - 複雑な逆順ロジックを削除")
print("  - シンプルな逆順抽出に変更")
print("  - corner_1~4を確実に格納")
