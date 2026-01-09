#!/usr/bin/env python3
"""
NAR Basic v2のコーナー抽出ロジックを同着対応版に更新
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
            
            # コーナーテーブル取得部分を修正
            old_corner_table = """        # コーナー通過順テーブル取得(NAR)
        corner_data = {}
        for table in tables:
            if 'コーナー' in table.text and '通過' in table.text:
                corner_rows = table.find_all('tr')
                for row in corner_rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        corner_name = cells[0].text.strip()
                        corner_text = cells[1].text.strip()
                        corner_data[corner_name] = corner_text
                break"""
            
            new_corner_table = """        # コーナー通過順テーブル取得(NAR)
        corner_data = {}
        for table in tables:
            if 'コーナー' in table.text:
                headers_cells = table.find_all('th')
                corner_names = [th.text.strip() for th in headers_cells]
                corner_rows = table.find_all('tr')
                for j, row in enumerate(corner_rows):
                    cells = row.find_all('td')
                    if cells and j < len(corner_names):
                        corner_data[corner_names[j]] = cells[0].text.strip()
                break"""
            
            source = source.replace(old_corner_table, new_corner_table)
            
            # コーナー順位抽出部分を同着対応版に修正
            old_corner_extract = """            # コーナー通過順位の抽出(NAR: 馬番号形式)
            umaban = horse_data['馬番']
            for corner_num in range(1, 5):
                corner_key = f'{corner_num}コーナー'
                if corner_key in corner_data:
                    corner_text = corner_data[corner_key]
                    # 馬番号形式をパース
                    corner_text_clean = corner_text.replace('(', '').replace(')', '').replace('-', ',')
                    horses = [h.strip() for h in corner_text_clean.split(',') if h.strip()]
                    for j, horse_num in enumerate(horses, 1):
                        if horse_num == umaban:
                            horse_data[f'corner_{corner_num}'] = str(j)
                            break"""
            
            new_corner_extract = """            # コーナー通過順位の抽出(NAR: 馬番号形式、同着考慮)
            umaban = horse_data['馬番']
            for corner_num in range(1, 5):
                corner_key = f'{corner_num}コーナー'
                if corner_key in corner_data:
                    corner_text = corner_data[corner_key]
                    # 括弧(同着)を考慮してパース
                    corner_text = corner_text.replace('-', ',')
                    parts = []
                    current = ''
                    paren_depth = 0
                    for char in corner_text:
                        if char == '(':
                            paren_depth += 1
                            current += char
                        elif char == ')':
                            paren_depth -= 1
                            current += char
                        elif char == ',' and paren_depth == 0:
                            if current.strip():
                                parts.append(current.strip())
                            current = ''
                        else:
                            current += char
                    if current.strip():
                        parts.append(current.strip())
                    
                    # 各パートから順位を計算
                    current_position = 1
                    for part in parts:
                        if part.startswith('(') and part.endswith(')'):
                            horses_in_group = part[1:-1].split(',')
                            for horse_num in horses_in_group:
                                if horse_num.strip() == umaban:
                                    horse_data[f'corner_{corner_num}'] = str(current_position)
                                    break
                            current_position += len([h for h in horses_in_group if h.strip()])
                        else:
                            if part.strip() == umaban:
                                horse_data[f'corner_{corner_num}'] = str(current_position)
                            current_position += 1"""
            
            source = source.replace(old_corner_extract, new_corner_extract)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ コーナー抽出ロジックを同着対応版に更新")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 更新内容:")
print("  - 括弧内の同着馬を正しく処理")
print("  - 同着馬は同じ順位、次の馬は括弧内の馬数分加算")
