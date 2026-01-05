"""
SQLiteデータベース管理
CSVからの移行と高速クエリ機能
"""

import sqlite3
import pandas as pd
import os


class KeibaDatabase:
    """
    競馬データベース管理クラス
    """

    def __init__(self, db_path='dai_keiba.db'):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """データベースに接続"""
        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def close(self):
        """接続を閉じる"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def migrate_from_csv(self, csv_path):
        """
        CSVからSQLiteに移行

        Args:
            csv_path: CSVファイルのパス
        """
        if not os.path.exists(csv_path):
            print(f"CSV file {csv_path} not found.")
            return False

        print(f"📥 Loading CSV: {csv_path}")
        df = pd.read_csv(csv_path)

        print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")

        # Connect
        conn = self.connect()

        # Create table
        print("🔄 Migrating to SQLite...")
        df.to_sql('race_results', conn, if_exists='replace', index=False)

        # Create indexes for fast queries
        print("🔍 Creating indexes...")
        cursor = conn.cursor()

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_race_id ON race_results(race_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_horse_id ON race_results(horse_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON race_results(日付)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_venue ON race_results(会場)')

        if '馬名' in df.columns:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_horse_name ON race_results(馬名)')

        conn.commit()

        print("✅ Migration complete!")
        print(f"  Database: {self.db_path}")
        print(f"  Table: race_results ({len(df)} rows)")

        self.close()

        return True

    def query_race_data(self, race_id):
        """
        レースデータを取得

        Args:
            race_id: レースID

        Returns:
            DataFrame: レース結果
        """
        conn = self.connect()

        query = "SELECT * FROM race_results WHERE race_id = ?"
        df = pd.read_sql_query(query, conn, params=(race_id,))

        self.close()

        return df

    def query_horse_history(self, horse_id, limit=10):
        """
        馬の過去走データを取得

        Args:
            horse_id: 馬ID
            limit: 取得件数

        Returns:
            DataFrame: 過去走データ
        """
        conn = self.connect()

        query = """
            SELECT * FROM race_results
            WHERE horse_id = ?
            ORDER BY 日付 DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(horse_id, limit))

        self.close()

        return df

    def query_by_date_range(self, start_date, end_date):
        """
        日付範囲でデータ取得

        Args:
            start_date: 開始日 (例: '2025-01-01')
            end_date: 終了日

        Returns:
            DataFrame: データ
        """
        conn = self.connect()

        query = """
            SELECT * FROM race_results
            WHERE 日付 BETWEEN ? AND ?
            ORDER BY 日付 DESC
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))

        self.close()

        return df

    def query_by_venue(self, venue, limit=100):
        """
        会場別にデータ取得

        Args:
            venue: 会場名 (例: '中山', '東京')
            limit: 取得件数

        Returns:
            DataFrame: データ
        """
        conn = self.connect()

        query = """
            SELECT * FROM race_results
            WHERE 会場 = ?
            ORDER BY 日付 DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(venue, limit))

        self.close()

        return df

    def get_all_data(self):
        """
        全データを取得

        Returns:
            DataFrame: 全データ
        """
        conn = self.connect()

        df = pd.read_sql_query("SELECT * FROM race_results", conn)

        self.close()

        return df

    def get_statistics(self):
        """
        データベース統計を取得

        Returns:
            dict: 統計情報
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Total rows
        cursor.execute("SELECT COUNT(*) FROM race_results")
        total_rows = cursor.fetchone()[0]

        # Unique races
        cursor.execute("SELECT COUNT(DISTINCT race_id) FROM race_results")
        unique_races = cursor.fetchone()[0]

        # Unique horses
        cursor.execute("SELECT COUNT(DISTINCT horse_id) FROM race_results")
        unique_horses = cursor.fetchone()[0]

        # Date range
        cursor.execute("SELECT MIN(日付), MAX(日付) FROM race_results")
        date_range = cursor.fetchone()

        self.close()

        return {
            'total_rows': total_rows,
            'unique_races': unique_races,
            'unique_horses': unique_horses,
            'date_range': date_range
        }


def migrate_csv_to_sqlite(csv_path, db_path='dai_keiba.db'):
    """
    CSVをSQLiteに移行するヘルパー関数

    Args:
        csv_path: CSVファイルのパス
        db_path: データベースファイルのパス
    """
    db = KeibaDatabase(db_path)
    success = db.migrate_from_csv(csv_path)

    if success:
        # Show statistics
        stats = db.get_statistics()
        print("\n📊 Database Statistics:")
        print(f"  Total rows: {stats['total_rows']:,}")
        print(f"  Unique races: {stats['unique_races']:,}")
        print(f"  Unique horses: {stats['unique_horses']:,}")
        print(f"  Date range: {stats['date_range'][0]} ~ {stats['date_range'][1]}")

    return success


if __name__ == "__main__":
    # Test migration
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dai_keiba.db")

    print("🚀 Starting CSV to SQLite migration...")
    success = migrate_csv_to_sqlite(csv_path, db_path)

    if success:
        print("\n✅ Migration successful!")

        # Test query
        db = KeibaDatabase(db_path)
        print("\n🔍 Testing query (first race)...")
        df = db.get_all_data()
        if len(df) > 0:
            first_race_id = df['race_id'].iloc[0]
            race_data = db.query_race_data(first_race_id)
            print(f"  Race ID: {first_race_id}")
            print(f"  Horses: {len(race_data)}")
    else:
        print("\n❌ Migration failed")
