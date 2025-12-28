
import pickle
import os
import sys

def verify_keys():
    pkl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml/models/feature_stats.pkl")
    if not os.path.exists(pkl_path):
        print(f"File not found: {pkl_path}")
        return

    print(f"Loading {pkl_path}...")
    with open(pkl_path, 'rb') as f:
        stats = pickle.load(f)

    # Check hj_compatibility
    if 'hj_compatibility' in stats:
        keys = list(stats['hj_compatibility'].keys())
        print(f"Total hj_compatibility keys: {len(keys)}")
        print("Sample keys (First 10):")
        for k in keys[:10]:
            print(f"  '{k}'")
            
        # Check for dirty patterns
        dirty_dot_zero = [k for k in keys if ".0_" in k]
        dirty_spaces = [k for k in keys if " " in k.split('_')[-1]] # Space in jockey name part
        
        if dirty_dot_zero:
            print(f"\n⚠️  WARNING: Found {len(dirty_dot_zero)} keys with '.0_' pattern (Float String ID mismatch)!")
            print(f"  Example: {dirty_dot_zero[0]}")
        else:
            print("\n✅ No '.0_' keys found. IDs seem clean.")
            
        if dirty_spaces:
            print(f"\n⚠️  WARNING: Found {len(dirty_spaces)} keys with spaces in Jockey Name!")
            print(f"  Example: {dirty_spaces[0]}")
        else:
            print("\n✅ No spaces in Jockey Names found.")
            
    else:
        print("hj_compatibility key MISSING in stats!")

if __name__ == "__main__":
    verify_keys()
