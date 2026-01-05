
import pandas as pd
import os
from datetime import datetime

def check_max_date():
    path = 'data/raw/database_nar.parquet'
    if os.path.exists(path):
        df = pd.read_parquet(path)
        
        # Parse JRA timestamps
        def parse_date(s):
            try:
                import re
                match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(s))
                if match:
                    return pd.Timestamp(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                return pd.to_datetime(s, errors='coerce')
            except:
                return pd.NaT

        df['date'] = df['日付'].apply(parse_date)
        max_date = df['date'].max()
        print(f"Max Date in DB: {max_date}")
        print(f"Current System Time: {datetime.now()}")
    else:
        print("database.parquet not found")

if __name__ == "__main__":
    check_max_date()
