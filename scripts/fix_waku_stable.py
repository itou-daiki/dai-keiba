#!/usr/bin/env python3
"""
JRA/NAR Basic v2ノートブックの枠・厩舎抽出を修正
"""

import json

def fix_notebook(notebook_path, stable_cell_index):
    """ノートブックの枠・厩舎抽出を修正"""
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            
            if 'def scrape_race_basic(' in source:
                print(f"✅ セル{i}: スクレイピング関数を発見")
                
                # 枠番の抽出を修正(画像から → テキストから)
                old_waku = """            # 枠番(画像から抽出)
            waku_img = cells[1].find('img') if len(cells) > 1 else None
            if waku_img and 'alt' in waku_img.attrs:
                waku_match = re.search(r'枠(\\d+)', waku_img['alt'])
                if waku_match:
                    horse_data['枠'] = waku_match.group(1)"""
                
                new_waku = """            # 枠番(テキストから直接取得)
            if len(cells) > 1:
                horse_data['枠'] = cells[1].text.strip()"""
                
                source = source.replace(old_waku, new_waku)
                
                # 厩舎の抽出を修正(セル18 → 正しいセル)
                old_stable = f"'厩舎': cells[18].text.strip() if len(cells) > 18 else '',"
                new_stable = f"'厩舎': cells[{stable_cell_index}].text.strip() if len(cells) > {stable_cell_index} else '',"
                
                source = source.replace(old_stable, new_stable)
                
                cell['source'] = [line + '\n' for line in source.split('\n')]
                if cell['source'] and cell['source'][-1] == '\n':
                    cell['source'][-1] = cell['source'][-1].rstrip('\n')
                
                print(f"  ✅ 枠番: 画像から → テキストから")
                print(f"  ✅ 厩舎: セル18 → セル{stable_cell_index}")
                break
    
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    
    print(f"💾 保存完了: {notebook_path}\n")

# JRA Basic v2 (厩舎=セル13)
print("📝 JRA Basic v2 修正:")
print(f"{'-'*80}")
fix_notebook("/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb", 13)

# NAR Basic v2 (厩舎=セル12)
print("📝 NAR Basic v2 修正:")
print(f"{'-'*80}")
fix_notebook("/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb", 12)

print("✅ 両方のノートブックを修正しました")
