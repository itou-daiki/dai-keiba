#!/usr/bin/env python3
"""
Colab_JRA_Basic.ipynbのvenue_text初期化バグを修正
"""

import json

def fix_jra_basic_notebook():
    notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic.ipynb"
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # セル3(スクレイピングロジック)を修正
    for cell in nb['cells']:
        if cell['cell_type'] == 'code' and 'scrape_race_basic' in ''.join(cell['source']):
            source = ''.join(cell['source'])
            
            # 修正: venue_textとr_numをforce_race_idの前に初期化
            old_code = """        if force_race_id:
            race_id = str(force_race_id)
        else:
            # Parse race_id from header
            venue_text = ""
            kai = "01"
            day = "01"
            r_num = "10\""""
            
            new_code = """        # Initialize variables
        venue_text = ""
        kai = "01"
        day = "01"
        r_num = "10"
        
        if force_race_id:
            race_id = str(force_race_id)
        else:
            # Parse race_id from header"""
            
            if old_code in source:
                source = source.replace(old_code, new_code)
                cell['source'] = [line + '\n' for line in source.split('\n')]
                # 最後の行の改行を削除
                if cell['source'] and cell['source'][-1] == '\n':
                    cell['source'][-1] = cell['source'][-1].rstrip('\n')
                print("✅ JRA Basic notebook fixed")
                break
    
    # 保存
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    
    print(f"✅ Saved: {notebook_path}")

def fix_nar_basic_notebook():
    notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic.ipynb"
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # セル3(スクレイピングロジック)を修正
    for cell in nb['cells']:
        if cell['cell_type'] == 'code' and 'scrape_nar_race_basic' in ''.join(cell['source']):
            source = ''.join(cell['source'])
            
            # NAR用の修正
            old_code = """        # NAR: force_race_idを使用
        race_id = str(force_race_id) if force_race_id else ""
        
        # Race Info"""
            
            new_code = """        # NAR: force_race_idを使用
        race_id = str(force_race_id) if force_race_id else ""
        
        # Initialize variables
        venue_text = ""
        r_num = ""
        
        # Race Info"""
            
            if old_code in source:
                source = source.replace(old_code, new_code)
                cell['source'] = [line + '\n' for line in source.split('\n')]
                # 最後の行の改行を削除
                if cell['source'] and cell['source'][-1] == '\n':
                    cell['source'][-1] = cell['source'][-1].rstrip('\n')
                print("✅ NAR Basic notebook fixed")
                break
    
    # 保存
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    
    print(f"✅ Saved: {notebook_path}")

if __name__ == "__main__":
    print("🔧 Fixing variable initialization bugs...\n")
    fix_jra_basic_notebook()
    fix_nar_basic_notebook()
    print("\n✅ All notebooks fixed!")
