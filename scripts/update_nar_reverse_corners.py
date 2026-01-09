#!/usr/bin/env python3
"""
NAR Basic v2を逆順コーナー抽出に更新
"""

import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def scrape_race_basic(' in source and 'corner_1' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見")
            
            # NARのコーナー抽出を逆順に変更
            # 現在の実装: corner_numで1,2,3,4の順にループ
            # 変更後: コーナーデータを収集してから逆順に格納
            
            old_nar_logic = """            # コーナー通過順位の抽出(NAR: 馬番号形式、同着考慮)
            umaban = horse_data['馬番']
            for corner_num in range(1, 5):
                corner_key = f'{corner_num}コーナー'
                if corner_key in corner_data:"""
            
            new_nar_logic = """            # コーナー通過順位の抽出(NAR: 馬番号形式、同着考慮、逆順)
            umaban = horse_data['馬番']
            # まず全コーナーの順位を収集
            corner_positions = []
            for corner_num in range(1, 5):
                corner_key = f'{corner_num}コーナー'
                if corner_key in corner_data:"""
            
            # corner_dataループの最後を変更
            old_loop_end = """                            current_position += 1"""
            
            new_loop_end = """                            current_position += 1
                    # 順位を収集
                    if f'corner_{corner_num}' in horse_data:
                        corner_positions.append(horse_data[f'corner_{corner_num}'])
                        del horse_data[f'corner_{corner_num}']  # 一旦削除
            
            # 逆順に格納(corner_1=最終コーナー)
            for j, pos in enumerate(reversed(corner_positions)):
                if j < 4:
                    horse_data[f'corner_{j+1}'] = pos"""
            
            source = source.replace(old_nar_logic, new_nar_logic)
            source = source.replace(old_loop_end, new_loop_end)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ コーナー抽出を逆順に変更")
            print("  ✅ corner_1 = 最終コーナー")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 NAR更新内容:")
print("  - コーナーデータを収集後、逆順に格納")
print("  - corner_1: 最終コーナー")
print("  - JRAと同じ順序で統一")
