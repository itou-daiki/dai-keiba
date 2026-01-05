
import pandas as pd
import pickle
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.feature_engineering import process_data

def debug_inference():
    print("Loading Stats...")
    stats_path = "ml/models/feature_stats_nar.pkl"
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    
    print("Stats Keys:", list(stats.keys())) # Check for hj_compatibility
    
    print("Loading Raw Data...")
    df = pd.read_csv("data/raw/database_nar.csv", nrows=100)
    
    print("Running process_data...")
    try:
        processed_df = process_data(df, input_stats=stats)
        print("Columns:", processed_df.columns.tolist())
        
        if 'jockey_compatibility' in processed_df.columns:
            print("\nJockey Compatibility (First 20):")
            print(processed_df['jockey_compatibility'].head(20))
            print("\nStats:")
            print(processed_df['jockey_compatibility'].describe())
            
            # Inspect Keys
            hj_stats = stats.get('hj_compatibility', {})
            if hj_stats:
                print("\nStats Keys (First 5):", list(hj_stats.keys())[:5])
                
                # Manual Key Generation Check
                print("\n--- Manual Key Check ---")
                def clean_id(val):
                    try: return str(int(float(val)))
                    except: return str(val)
                def clean_j(val):
                     import re
                     val = str(val)
                     val = re.sub(r'[▲△☆◇★\d]', '', val)
                     return val.replace(" ", "").replace("　", "").strip()

                df['h_key_debug'] = df['horse_id'].apply(clean_id)
                df['j_key_debug'] = df['騎手'].apply(clean_j)
                df['hj_key_debug'] = df['h_key_debug'] + '_' + df['j_key_debug']
                
                print("Generated Keys (First 5):")
                print(df['hj_key_debug'].head(5).tolist())
                
                print("\nMatching Check:")
                for k in df['hj_key_debug'].head(20):
                    found = k in hj_stats
                    print(f"Key: {k} -> Found: {found}")
                    if found:
                        print(f"   Value: {hj_stats[k]}")
            else:
                print("hj_compatibility stats MISSING")

        else:
            print("❌ 'jockey_compatibility' column MISSING from output!")


            
    except Exception as e:
        print(f"❌ Error during process_data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_inference()
