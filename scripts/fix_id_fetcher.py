#!/usr/bin/env python3
"""
Colab_ID_Fetcher.ipynb を修正
JRA: 10桁、NAR: 12桁のrace_IDに対応
"""

import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_ID_Fetcher.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def get_race_ids_from_date(' in source:
            print(f"✅ セル{i}: get_race_ids_from_date関数を発見\n")
            
            # 固定の12桁チェックを、モードに応じた桁数チェックに変更
            old_check = """                rid = m.group(1)
                if len(rid) == 12:  # レースIDは12桁
                    race_ids.add(rid)"""
            
            new_check = """                rid = m.group(1)
                # JRA: 10桁, NAR: 12桁
                expected_len = 10 if mode == 'JRA' else 12
                if len(rid) == expected_len:
                    race_ids.add(rid)"""
            
            source = source.replace(old_check, new_check)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ race_ID桁数チェックを修正")
            print("     JRA: 10桁")
            print("     NAR: 12桁")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
