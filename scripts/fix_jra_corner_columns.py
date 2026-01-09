#!/usr/bin/env python3
"""
JRA Basic v2にコーナーカラムを正しく追加
"""

import json

notebook_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        
        if 'def scrape_race_basic(' in source:
            print(f"✅ セル{i}: スクレイピング関数を発見")
            
            # ordered_columnsにcorner_1~4を追加
            old_columns = """        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]"""
            
            new_columns = """        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', 'コーナー通過順', 'corner_1', 'corner_2', 'corner_3', 'corner_4',
            '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]"""
            
            if old_columns in source:
                source = source.replace(old_columns, new_columns)
                print("  ✅ ordered_columnsにcorner_1~4を追加")
            else:
                print("  ⚠️ ordered_columnsが見つかりません")
            
            # 辞書初期化にコーナーカラムを追加
            # コーナー通過順の後に追加
            if "'コーナー通過順': cells[12]" in source:
                old_dict = """                'コーナー通過順': cells[12].text.strip() if len(cells) > 12 else '',
                '厩舎': cells[13].text.strip() if len(cells) > 13 else '',"""
                
                new_dict = """                'コーナー通過順': cells[12].text.strip() if len(cells) > 12 else '',
                'corner_1': '',  # 最終コーナー
                'corner_2': '',  # 最終-1
                'corner_3': '',  # 最終-2
                'corner_4': '',  # 最終-3
                '厩舎': cells[13].text.strip() if len(cells) > 13 else '',"""
                
                source = source.replace(old_dict, new_dict)
                print("  ✅ 辞書初期化にcorner_1~4を追加")
            
            # コーナー抽出ロジックを追加
            if "horse_data['horse_id'] = horse_id_match.group(1)" in source:
                old_horse_id = """            if horse_link and 'href' in horse_link.attrs:
                horse_id_match = re.search(r'/horse/(\\d+)', horse_link['href'])
                if horse_id_match:
                    horse_data['horse_id'] = horse_id_match.group(1)
            
            race_data.append(horse_data)"""
                
                new_horse_id = """            if horse_link and 'href' in horse_link.attrs:
                horse_id_match = re.search(r'/horse/(\\d+)', horse_link['href'])
                if horse_id_match:
                    horse_data['horse_id'] = horse_id_match.group(1)
            
            # コーナー通過順の個別カラム抽出(LightGBM用、最終から逆順)
            corner_text = cells[12].text.strip() if len(cells) > 12 else ''
            if corner_text and '-' in corner_text:
                positions = corner_text.split('-')
                # 逆順に格納(corner_1=最終コーナー)
                for j, pos in enumerate(reversed(positions)):
                    if j < 4:
                        horse_data[f'corner_{j+1}'] = pos.strip()
            
            race_data.append(horse_data)"""
                
                source = source.replace(old_horse_id, new_horse_id)
                print("  ✅ コーナー抽出ロジックを追加")
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 追加内容:")
print("  - ordered_columns: 26 → 31カラム")
print("  - corner_1~4カラムを追加")
print("  - 逆順抽出ロジックを追加")
