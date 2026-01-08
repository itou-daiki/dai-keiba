#!/usr/bin/env python3
"""
JRA/NARスクレイピングノートブックの変数初期化バグをチェック・修正
"""

import json
import re

def check_and_fix_notebook(notebook_path: str, notebook_type: str):
    """
    ノートブックの変数初期化バグをチェック・修正
    """
    print(f"\n{'='*80}")
    print(f"🔍 Checking: {notebook_path}")
    print(f"{'='*80}\n")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    fixed = False
    
    for cell_idx, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        
        source = ''.join(cell['source'])
        
        # scrape_race_rich関数をチェック
        if 'def scrape_race_rich' in source or 'def scrape_race_basic' in source:
            print(f"✅ Found scraping function in cell {cell_idx}")
            
            # force_race_idの使用をチェック
            if 'if force_race_id:' in source:
                print("  📌 Uses force_race_id")
                
                # venue_textが初期化されているかチェック
                # パターン1: if force_race_id の前に venue_text = "" がある
                pattern1 = r'venue_text\s*=\s*"".*?if force_race_id:'
                # パターン2: else ブロック内に venue_text = "" がある
                pattern2 = r'if force_race_id:.*?else:.*?venue_text\s*=\s*""'
                
                has_init_before = bool(re.search(pattern1, source, re.DOTALL))
                has_init_in_else = bool(re.search(pattern2, source, re.DOTALL))
                
                if has_init_before:
                    print("  ✅ venue_text is initialized BEFORE if/else (GOOD)")
                elif has_init_in_else:
                    print("  ⚠️  venue_text is initialized in ELSE block (POTENTIAL BUG)")
                    print("  🔧 Fixing...")
                    
                    # 修正: venue_textをif文の前に移動
                    # パターンを探して修正
                    old_pattern = r'(if force_race_id:\s*race_id = str\(force_race_id\)\s*else:\s*# Parse race_id from header\s*)(venue_text = "")'
                    
                    def replacement(match):
                        return f'venue_text = ""\n        kai = "01"\n        day = "01"\n        r_num = "10"\n        \n        {match.group(1).strip()}\n            '
                    
                    new_source = re.sub(old_pattern, replacement, source, flags=re.DOTALL)
                    
                    if new_source != source:
                        cell['source'] = [line + '\n' for line in new_source.split('\n')]
                        if cell['source'] and cell['source'][-1] == '\n':
                            cell['source'][-1] = cell['source'][-1].rstrip('\n')
                        fixed = True
                        print("  ✅ Fixed!")
                    else:
                        print("  ⚠️  Could not auto-fix, manual review needed")
                else:
                    print("  ❌ venue_text initialization NOT FOUND (BUG!)")
                    print("  ⚠️  Manual fix required")
            else:
                print("  ℹ️  Does not use force_race_id")
    
    if fixed:
        # 保存
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        print(f"\n✅ Fixed and saved: {notebook_path}")
    else:
        print(f"\n✅ No fixes needed")
    
    return fixed

if __name__ == "__main__":
    print("🔍 Checking JRA/NAR Scraping notebooks for variable initialization bugs...\n")
    
    notebooks = [
        ("/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Scraping.ipynb", "JRA"),
        ("/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Scraping.ipynb", "NAR")
    ]
    
    total_fixed = 0
    for nb_path, nb_type in notebooks:
        if check_and_fix_notebook(nb_path, nb_type):
            total_fixed += 1
    
    print(f"\n{'='*80}")
    print(f"✅ Check complete: {total_fixed}/{len(notebooks)} notebooks fixed")
    print(f"{'='*80}\n")
