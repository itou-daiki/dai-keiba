#!/usr/bin/env python3
"""
NAR Basic v2にコーナー通過順抽出を追加
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
            
            # NARのコーナー通過順抽出ロジックを追加
            # まず、コーナーテーブルを取得する処理を追加
            insert_point = """        # メタデータ抽出
        metadata = extract_metadata(soup, url)"""
            
            corner_extraction = """        # メタデータ抽出
        metadata = extract_metadata(soup, url)
        
        # コーナー通過順テーブル取得(NAR)
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
            
            source = source.replace(insert_point, corner_extraction)
            
            # 各馬のデータ抽出時にコーナー順位を追加
            old_horse_id = """            # horse_id(リンクから抽出)
            horse_link = cells[3].find('a') if len(cells) > 3 else None
            if horse_link and 'href' in horse_link.attrs:
                horse_id_match = re.search(r'/horse/(\\d+)', horse_link['href'])
                if horse_id_match:
                    horse_data['horse_id'] = horse_id_match.group(1)
            
            race_data.append(horse_data)"""
            
            new_horse_id = """            # horse_id(リンクから抽出)
            horse_link = cells[3].find('a') if len(cells) > 3 else None
            if horse_link and 'href' in horse_link.attrs:
                horse_id_match = re.search(r'/horse/(\\d+)', horse_link['href'])
                if horse_id_match:
                    horse_data['horse_id'] = horse_id_match.group(1)
            
            # コーナー通過順位の抽出(NAR: 馬番号形式)
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
                            break
            
            race_data.append(horse_data)"""
            
            source = source.replace(old_horse_id, new_horse_id)
            
            # ordered_columnsにコーナーカラムを追加
            old_columns = """        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', 'コーナー通過順', '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]"""
            
            new_columns = """        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', 'コーナー通過順', 'corner_1', 'corner_2', 'corner_3', 'corner_4',
            '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]"""
            
            source = source.replace(old_columns, new_columns)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ NARコーナー通過順抽出を追加")
            print("  ✅ corner_1, corner_2, corner_3, corner_4 カラムを追加")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 NAR Basic v2 更新内容:")
print("  - コーナー通過順テーブルから馬番号形式をパース")
print("  - 各馬の順位を抽出してcorner_1~4に格納")
print("  - 総カラム数: 27 → 31カラム")
