#!/usr/bin/env python3
"""
JRA Basic v2の辞書初期化を完全修正
コーナー通過順とcorner_1~4を確実に追加
"""

import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def scrape_race_basic(' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見\n")
            
            # 辞書初期化の'後3F'の後に'コーナー通過順'とcorner_1~4を挿入
            old_dict = """                '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                '厩舎': cells[13].text.strip() if len(cells) > 13 else '',"""
            
            new_dict = """                '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                'コーナー通過順': cells[12].text.strip() if len(cells) > 12 else '',
                'corner_1': '',
                'corner_2': '',
                'corner_3': '',
                'corner_4': '',
                '厩舎': cells[13].text.strip() if len(cells) > 13 else '',"""
            
            source = source.replace(old_dict, new_dict)
            print("✅ 辞書初期化に'コーナー通過順'とcorner_1~4を追加\n")
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"💾 保存完了: {notebook_path}")
