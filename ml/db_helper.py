"""
SQLiteデータベースヘルパーモジュール

Colab環境で生成したSQLiteデータベースを読み書きするための関数群
"""

import sqlite3
import pandas as pd
import os
from typing import Optional, List, Dict, Any


class KeibaDatabase:
    """競馬データベース管理クラス"""

    def __init__(self, db_path: str = "keiba_data.db"):
        """
        Args:
            db_path: SQLiteデータベースのパス
        """
        self.db_path = db_path

        if not os.path.exists(db_path):
            raise FileNotFoundError(
                f"データベースファイルが見つかりません: {db_path}\n"
                "Google Colabで colab_data_pipeline.ipynb を実行してデータベースを作成してください。"
            )

    def get_connection(self) -> sqlite3.Connection:
        """データベース接続を取得"""
        return sqlite3.connect(self.db_path)

    def get_processed_data(self, mode: str = "JRA", limit: Optional[int] = None) -> pd.DataFrame:
        """
        処理済みデータを取得

        Args:
            mode: "JRA" または "NAR"
            limit: 取得する最大レコード数（Noneの場合は全件）

        Returns:
            処理済みデータのDataFrame
        """
        table_name = f"processed_data_{mode.lower()}"

        query = f"SELECT * FROM {table_name}"
        if limit:
            query += f" LIMIT {limit}"

        conn = self.get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def get_race_data(self, race_id: str, mode: str = "JRA") -> pd.DataFrame:
        """
        特定のレースのデータを取得

        Args:
            race_id: レースID
            mode: "JRA" または "NAR"

        Returns:
            レースデータのDataFrame
        """
        table_name = f"processed_data_{mode.lower()}"

        query = f"SELECT * FROM {table_name} WHERE race_id = ?"

        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=(race_id,))
        conn.close()

        return df

    def get_horse_history(self, horse_id: str, mode: str = "JRA", limit: int = 10) -> pd.DataFrame:
        """
        特定の馬の過去データを取得

        Args:
            horse_id: 馬ID
            mode: "JRA" または "NAR"
            limit: 取得する最大レコード数

        Returns:
            馬の過去データのDataFrame
        """
        table_name = f"processed_data_{mode.lower()}"

        query = f"""
            SELECT * FROM {table_name}
            WHERE horse_id = ?
            ORDER BY date DESC
            LIMIT ?
        """

        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=(horse_id, limit))
        conn.close()

        return df

    def get_statistics(self, mode: str = "JRA") -> Dict[str, Any]:
        """
        データベースの統計情報を取得

        Args:
            mode: "JRA" または "NAR"

        Returns:
            統計情報の辞書
        """
        table_name = f"processed_data_{mode.lower()}"

        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT race_id) as unique_races,
                COUNT(DISTINCT horse_id) as unique_horses,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                AVG(target_win) as win_rate
            FROM {table_name}
        """

        conn = self.get_connection()
        result = pd.read_sql_query(query, conn)
        conn.close()

        return result.iloc[0].to_dict()

    def get_feature_names(self, mode: str = "JRA") -> List[str]:
        """
        特徴量の列名リストを取得

        Args:
            mode: "JRA" または "NAR"

        Returns:
            列名のリスト
        """
        table_name = f"processed_data_{mode.lower()}"

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        return columns

    def get_latest_update(self, mode: str = "JRA") -> Optional[str]:
        """
        最新データの日付を取得

        Args:
            mode: "JRA" または "NAR"

        Returns:
            最新データの日付（YYYY-MM-DD形式）
        """
        table_name = f"processed_data_{mode.lower()}"

        query = f"SELECT MAX(date) as latest_date FROM {table_name}"

        conn = self.get_connection()
        result = pd.read_sql_query(query, conn)
        conn.close()

        latest = result['latest_date'].iloc[0]
        return latest if pd.notna(latest) else None

    def get_data_freshness(self, mode: str = "JRA") -> str:
        """
        データの鮮度情報を取得（表示用）

        Args:
            mode: "JRA" または "NAR"

        Returns:
            鮮度情報の文字列
        """
        from datetime import datetime

        latest = self.get_latest_update(mode)
        if not latest:
            return "データなし"

        # 日付の解析
        try:
            latest_date = pd.to_datetime(latest)
            today = pd.Timestamp.now()
            days_old = (today - latest_date).days

            if days_old == 0:
                return f"最新（今日）"
            elif days_old == 1:
                return f"1日前"
            elif days_old <= 7:
                return f"{days_old}日前"
            elif days_old <= 30:
                weeks = days_old // 7
                return f"{weeks}週間前"
            else:
                months = days_old // 30
                return f"{months}ヶ月前"
        except:
            return latest

    def execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """
        カスタムクエリを実行
        
        Args:
            query: SQLクエリ
            params: クエリパラメータ
            
        Returns:
            クエリ結果のDataFrame
        """
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df

    def save_processed_data(self, df: pd.DataFrame, mode: str = "JRA"):
        """
        処理済みデータを保存
        
        Args:
            df: 保存するDataFrame
            mode: "JRA" または "NAR"
        """
        table_name = f"processed_data_{mode.lower()}"
        conn = self.get_connection()
        
        # Save to SQL
        df.to_sql(table_name, conn, if_exists='replace', index=False, chunksize=1000)
        
        # Create indices for speed
        cursor = conn.cursor()
        indices = ['race_id', 'horse_id', 'date']
        for idx in indices:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{idx} ON {table_name}({idx})")
            except Exception as e:
                print(f"Index creation failed for {idx}: {e}")
        
        conn.commit()
        conn.close()


# 便利関数
def get_training_data(mode: str = "JRA", db_path: str = "keiba_data.db") -> pd.DataFrame:
    """
    学習用データを取得（簡易版）

    Args:
        mode: "JRA" または "NAR"
        db_path: データベースパス

    Returns:
        学習用データのDataFrame
    """
    db = KeibaDatabase(db_path)
    return db.get_processed_data(mode)


def get_data_stats(mode: str = "JRA", db_path: str = "keiba_data.db") -> Dict[str, Any]:
    """
    データ統計情報を取得（簡易版）

    Args:
        mode: "JRA" または "NAR"
        db_path: データベースパス

    Returns:
        統計情報の辞書
    """
    db = KeibaDatabase(db_path)
    return db.get_statistics(mode)


if __name__ == "__main__":
    # テスト実行
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "keiba_data.db"

    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        print("Google Colabで colab_data_pipeline.ipynb を実行してデータベースを作成してください。")
        sys.exit(1)

    db = KeibaDatabase(db_path)

    print("=" * 60)
    print("データベース統計情報")
    print("=" * 60)

    for mode in ["JRA", "NAR"]:
        try:
            print(f"\n📊 {mode}:")
            stats = db.get_statistics(mode)
            print(f"   総レコード数: {stats['total_records']:,}")
            print(f"   ユニークレース数: {stats['unique_races']:,}")
            print(f"   ユニーク馬数: {stats['unique_horses']:,}")
            print(f"   データ期間: {stats['earliest_date']} ～ {stats['latest_date']}")
            print(f"   勝率: {stats['win_rate']:.2%}")
            print(f"   鮮度: {db.get_data_freshness(mode)}")
        except Exception as e:
            print(f"   ❌ エラー: {e}")
