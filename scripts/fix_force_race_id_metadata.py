#!/usr/bin/env python3
"""
JRA/NARスクレイピングノートブックのメタデータ欠損を修正
"""

import json
import re

def fix_notebook_metadata(notebook_path):
    """
    force_race_id使用時でもメタデータを抽出するように修正
    """
    print(f"\n🔧 修正中: {notebook_path}")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        
        source = ''.join(cell['source'])
        
        # scrape_race_rich関数を探す
        if 'def scrape_race_rich(' not in source:
            continue
        
        if 'if force_race_id:' not in source:
            continue
        
        print(f"  ✅ セル {i}: scrape_race_rich関数を発見")
        
        # 修正: elseブロックを削除してメタデータを常に抽出
        lines = source.split('\n')
        new_lines = []
        in_else_block = False
        else_indent = 0
        
        for line in lines:
            # force_race_idのelseブロックを見つける
            if re.match(r'\s+else:\s*$', line) and 'venues_str' in source[source.index(line):source.index(line)+500]:
                # このelseはforce_race_idのelse
                in_else_block = True
                else_indent = len(line) - len(line.lstrip())
                # elseをコメントに変更
                new_lines.append(line.replace('else:', '# Always extract metadata (even with force_race_id)'))
                continue
            
            # elseブロック内のインデントを調整
            if in_else_block:
                current_indent = len(line) - len(line.lstrip())
                if line.strip() and current_indent <= else_indent:
                    # elseブロック終了
                    in_else_block = False
                    new_lines.append(line)
                else:
                    # インデントを1レベル減らす
                    if line.strip():
                        new_line = line[4:] if len(line) > 4 else line
                        new_lines.append(new_line)
                    else:
                        new_lines.append(line)
            else:
                new_lines.append(line)
        
        # セルを更新
        new_source = '\n'.join(new_lines)
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        if cell['source'] and cell['source'][-1].endswith('\n\n'):
            cell['source'][-1] = cell['source'][-1].rstrip('\n') + '\n'
        elif cell['source'] and cell['source'][-1] == '\n':
            cell['source'][-1] = ''
        
        print(f"  ✅ 修正完了")
        break
    
    # 保存
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    
    print(f"  💾 保存完了\n")

if __name__ == "__main__":
    print("="*80)
    print("🔧 メタデータ欠損の修正")
    print("="*80)
    
    notebooks = [
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Scraping.ipynb",
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Scraping.ipynb"
    ]
    
    for nb in notebooks:
        fix_notebook_metadata(nb)
    
    print("="*80)
    print("✅ 修正完了")
    print("="*80)
    print("\n📝 変更内容:")
    print("  - force_race_id使用時でもメタデータ(日付、会場等)を抽出")
    print("  - 基本情報カラムの欠損を解消")
    print("\n⚠️  次のステップ:")
    print("  1. 既存のCSVファイルを削除またはバックアップ")
    print("  2. 修正後のノートブックでスクレイピングを再実行")
    print("  3. メタデータが正しく取得されることを確認")
