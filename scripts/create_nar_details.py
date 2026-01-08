#!/usr/bin/env python3
"""
NAR Detailsノートブックを作成(JRAをベースに修正)
"""

import json

def create_nar_details():
    nar_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Details.ipynb"
    
    with open(nar_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # タイトルと説明を更新
    for cell in nb['cells']:
        if cell['cell_type'] == 'markdown':
            source = ''.join(cell['source'])
            source = source.replace('JRA', 'NAR')
            source = source.replace('database_basic.csv', 'database_nar_basic.csv')
            source = source.replace('database_details.csv', 'database_nar_details.csv')
            source = source.replace('database.csv', 'database_nar.csv')
            source = source.replace('merge_jra_data.py', 'merge_nar_data.py')
            source = source.replace('Colab_JRA_Basic.ipynb', 'Colab_NAR_Basic.ipynb')
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
        
        elif cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if 'BASIC_CSV' in source or 'DETAILS_CSV' in source:
                source = source.replace("BASIC_CSV = 'database_basic.csv'", 
                                       "BASIC_CSV = 'database_nar_basic.csv'")
                source = source.replace("DETAILS_CSV = 'database_details.csv'", 
                                       "DETAILS_CSV = 'database_nar_details.csv'")
                cell['source'] = [line + '\n' for line in source.split('\n')]
                if cell['source'] and cell['source'][-1] == '\n':
                    cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            if 'Colab_JRA_Basic.ipynb' in source:
                source = source.replace('Colab_JRA_Basic.ipynb', 'Colab_NAR_Basic.ipynb')
                source = source.replace('merge_jra_data.py', 'merge_nar_data.py')
                source = source.replace('database.csv', 'database_nar.csv')
                cell['source'] = [line + '\n' for line in source.split('\n')]
                if cell['source'] and cell['source'][-1] == '\n':
                    cell['source'][-1] = cell['source'][-1].rstrip('\n')
    
    # 保存
    with open(nar_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    
    print(f"✅ NAR Details notebook created: {nar_path}")

if __name__ == "__main__":
    create_nar_details()
