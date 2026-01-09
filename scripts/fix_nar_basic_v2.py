#!/usr/bin/env python3
"""
NAR Basic v2 ノートブックを修正
- NAR会場リストに変更
- nar.netkeiba.com URLに変更
"""

import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# メタデータ抽出関数のセルを探して修正
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def extract_metadata(' in source:
            print(f"✅ セル{i}: メタデータ抽出関数を発見")
            
            # JRA会場リストをNAR会場リストに置換
            source = source.replace(
                "venues = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']",
                "nar_venues = ['門別', '盛岡', '水沢', '浦和', '船橋', '大井', '川崎', '金沢', '笠松', '名古屋', '園田', '姫路', '高知', '佐賀', 'ばんえい帯広']"
            )
            source = source.replace("for venue in venues:", "for venue in nar_venues:")
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ 会場リストをNARに変更")
        
        if 'def scrape_race_basic(' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見")
            
            # URLをnar.netkeiba.comに変更
            source = source.replace(
                'url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"',
                'url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"'
            )
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ URLをnar.netkeiba.comに変更")

# 保存
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 修正内容:")
print("  - 会場リスト: JRA → NAR")
print("  - URL: race.netkeiba.com → nar.netkeiba.com")
