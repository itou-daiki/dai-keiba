import pandas as pd
import os
import sys

def backfill_rotation():
    # Path to database.csv
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(project_root, "data", "raw", "database.csv")
    
    if not os.path.exists(csv_path):
        print("Error: database.csv not found.")
        return

    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path, dtype=str) # Read all as str to preserve layout
    
    if '回り' not in df.columns:
        print("Adding '回り' column...")
        df['回り'] = ""
    
    # Heuristic Logic
    def get_rotation(row):
        # If already present, keep it (unless empty)
        val = str(row.get('回り', ''))
        if val and val != "nan" and val.strip():
            return val
            
        venue = str(row.get('会場', ''))
        distance = str(row.get('距離', ''))
        course = str(row.get('コースタイプ', ''))
        
        try:
            dist_int = int(float(distance)) if distance and distance != 'nan' else 0
        except:
            dist_int = 0
            
        # Left Handed Venues
        if venue in ["東京", "中京"]:
            return "左"
            
        # Niigata is Left but has Straight 1000m
        if venue == "新潟":
            if dist_int == 1000 and "芝" in course:
                return "直線"
            return "左"
            
        # Others are generally Right
        if venue in ["札幌", "函館", "福島", "中山", "京都", "阪神", "小倉"]:
             return "右"
             
        return "" # Unknown or NAR mixed in?

    print("Backfilling '回り' data...")
    # Apply logic
    df['回り'] = df.apply(get_rotation, axis=1)
    
    # Save
    print("Saving updated CSV...")
    df.to_csv(csv_path, index=False)
    print("Success!")

if __name__ == "__main__":
    backfill_rotation()
