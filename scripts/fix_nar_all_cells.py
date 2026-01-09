#!/usr/bin/env python3
"""
NAR Basic v2ノートブックの全セル位置を修正
JRAとNARでテーブル構造が異なるため、正しいセル位置に修正
"""

import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def scrape_race_basic(' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見")
            
            # NARの正しいセル位置
            # JRAと比較してコーナー通過順がないため、1つずつずれる
            
            # 馬体重(増減): cells[14] → cells[13]
            source = source.replace(
                "'馬体重(増減)': cells[14].text.strip() if len(cells) > 14 else '',",
                "'馬体重(増減)': cells[13].text.strip() if len(cells) > 13 else '',"
            )
            print("  ✅ 馬体重(増減): cells[14] → cells[13]")
            
            # 厩舎は既にcells[12]に修正済みのはず
            if "cells[12].text.strip() if len(cells) > 12" in source and "'厩舎':" in source:
                print("  ✅ 厩舎: cells[12] (既に正しい)")
            
            # 後3F: cells[11]のまま(正しい)
            if "cells[11].text.strip() if len(cells) > 11" in source and "'後3F':" in source:
                print("  ✅ 後3F: cells[11] (正しい)")
            
            # 単勝オッズ: cells[10]のまま(正しい)
            if "cells[10].text.strip() if len(cells) > 10" in source and "'単勝オッズ':" in source:
                print("  ✅ 単勝オッズ: cells[10] (正しい)")
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 NAR修正内容:")
print("  - 馬体重(増減): cells[14] → cells[13]")
print("  - その他のフィールドは正しいセル位置を使用")
