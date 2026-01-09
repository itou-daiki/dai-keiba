#!/usr/bin/env python3
"""
NAR Basic v2のtables変数スコープエラーを修正
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
            
            # tablesの定義を、コーナーデータ取得の前に移動
            old_code = """        # メタデータ抽出
        metadata = extract_metadata(soup, url)
        
        # コーナー通過順テーブル取得(NAR)
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
                break
        
        # レース結果テーブル取得
        tables = soup.find_all('table')"""
            
            new_code = """        # メタデータ抽出
        metadata = extract_metadata(soup, url)
        
        # 全テーブル取得(コーナーデータとレース結果の両方で使用)
        tables = soup.find_all('table')
        
        # コーナー通過順テーブル取得(NAR)
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
                break
        
        # レース結果テーブル取得"""
            
            source = source.replace(old_code, new_code)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ tables変数の定義をコーナーデータ取得の前に移動")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 修正内容:")
print("  - tables = soup.find_all('table') をコーナーデータ取得の前に移動")
print("  - スコープエラーを解決")
