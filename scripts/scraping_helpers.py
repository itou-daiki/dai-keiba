"""
最適化されたスクレイピングヘルパー関数
Colab JRA/NAR スクレイピングノートブックで使用
"""

import pandas as pd
import gc
import os
import shutil
from typing import Set, Optional


def deduplicate_in_chunks(csv_path: str, chunk_size: int = 10000) -> None:
    """
    チャンク単位で重複削除を実行(メモリ効率的)
    
    Args:
        csv_path: 重複削除対象のCSVファイルパス
        chunk_size: 一度に処理する行数
    """
    if not os.path.exists(csv_path):
        print(f"  ⚠️  ファイルが存在しません: {csv_path}")
        return
    
    print(f"  🔄 チャンク単位で重複削除中... (chunk_size={chunk_size})")
    
    seen: Set[str] = set()
    temp_path = csv_path + '.tmp'
    
    try:
        # ヘッダーを取得
        headers = pd.read_csv(csv_path, nrows=0).columns.tolist()
        
        if 'race_id' not in headers or 'horse_id' not in headers:
            print("  ⚠️  race_id または horse_id カラムが見つかりません")
            return
        
        # チャンクごとに処理
        first_chunk = True
        total_rows = 0
        unique_rows = 0
        
        for chunk in pd.read_csv(csv_path, dtype=str, chunksize=chunk_size, low_memory=False):
            total_rows += len(chunk)
            
            # 重複チェック用のキーを作成
            chunk['_key'] = chunk['race_id'].fillna('') + '_' + chunk['horse_id'].fillna('')
            
            # 既に見たキーを除外
            chunk_dedup = chunk[~chunk['_key'].isin(seen)]
            
            # 見たキーを記録
            seen.update(chunk_dedup['_key'].tolist())
            unique_rows += len(chunk_dedup)
            
            # 一時ファイルに書き込み
            chunk_dedup = chunk_dedup.drop('_key', axis=1)
            chunk_dedup.to_csv(temp_path, mode='a', header=first_chunk, index=False)
            first_chunk = False
            
            # メモリ解放
            del chunk, chunk_dedup
            gc.collect()
        
        # 元ファイルを置き換え
        shutil.move(temp_path, csv_path)
        
        duplicates = total_rows - unique_rows
        print(f"  ✅ 重複削除完了: {total_rows} → {unique_rows} rows ({duplicates} duplicates removed)")
        
    except Exception as e:
        print(f"  ❌ 重複削除エラー: {e}")
        # 一時ファイルを削除
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def check_memory_usage() -> float:
    """
    現在のメモリ使用量を確認(MB単位)
    
    Returns:
        メモリ使用量(MB)
    """
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / 1024 / 1024
        return mem_mb
    except ImportError:
        # psutilがない場合はスキップ
        return 0.0


def log_memory(label: str = "", threshold_mb: float = 10000) -> None:
    """
    メモリ使用量をログ出力し、閾値を超えたら警告
    
    Args:
        label: ログのラベル
        threshold_mb: 警告を出すメモリ閾値(MB)
    """
    mem_mb = check_memory_usage()
    
    if mem_mb > 0:
        status = "⚠️" if mem_mb > threshold_mb else "💾"
        print(f"  {status} Memory: {mem_mb:.1f} MB {label}")
        
        if mem_mb > threshold_mb:
            print(f"  ⚠️  メモリ使用量が高い! GC実行...")
            gc.collect()


class HorseHistoryCache:
    """
    馬の履歴データをキャッシュするクラス
    同じ馬の重複取得を回避してメモリとネットワークを節約
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Args:
            max_size: キャッシュの最大サイズ
        """
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, horse_id: str, race_date: str) -> Optional[pd.DataFrame]:
        """
        キャッシュから履歴を取得
        
        Args:
            horse_id: 馬ID
            race_date: レース日付
            
        Returns:
            キャッシュされた履歴DataFrame、なければNone
        """
        cache_key = f"{horse_id}_{race_date}"
        
        if cache_key in self.cache:
            self.hits += 1
            return self.cache[cache_key].copy()
        
        self.misses += 1
        return None
    
    def put(self, horse_id: str, race_date: str, df: pd.DataFrame) -> None:
        """
        履歴をキャッシュに保存
        
        Args:
            horse_id: 馬ID
            race_date: レース日付
            df: 履歴DataFrame
        """
        cache_key = f"{horse_id}_{race_date}"
        
        # キャッシュサイズ制限
        if len(self.cache) >= self.max_size:
            # 最も古いエントリを削除(FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = df.copy()
    
    def stats(self) -> str:
        """
        キャッシュ統計を返す
        
        Returns:
            統計文字列
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return f"Cache: {len(self.cache)} entries, Hit rate: {hit_rate:.1f}% ({self.hits}/{total})"


def fetch_with_retry(url: str, headers: dict, max_retries: int = 3, timeout: int = 15) -> Optional[object]:
    """
    リトライロジック付きでHTTPリクエストを実行
    
    Args:
        url: リクエストURL
        headers: HTTPヘッダー
        max_retries: 最大リトライ回数
        timeout: タイムアウト(秒)
        
    Returns:
        レスポンスオブジェクト、失敗時はNone
    """
    import requests
    import time
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            
            # レート制限検知
            if resp.status_code == 403 or resp.status_code == 429:
                wait_time = (2 ** attempt) * 5  # 指数バックオフ: 5秒, 10秒, 20秒
                print(f"  ⚠️  レート制限検知 (Status {resp.status_code}). {wait_time}秒待機...")
                time.sleep(wait_time)
                continue
            
            if resp.status_code == 200:
                return resp
            
            # その他のエラー
            print(f"  ⚠️  HTTP Error {resp.status_code} (attempt {attempt + 1}/{max_retries})")
            
        except requests.exceptions.Timeout:
            print(f"  ⚠️  Timeout (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Request Error: {e} (attempt {attempt + 1}/{max_retries})")
        
        # リトライ前に待機
        if attempt < max_retries - 1:
            time.sleep(2)
    
    print(f"  ❌ Failed after {max_retries} attempts: {url}")
    return None


def safe_append_csv_optimized(df_chunk: pd.DataFrame, path: str) -> None:
    """
    最適化されたCSV追記関数
    
    Args:
        df_chunk: 追記するDataFrame
        path: CSVファイルパス
    """
    if not os.path.exists(path):
        # 新規作成
        df_chunk.to_csv(path, index=False)
    else:
        try:
            # カラム順序を既存ファイルに合わせる
            headers = pd.read_csv(path, nrows=0).columns.tolist()
            df_aligned = df_chunk.reindex(columns=headers, fill_value='')
            df_aligned.to_csv(path, mode='a', header=False, index=False)
        except Exception as e:
            print(f"  ⚠️  カラム整列失敗、そのまま追記: {e}")
            df_chunk.to_csv(path, mode='a', header=False, index=False)
