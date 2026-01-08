#!/usr/bin/env python3
"""
追加の不要なファイルを削除
"""

import os
import shutil
from pathlib import Path

base_dir = "/Users/itoudaiki/Program/dai-keiba"

# 追加の不要なファイル
ADDITIONAL_CLEANUP = {
    "Pythonキャッシュ": [
        "__pycache__",
        "*.pyc",
    ],
    "システムファイル": [
        ".DS_Store",
        ".nojekyll",
    ],
    "ログファイル": [
        "ml/training.log",
    ],
    "不要な設定ファイル": [
        "packages.txt",
    ],
    "古いスクリプト": [
        "scripts/colab_backfill_helper.py",
        "scripts/colab_data_filler.py",
        "scripts/scraping_logic_v2.py",
        "scripts/smart_id_generator.py",
        "scripts/create_nar_details.py",
        "scripts/enable_venue_features.py",
    ],
    "クリーンアップスクリプト(使用済み)": [
        "scripts/cleanup_project.py",
        "scripts/delete_unnecessary_files.py",
    ],
}

def find_and_delete(base_dir, patterns):
    """パターンに一致するファイルを検索・削除"""
    from glob import glob
    
    deleted = []
    total_size = 0
    
    for pattern in patterns:
        # __pycache__ディレクトリの処理
        if pattern == "__pycache__":
            for root, dirs, files in os.walk(base_dir):
                if "__pycache__" in dirs:
                    pycache_path = os.path.join(root, "__pycache__")
                    try:
                        size = sum(os.path.getsize(os.path.join(pycache_path, f)) 
                                  for f in os.listdir(pycache_path) if os.path.isfile(os.path.join(pycache_path, f)))
                        shutil.rmtree(pycache_path)
                        rel_path = os.path.relpath(pycache_path, base_dir)
                        deleted.append((rel_path, size))
                        total_size += size
                    except Exception as e:
                        print(f"  ❌ エラー: {pycache_path} - {e}")
        else:
            # 通常のファイルパターン
            full_pattern = os.path.join(base_dir, "**", pattern) if "*" in pattern else os.path.join(base_dir, pattern)
            matched = glob(full_pattern, recursive=True)
            
            for filepath in matched:
                if os.path.isfile(filepath):
                    try:
                        size = os.path.getsize(filepath)
                        os.remove(filepath)
                        rel_path = os.path.relpath(filepath, base_dir)
                        deleted.append((rel_path, size))
                        total_size += size
                    except Exception as e:
                        print(f"  ❌ エラー: {filepath} - {e}")
    
    return deleted, total_size

print("🗑️  追加の不要なファイルを削除中...\n")

all_deleted = []
grand_total = 0

for category, patterns in ADDITIONAL_CLEANUP.items():
    print(f"📁 {category}")
    print(f"{'─'*80}")
    
    deleted, total_size = find_and_delete(base_dir, patterns)
    
    for filepath, size in deleted:
        print(f"  ✅ 削除: {filepath} ({size/1024:.1f}KB)")
        all_deleted.append((filepath, size))
        grand_total += size
    
    if not deleted:
        print(f"  (該当なし)")
    
    print()

print(f"{'='*80}")
print(f"✅ 追加削除完了")
print(f"{'='*80}")
print(f"削除ファイル数: {len(all_deleted)}")
print(f"解放容量: {grand_total/1024:.1f}KB")
