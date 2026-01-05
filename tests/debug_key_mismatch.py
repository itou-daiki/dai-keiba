
import pandas as pd
import os
import sys

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_formats():
    print("--- Checking Key Formats ---")
    
    # 1. Database (Training Source)
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/raw/database.csv")
    if os.path.exists(db_path):
        df_db = pd.read_csv(db_path, nrows=5)
        print("\n[Database Raw Load]")
        print(df_db['horse_id'].head())
        print(f"Type: {df_db['horse_id'].dtype}")
        
        # Casting used in feature_engineering processing
        h_key_db = df_db['horse_id'].astype(str)
        print(f"Casted to str in ML pipeline: '{h_key_db.iloc[0]}'")
        
    # 2. Scraper Output (Inference Source)
    # Simulate what auto_scraper produces or load a sample
    # We can inspect todays_data.json if available
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/temp/todays_data.json")
    if(os.path.exists(json_path)):
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
            if 'races' in data and len(data['races']) > 0:
                print("\n[Scraper JSON]")
                # Shutuba data is fetched dynamically, but lets see if we can infer format
                # Usually scraper keeps IDs as pure strings from URL
                print(f"Race ID sample: {data['races'][0]['id']}")
                
    # 3. Check clean logic
    id_float = 2011106610.0
    id_str = "2011106610"
    print(f"\n[Comparison]")
    print(f"Float as str: '{str(id_float)}'")
    print(f"String as str: '{str(id_str)}'")
    
    # 4. Check Jockey Names
    print("\n[Jockey Name Check]")
    if os.path.exists(db_path):
        print("Database Sample:")
        print(df_db['騎手'].head())
        # Apply clean
        import re
        def clean_jockey(name):
            if not isinstance(name, str): return ""
            return re.sub(r'[▲△☆◇★\d]', '', name).strip()
            
        print("Database Cleaned:")
        print(df_db['騎手'].astype(str).apply(clean_jockey).head())

    # Check Scraper JSON jockey names if possible
    # (Simulated check based on common netkeiba issues)
    print("Scraper usually returns names like 'ルメール' or '武 豊'.")
    print("If DB has '武 豊' (space) and Scraper has '武豊' (no space), keys won't match.")

if __name__ == "__main__":
    check_formats()
