#!/usr/bin/env python3
"""
Colabノートブックに最適化コードを注入するスクリプト
"""

import json
import sys
from pathlib import Path

def inject_optimizations(notebook_path: str, output_path: str = None):
    """
    ノートブックに最適化コードを注入
    
    Args:
        notebook_path: 元のノートブックパス
        output_path: 出力先(Noneの場合は上書き)
    """
    if output_path is None:
        output_path = notebook_path
    
    # ノートブックを読み込み
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # 最適化ヘルパー関数セルを作成
    helper_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 🚀 最適化ヘルパー関数\\n",
            "import pandas as pd\\n",
            "import gc\\n",
            "import os\\n",
            "import shutil\\n",
            "from typing import Set, Optional\\n",
            "\\n",
            "# psutilのインストール\\n",
            "try:\\n",
            "    import psutil\\n",
            "except ImportError:\\n",
            "    !pip install -q psutil\\n",
            "    import psutil\\n",
            "\\n",
            "def check_memory_usage() -> float:\\n",
            "    \\\"\\\"\\\"現在のメモリ使用量を確認(MB単位)\\\"\\\"\\\"\\n",
            "    process = psutil.Process(os.getpid())\\n",
            "    return process.memory_info().rss / 1024 / 1024\\n",
            "\\n",
            "def log_memory(label: str = \\\"\\\", threshold_mb: float = 10000) -> None:\\n",
            "    \\\"\\\"\\\"メモリ使用量をログ出力\\\"\\\"\\\"\\n",
            "    mem_mb = check_memory_usage()\\n",
            "    status = \\\"⚠️\\\" if mem_mb > threshold_mb else \\\"💾\\\"\\n",
            "    print(f\\\"  {status} Memory: {mem_mb:.1f} MB {label}\\\")\\n",
            "    if mem_mb > threshold_mb:\\n",
            "        print(f\\\"  ⚠️  メモリ使用量が高い! GC実行...\\\")\\n",
            "        gc.collect()\\n",
            "\\n",
            "class HorseHistoryCache:\\n",
            "    \\\"\\\"\\\"馬の履歴データをキャッシュ\\\"\\\"\\\"\\n",
            "    def __init__(self, max_size: int = 1000):\\n",
            "        self.cache = {}\\n",
            "        self.max_size = max_size\\n",
            "        self.hits = 0\\n",
            "        self.misses = 0\\n",
            "    \\n",
            "    def get(self, horse_id: str, race_date: str) -> Optional[pd.DataFrame]:\\n",
            "        cache_key = f\\\"{horse_id}_{race_date}\\\"\\n",
            "        if cache_key in self.cache:\\n",
            "            self.hits += 1\\n",
            "            return self.cache[cache_key].copy()\\n",
            "        self.misses += 1\\n",
            "        return None\\n",
            "    \\n",
            "    def put(self, horse_id: str, race_date: str, df: pd.DataFrame) -> None:\\n",
            "        cache_key = f\\\"{horse_id}_{race_date}\\\"\\n",
            "        if len(self.cache) >= self.max_size:\\n",
            "            oldest_key = next(iter(self.cache))\\n",
            "            del self.cache[oldest_key]\\n",
            "        self.cache[cache_key] = df.copy()\\n",
            "    \\n",
            "    def stats(self) -> str:\\n",
            "        total = self.hits + self.misses\\n",
            "        hit_rate = (self.hits / total * 100) if total > 0 else 0\\n",
            "        return f\\\"Cache: {len(self.cache)} entries, Hit rate: {hit_rate:.1f}% ({self.hits}/{total})\\\"\\n",
            "\\n",
            "def fetch_with_retry(url: str, headers: dict, max_retries: int = 3) -> Optional[object]:\\n",
            "    \\\"\\\"\\\"リトライロジック付きHTTPリクエスト\\\"\\\"\\\"\\n",
            "    import requests\\n",
            "    import time\\n",
            "    for attempt in range(max_retries):\\n",
            "        try:\\n",
            "            resp = requests.get(url, headers=headers, timeout=15)\\n",
            "            if resp.status_code in [403, 429]:\\n",
            "                wait_time = (2 ** attempt) * 5\\n",
            "                print(f\\\"  ⚠️  レート制限 (Status {resp.status_code}). {wait_time}秒待機...\\\")\\n",
            "                time.sleep(wait_time)\\n",
            "                continue\\n",
            "            if resp.status_code == 200:\\n",
            "                return resp\\n",
            "        except requests.exceptions.Timeout:\\n",
            "            print(f\\\"  ⚠️  Timeout (attempt {attempt + 1}/{max_retries})\\\")\\n",
            "        except requests.exceptions.RequestException as e:\\n",
            "            print(f\\\"  ⚠️  Request Error: {e}\\\")\\n",
            "        if attempt < max_retries - 1:\\n",
            "            time.sleep(2)\\n",
            "    return None\\n",
            "\\n",
            "def deduplicate_in_chunks(csv_path: str, chunk_size: int = 10000) -> None:\\n",
            "    \\\"\\\"\\\"チャンク単位で重複削除(メモリ効率的)\\\"\\\"\\\"\\n",
            "    if not os.path.exists(csv_path):\\n",
            "        return\\n",
            "    print(f\\\"  🔄 チャンク単位で重複削除中... (chunk_size={chunk_size})\\\")\\n",
            "    seen: Set[str] = set()\\n",
            "    temp_path = csv_path + '.tmp'\\n",
            "    try:\\n",
            "        headers = pd.read_csv(csv_path, nrows=0).columns.tolist()\\n",
            "        if 'race_id' not in headers or 'horse_id' not in headers:\\n",
            "            print(\\\"  ⚠️  race_id または horse_id カラムが見つかりません\\\")\\n",
            "            return\\n",
            "        first_chunk = True\\n",
            "        total_rows = 0\\n",
            "        unique_rows = 0\\n",
            "        for chunk in pd.read_csv(csv_path, dtype=str, chunksize=chunk_size, low_memory=False):\\n",
            "            total_rows += len(chunk)\\n",
            "            chunk['_key'] = chunk['race_id'].fillna('') + '_' + chunk['horse_id'].fillna('')\\n",
            "            chunk_dedup = chunk[~chunk['_key'].isin(seen)]\\n",
            "            seen.update(chunk_dedup['_key'].tolist())\\n",
            "            unique_rows += len(chunk_dedup)\\n",
            "            chunk_dedup = chunk_dedup.drop('_key', axis=1)\\n",
            "            chunk_dedup.to_csv(temp_path, mode='a', header=first_chunk, index=False)\\n",
            "            first_chunk = False\\n",
            "            del chunk, chunk_dedup\\n",
            "            gc.collect()\\n",
            "        shutil.move(temp_path, csv_path)\\n",
            "        duplicates = total_rows - unique_rows\\n",
            "        print(f\\\"  ✅ 重複削除完了: {total_rows} → {unique_rows} rows ({duplicates} duplicates removed)\\\")\\n",
            "    except Exception as e:\\n",
            "        print(f\\\"  ❌ 重複削除エラー: {e}\\\")\\n",
            "        if os.path.exists(temp_path):\\n",
            "            os.remove(temp_path)\\n",
            "\\n",
            "# グローバルキャッシュを初期化\\n",
            "horse_cache = HorseHistoryCache()\\n",
            "\\n",
            "print(\\\"✅ 最適化ヘルパー関数がロードされました\\\")\\n"
        ]
    }
    
    # セル3(インデックス2)の後に挿入
    nb['cells'].insert(3, helper_cell)
    
    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    
    print(f"✅ 最適化コードを注入しました: {output_path}")
    print(f"   総セル数: {len(nb['cells'])}")

if __name__ == "__main__":
    # JRAノートブック
    jra_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Scraping.ipynb"
    inject_optimizations(jra_path)
    
    # NARノートブック
    nar_path = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Scraping.ipynb"
    inject_optimizations(nar_path)
    
    print("\\n✅ 両方のノートブックに最適化コードを注入しました")
