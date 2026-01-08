#!/usr/bin/env python3
"""
カラム名のスペース問題を修正するスクリプト
ノートブック内のscrape_race_rich関数を更新
"""

import json
import re
from pathlib import Path

def fix_column_names_in_notebook(notebook_path: str):
    """
    ノートブック内のカラム名を修正
    """
    print(f"\n{'='*80}")
    print(f"🔧 カラム名修正: {Path(notebook_path).name}")
    print(f"{'='*80}\n")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    modified = False
    
    for cell in nb['cells']:
        if cell['cell_type'] != 'code':
            continue
        
        source = ''.join(cell['source'])
        
        # scrape_race_rich関数内のカラム名を修正
        if 'row_dict = {' in source and 'scrape_race_rich' in source:
            print("✅ scrape_race_rich関数を発見")
            
            # スペースを含むカラム名を修正
            replacements = [
                (r'"着\s*順"', '"着順"'),
                (r'"馬\s*番"', '"馬番"'),
                (r'"人\s*気"', '"人気"'),
                (r'"単勝\s*オッズ"', '"単勝オッズ"'),
            ]
            
            original_source = source
            for pattern, replacement in replacements:
                source = re.sub(pattern, replacement, source)
            
            if source != original_source:
                cell['source'] = source.split('\n')
                # 各行の末尾に改行を追加
                cell['source'] = [line + '\n' if not line.endswith('\n') else line 
                                 for line in cell['source']]
                modified = True
                print("  ✅ カラム名を修正しました")
                print(f"     - 着順, 馬番, 人気, 単勝オッズ")
    
    if modified:
        # 保存
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        print(f"\n✅ 修正を保存しました: {notebook_path}")
    else:
        print(f"\n⚠️  修正箇所が見つかりませんでした")
    
    return modified

if __name__ == "__main__":
    notebooks = [
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Scraping.ipynb",
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Scraping.ipynb"
    ]
    
    total_modified = 0
    for nb_path in notebooks:
        if Path(nb_path).exists():
            if fix_column_names_in_notebook(nb_path):
                total_modified += 1
    
    print(f"\n{'='*80}")
    print(f"✅ 完了: {total_modified}/{len(notebooks)} ノートブックを修正")
    print(f"{'='*80}\n")
