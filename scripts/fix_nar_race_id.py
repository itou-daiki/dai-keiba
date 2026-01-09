#!/usr/bin/env python3
"""
NAR Basic v2のrace_id生成を修正
URLから直接取得するように変更
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
            
            # race_id生成部分を修正
            # 複雑な生成ロジックを削除し、URLから直接取得
            old_race_id_logic = """        # race_id生成
        if metadata['日付'] and metadata['会場'] and metadata['レース番号']:
            year = metadata['日付'][:4]
            place_map = {
                '札幌': '01', '函館': '02', '福島': '03', '新潟': '04', '東京': '05',
                '中山': '06', '中京': '07', '京都': '08', '阪神': '09', '小倉': '10'
            }
            place_code = place_map.get(metadata['会場'], '00')
            race_num = metadata['レース番号'].replace('R', '')
            race_num_padded = f"{int(race_num):02d}"
            
            kai = '01'
            nichi = '01'
            kai_match = re.search(rf'(\\d+)回{metadata["会場"]}(\\d+)日', title + full_text)
            if kai_match:
                kai = f"{int(kai_match.group(1)):02d}"
                nichi = f"{int(kai_match.group(2)):02d}"
            
            metadata['race_id'] = f"{year}{place_code}{kai}{nichi}{race_num_padded}\""""
            
            new_race_id_logic = """        # race_id(URLから直接取得)
        race_id_match = re.search(r'race_id=(\\d+)', url)
        if race_id_match:
            metadata['race_id'] = race_id_match.group(1)"""
            
            source = source.replace(old_race_id_logic, new_race_id_logic)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ race_id生成をURLから直接取得に変更")
            break

# 保存
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 修正内容:")
print("  - race_id: 複雑な生成ロジック → URLから直接取得")
