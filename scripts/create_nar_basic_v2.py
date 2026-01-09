#!/usr/bin/env python3
"""
NAR Basic v2ノートブックをJRAから作成
"""

import json

nar_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"

with open(nar_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# タイトルと設定を更新
for cell in nb['cells']:
    if cell['cell_type'] == 'markdown':
        source = ''.join(cell['source'])
        source = source.replace('JRA', 'NAR')
        cell['source'] = [line + '\n' for line in source.split('\n')]
        if cell['source'] and cell['source'][-1] == '\n':
            cell['source'][-1] = cell['source'][-1].rstrip('\n')
    
    elif cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        # 設定を更新
        if 'TARGET_CSV' in source:
            source = source.replace("TARGET_CSV = 'database_basic.csv'", 
                                   "TARGET_CSV = 'database_nar_basic.csv'")
            source = source.replace("MASTER_ID_CSV = 'race_ids.csv'",
                                   "MASTER_ID_CSV = 'race_ids_nar.csv'")
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')

# 保存
with open(nar_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("✅ NAR Basic v2 created")
