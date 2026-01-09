#!/usr/bin/env python3
"""
JRA Basic v2にコーナー通過順の個別カラム抽出を追加
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
            
            # コーナー通過順の抽出ロジックを追加
            # 辞書構築の後に追加
            old_code = """            # horse_id(リンクから抽出)
            horse_link = cells[3].find('a') if len(cells) > 3 else None
            if horse_link and 'href' in horse_link.attrs:
                horse_id_match = re.search(r'/horse/(\\d+)', horse_link['href'])
                if horse_id_match:
                    horse_data['horse_id'] = horse_id_match.group(1)
            
            race_data.append(horse_data)"""
            
            new_code = """            # horse_id(リンクから抽出)
            horse_link = cells[3].find('a') if len(cells) > 3 else None
            if horse_link and 'href' in horse_link.attrs:
                horse_id_match = re.search(r'/horse/(\\d+)', horse_link['href'])
                if horse_id_match:
                    horse_data['horse_id'] = horse_id_match.group(1)
            
            # コーナー通過順の個別カラム抽出(LightGBM用)
            corner_text = cells[12].text.strip() if len(cells) > 12 else ''
            if corner_text and '-' in corner_text:
                positions = corner_text.split('-')
                for j, pos in enumerate(positions[:4], 1):
                    horse_data[f'corner_{j}'] = pos.strip()
            
            race_data.append(horse_data)"""
            
            source = source.replace(old_code, new_code)
            
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
            
            # 辞書初期化にもコーナーカラムを追加
            old_dict_init = """                'コーナー通過順': '',  # NARには存在しないため空欄
                '厩舎': cells[12].text.strip() if len(cells) > 12 else '',"""
            
            new_dict_init = """                'コーナー通過順': '',  # 生データ
                'corner_1': '',  # 1コーナー通過順位
                'corner_2': '',  # 2コーナー通過順位
                'corner_3': '',  # 3コーナー通過順位
                'corner_4': '',  # 4コーナー通過順位
                '厩舎': cells[13].text.strip() if len(cells) > 13 else '',"""
            
            source = source.replace(old_dict_init, new_dict_init)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ コーナー通過順の個別カラム抽出を追加")
            print("  ✅ corner_1, corner_2, corner_3, corner_4 カラムを追加")
            print("  ✅ ordered_columnsを更新(27→31カラム)")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 JRA Basic v2 更新内容:")
print("  - コーナー通過順を個別カラムに分解")
print("  - corner_1, corner_2, corner_3, corner_4 を追加")
print("  - 総カラム数: 27 → 31カラム")
