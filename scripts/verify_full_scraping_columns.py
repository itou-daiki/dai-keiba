#!/usr/bin/env python3
"""
一括スクレイピングノートブック(JRA/NAR)のカラム整合性を検証
"""

import json
import re

def extract_ordered_columns_from_notebook(notebook_path):
    """
    ノートブックからordered_columnsリストを抽出
    """
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            
            # ordered_columnsを探す
            if 'ordered_columns = [' in source:
                # リストを抽出
                match = re.search(r'ordered_columns\s*=\s*\[(.*?)\]', source, re.DOTALL)
                if match:
                    columns_str = match.group(1)
                    # カラム名を抽出
                    columns = re.findall(r'"([^"]+)"', columns_str)
                    return columns
    
    return None

def extract_row_dict_keys_from_notebook(notebook_path):
    """
    ノートブックからrow_dictのキーを抽出
    """
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            
            # row_dictを探す
            if 'row_dict = {' in source or 'row_data = {' in source:
                # キーを抽出
                keys = re.findall(r'"([^"]+)":\s*[^,}]+', source)
                return keys
    
    return None

def verify_notebook_columns(notebook_path, notebook_name):
    """
    ノートブックのカラム整合性を検証
    """
    print(f"\n{'='*80}")
    print(f"🔍 検証: {notebook_name}")
    print(f"{'='*80}\n")
    
    # ordered_columnsを抽出
    ordered_cols = extract_ordered_columns_from_notebook(notebook_path)
    
    if not ordered_cols:
        print("❌ ordered_columnsが見つかりません")
        return False
    
    print(f"✅ ordered_columns定義を発見")
    print(f"   カラム数: {len(ordered_cols)}")
    print(f"   期待値: 94カラム")
    
    if len(ordered_cols) != 94:
        print(f"   ⚠️  カラム数が一致しません: {len(ordered_cols)} != 94")
    else:
        print(f"   ✅ カラム数OK")
    
    # row_dictのキーを抽出
    row_keys = extract_row_dict_keys_from_notebook(notebook_path)
    
    if not row_keys:
        print("\n❌ row_dict定義が見つかりません")
        return False
    
    print(f"\n✅ row_dict定義を発見")
    print(f"   キー数: {len(row_keys)}")
    
    # 基本情報カラム(26)
    basic_cols = [
        "日付", "会場", "レース番号", "レース名", "重賞", "コースタイプ", "距離", "回り", "天候", "馬場状態",
        "着順", "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "タイム", "着差", "人気", "単勝オッズ",
        "後3F", "厩舎", "馬体重(増減)", "race_id", "horse_id"
    ]
    
    # row_dictに基本カラムが含まれているかチェック
    missing_basic = []
    for col in basic_cols:
        if col not in row_keys:
            missing_basic.append(col)
    
    if missing_basic:
        print(f"\n⚠️  基本カラムの欠落:")
        for col in missing_basic:
            print(f"     - {col}")
    else:
        print(f"\n✅ 基本カラム(26): すべて存在")
    
    # 過去5走カラムチェック
    past_cols_expected = 65  # 13カラム × 5走
    past_cols_found = len([k for k in row_keys if k.startswith('past_')])
    
    print(f"\n📊 過去走カラム:")
    print(f"   期待値: {past_cols_expected}")
    print(f"   実際: {past_cols_found}")
    
    if past_cols_found != past_cols_expected:
        print(f"   ⚠️  カラム数が一致しません")
    else:
        print(f"   ✅ OK")
    
    # 血統カラムチェック
    pedigree_cols = ["father", "mother", "bms"]
    missing_pedigree = []
    for col in pedigree_cols:
        if col not in row_keys:
            missing_pedigree.append(col)
    
    print(f"\n📊 血統カラム:")
    if missing_pedigree:
        print(f"   ⚠️  欠落: {missing_pedigree}")
    else:
        print(f"   ✅ OK (3カラム)")
    
    # 総合判定
    total_expected = 26 + 65 + 3  # 94
    total_found = len(row_keys)
    
    print(f"\n{'='*80}")
    print(f"📊 総合結果:")
    print(f"   期待カラム数: {total_expected}")
    print(f"   実際のキー数: {total_found}")
    
    if total_found == total_expected and not missing_basic and not missing_pedigree:
        print(f"   ✅ カラム整合性: OK")
        return True
    else:
        print(f"   ⚠️  カラム整合性: 問題あり")
        return False

if __name__ == "__main__":
    print("🔍 一括スクレイピングノートブックのカラム整合性検証\n")
    
    notebooks = [
        ("/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Scraping.ipynb", "JRA一括スクレイピング"),
        ("/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Scraping.ipynb", "NAR一括スクレイピング"),
    ]
    
    results = {}
    for nb_path, nb_name in notebooks:
        results[nb_name] = verify_notebook_columns(nb_path, nb_name)
    
    print(f"\n{'='*80}")
    print("📊 最終結果")
    print(f"{'='*80}\n")
    
    for nb_name, result in results.items():
        status = "✅ OK" if result else "❌ 問題あり"
        print(f"  {nb_name}: {status}")
    
    if all(results.values()):
        print(f"\n✅ すべてのノートブックでカラム整合性が確認されました")
    else:
        print(f"\n⚠️  一部のノートブックに問題があります")
