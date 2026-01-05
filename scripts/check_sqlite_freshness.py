
import sys
import os
sys.path.append(os.getcwd())
from ml.db_helper import KeibaDatabase

def check_sqlite():
    db_path = "db/keiba_data.db"
    if not os.path.exists(db_path):
        print(f"{db_path} not found.")
        return

    db = KeibaDatabase(db_path)
    print("Checking JRA Freshness via SQLite...")
    try:
        freshness = db.get_data_freshness("JRA")
        latest = db.get_latest_update("JRA")
        print(f"Latest Date: {latest}")
        print(f"Display String: {freshness}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sqlite()
