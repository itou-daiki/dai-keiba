import pandas as pd
import os
import sys
import pickle
import argparse
import joblib

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from ml.feature_engineering import process_data

def export_stats(mode="JRA", output_dir=None):
    """
    Load raw database, process features, and export statistical artifacts.
    """
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "ml", "models")
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Select DB
    if mode == "NAR":
        db_path = os.path.join(PROJECT_ROOT, "data", "raw", "database_nar.csv")
        suffix = "_nar"
    else:
        db_path = os.path.join(PROJECT_ROOT, "data", "raw", "database.csv")
        suffix = ""
        
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
        
    print(f"Loading {db_path}...")
    df = pd.read_csv(db_path)
    
    print("Processing data and calculating stats...")
    # enable venue features for full stats availability
    # return_stats=True gets the stats dictionary
    _, stats = process_data(df, use_venue_features=True, return_stats=True)
    
    # Save artifacts
    save_path = os.path.join(output_dir, f"feature_stats{suffix}.pkl")
    
    print(f"Saving statistics to {save_path}...")
    try:
        with open(save_path, 'wb') as f:
            pickle.dump(stats, f)
        print("Success! Stats exported.")
        
        # Print summary
        if 'jockey' in stats:
            print(f"  Jockeys: {len(stats['jockey']['win_rate'])}")
        if 'stable' in stats:
            print(f"  Stables: {len(stats['stable']['win_rate'])}")
        if 'course_horse' in stats:
            print(f"  Course-Horse Records: {len(stats['course_horse'])}")
            
        return True
    except Exception as e:
        print(f"Error saving stats: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="JRA", help="JRA or NAR")
    args = parser.parse_args()
    
    export_stats(args.mode)
