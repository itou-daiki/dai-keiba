
import pickle
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def inspect_stats(mode="JRA"):
    file_name = "feature_stats_nar.pkl" if mode == "NAR" else "feature_stats.pkl"
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "models", file_name)
    
    print(f"Inspecting {path}...")
    if not os.path.exists(path):
        print("File not found!")
        return

    try:
        with open(path, 'rb') as f:
            stats = pickle.load(f)
            
        print(f"Stats Keys: {list(stats.keys())}")
        
        check_keys = ['horse_turf', 'horse_dirt', 'horse_dist_Mile']
        for k in check_keys:
            if k in stats:
                print(f"  {k}: {len(stats[k])} items")
                # Print first 3 items
                print(f"    Sample: {list(stats[k].items())[:3]}")
                keys_list = list(stats[k].keys())
                print(f"    Key Type: {type(keys_list[0])} (Example: '{keys_list[0]}')")
            else:
                print(f"  {k}: MISSING")
                
    except Exception as e:
        print(f"Error loading pickle: {e}")

if __name__ == "__main__":
    print("--- JRA ---")
    inspect_stats("JRA")
    print("\n--- NAR ---")
    inspect_stats("NAR")
