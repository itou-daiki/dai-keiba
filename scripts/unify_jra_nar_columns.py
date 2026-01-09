#!/usr/bin/env python3
"""
JRAとNARのカラム構造を完全統一
NARに「コーナー通過順」カラムを追加(空欄)
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
            
            # 辞書構築部分に「コーナー通過順」を追加
            old_dict = """            # 基本情報を辞書で構築(カラムズレ防止)
            horse_data = {
                '日付': metadata['日付'],
                '会場': metadata['会場'],
                'レース番号': metadata['レース番号'],
                'レース名': metadata['レース名'],
                '重賞': metadata['重賞'],
                'コースタイプ': metadata['コースタイプ'],
                '距離': metadata['距離'],
                '回り': metadata['回り'],
                '天候': metadata['天候'],
                '馬場状態': metadata['馬場状態'],
                '着順': cells[0].text.strip(),
                '枠': '',
                '馬番': cells[2].text.strip() if len(cells) > 2 else '',
                '馬名': cells[3].text.strip() if len(cells) > 3 else '',
                '性齢': cells[4].text.strip() if len(cells) > 4 else '',
                '斤量': cells[5].text.strip() if len(cells) > 5 else '',
                '騎手': cells[6].text.strip() if len(cells) > 6 else '',
                'タイム': cells[7].text.strip() if len(cells) > 7 else '',
                '着差': cells[8].text.strip() if len(cells) > 8 else '',
                '人気': cells[9].text.strip() if len(cells) > 9 else '',
                '単勝オッズ': cells[10].text.strip() if len(cells) > 10 else '',
                '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                '厩舎': cells[12].text.strip() if len(cells) > 12 else '',
                '馬体重(増減)': cells[13].text.strip() if len(cells) > 13 else '',
                'race_id': metadata['race_id'],
                'horse_id': ''
            }"""
            
            new_dict = """            # 基本情報を辞書で構築(カラムズレ防止)
            horse_data = {
                '日付': metadata['日付'],
                '会場': metadata['会場'],
                'レース番号': metadata['レース番号'],
                'レース名': metadata['レース名'],
                '重賞': metadata['重賞'],
                'コースタイプ': metadata['コースタイプ'],
                '距離': metadata['距離'],
                '回り': metadata['回り'],
                '天候': metadata['天候'],
                '馬場状態': metadata['馬場状態'],
                '着順': cells[0].text.strip(),
                '枠': '',
                '馬番': cells[2].text.strip() if len(cells) > 2 else '',
                '馬名': cells[3].text.strip() if len(cells) > 3 else '',
                '性齢': cells[4].text.strip() if len(cells) > 4 else '',
                '斤量': cells[5].text.strip() if len(cells) > 5 else '',
                '騎手': cells[6].text.strip() if len(cells) > 6 else '',
                'タイム': cells[7].text.strip() if len(cells) > 7 else '',
                '着差': cells[8].text.strip() if len(cells) > 8 else '',
                '人気': cells[9].text.strip() if len(cells) > 9 else '',
                '単勝オッズ': cells[10].text.strip() if len(cells) > 10 else '',
                '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                'コーナー通過順': '',  # NARには存在しないため空欄
                '厩舎': cells[12].text.strip() if len(cells) > 12 else '',
                '馬体重(増減)': cells[13].text.strip() if len(cells) > 13 else '',
                'race_id': metadata['race_id'],
                'horse_id': ''
            }"""
            
            source = source.replace(old_dict, new_dict)
            
            # ordered_columnsにも追加
            old_columns = """        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]"""
            
            new_columns = """        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', 'コーナー通過順', '厩舎', '馬体重(増減)', 'race_id', 'horse_id'
        ]"""
            
            source = source.replace(old_columns, new_columns)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ 'コーナー通過順'カラムを追加(空欄)")
            print("  ✅ ordered_columnsを更新")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 統一後のカラム構造(27カラム):")
print("  1. 日付")
print("  2. 会場")
print("  3. レース番号")
print("  4. レース名")
print("  5. 重賞")
print("  6. コースタイプ")
print("  7. 距離")
print("  8. 回り")
print("  9. 天候")
print("  10. 馬場状態")
print("  11. 着順")
print("  12. 枠")
print("  13. 馬番")
print("  14. 馬名")
print("  15. 性齢")
print("  16. 斤量")
print("  17. 騎手")
print("  18. タイム")
print("  19. 着差")
print("  20. 人気")
print("  21. 単勝オッズ")
print("  22. 後3F")
print("  23. コーナー通過順 (JRA: データあり, NAR: 空欄)")
print("  24. 厩舎")
print("  25. 馬体重(増減)")
print("  26. race_id")
print("  27. horse_id")
print("\n✅ JRAとNARのカラム構造が完全に統一されました")
