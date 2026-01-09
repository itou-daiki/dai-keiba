#!/usr/bin/env python3
"""
JRA Basic v2に堅牢なエラーハンドリングを追加
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
            
            # テーブル検出失敗時のログを改善
            old_error_msg = """        if not result_table:
            print(f"  ⚠️ レース結果テーブルが見つかりません: {race_id}")
            return None"""
            
            new_error_msg = """        if not result_table:
            print(f"  ⚠️ レース結果テーブルが見つかりません: {race_id}")
            print(f"     URL: {url}")
            print(f"     総テーブル数: {len(tables)}")
            # レスポンスの一部を表示(デバッグ用)
            if len(soup.text) < 100:
                print(f"     ページ内容が少なすぎます(レート制限の可能性)")
            return None"""
            
            source = source.replace(old_error_msg, new_error_msg)
            
            # HTTPエラーのハンドリングを追加
            old_try_block = """    try:
        # ページ取得
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')"""
            
            new_try_block = """    try:
        # ページ取得
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        
        # HTTPステータスチェック
        if resp.status_code != 200:
            print(f"  ⚠️ HTTP {resp.status_code}: {race_id}")
            return None
        
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')"""
            
            source = source.replace(old_try_block, new_try_block)
            
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source'] and cell['source'][-1] == '\n':
                cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            print("  ✅ エラーハンドリングを強化")
            print("  ✅ HTTPステータスチェックを追加")
            print("  ✅ デバッグ情報を追加")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n💾 保存完了: {notebook_path}")
print("\n📝 改善内容:")
print("  - HTTPステータスコードチェック")
print("  - テーブル検出失敗時の詳細ログ")
print("  - レート制限検出")
