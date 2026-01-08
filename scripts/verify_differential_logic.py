import pandas as pd
import os
import shutil

# Mock Constants
DATA_DIR = 'data/test_differential'
DB_FILE = os.path.join(DATA_DIR, 'database.csv')
VERIFIED_FILE = os.path.join(DATA_DIR, 'race_ids.csv')

def setup_mocks():
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR)
    
    # Create a mock DB with:
    # Race A: Complete (Valid)
    # Race B: Incomplete (Missing Horse Name)
    
    data = [
        # Race A (Complete)
        {'race_id': '20250101', 'horse_id': 'h1', 'horse_name': 'Horse A1', 'rank': 1, 'jockey': 'J1', 'date': '2025-01-01'},
        {'race_id': '20250101', 'horse_id': 'h2', 'horse_name': 'Horse A2', 'rank': 2, 'jockey': 'J2', 'date': '2025-01-01'},
        # Race B (Broken - Missing Name)
        {'race_id': '20250102', 'horse_id': 'h3', 'horse_name': None,       'rank': 1, 'jockey': 'J3', 'date': '2025-01-02'}, 
        {'race_id': '20250102', 'horse_id': 'h4', 'horse_name': 'Horse B2', 'rank': 2, 'jockey': 'J4', 'date': '2025-01-02'},
    ]
    df = pd.DataFrame(data)
    df.to_csv(DB_FILE, index=False)
    print(f"✅ Created mock DB at {DB_FILE}")

def check_integrity(df_chunk):
    # Critical columns that must not be null
    CRITICAL_COLS = ['race_id', 'horse_id', 'horse_name', 'jockey', 'date', 'rank']
    
    # Check if cols exist
    missing_cols = [c for c in CRITICAL_COLS if c not in df_chunk.columns]
    if missing_cols:
        return False # Missing entire column
        
    # Check for NaNs in critical columns
    # Note: 'rank' might be non-numeric string, but shouldn't be NaN/None
    if df_chunk[CRITICAL_COLS].isnull().any().any():
        return False
        
    return True

def init_verified_cache(db_path, cache_path):
    verified_ids = set()
    
    # 1. Load Cache if exists
    if os.path.exists(cache_path):
        try:
            df_cache = pd.read_csv(cache_path, dtype=str)
            if 'race_id' in df_cache.columns:
                verified_ids = set(df_cache['race_id'].unique())
            print(f"📖 Loaded {len(verified_ids)} verified IDs from cache.")
        except:
            print("⚠️ Cache file corrupted or unreadable.")
            
    # 2. If DB exists, checking unverified legacy data
    if os.path.exists(db_path):
        print("🔍 Checking DB for valid races...")
        df = pd.read_csv(db_path, dtype=str)
        
        # Normalize columns if needed
        # (Mock already has correct cols)
        
        groups = df.groupby('race_id')
        new_verified = []
        for rid, group in groups:
            if rid in verified_ids:
                continue
                
            if check_integrity(group):
                verified_ids.add(rid)
                new_verified.append(rid)
            else:
                print(f"  ❌ Race {rid} is incomplete/corrupted. Needs re-scrape.")
        
        # Update cache if found new
        if new_verified:
            print(f"  ✨ Found {len(new_verified)} valid races in DB. Updating cache.")
            mode = 'a' if os.path.exists(cache_path) else 'w'
            pd.DataFrame({'race_id': new_verified}).to_csv(cache_path, mode=mode, header=(not os.path.exists(cache_path)), index=False)
            
    return verified_ids

def run_differential_logic():
    setup_mocks()
    
    # Step 1: Init Cache
    # Should mark Race A as verified, Race B as unverified
    verified_ids = init_verified_cache(DB_FILE, VERIFIED_FILE)
    
    print(f"Verified IDs: {verified_ids}")
    
    assert '20250101' in verified_ids, "Race A should be verified"
    assert '20250102' not in verified_ids, "Race B should NOT be verified (missing name)"
    
    # Step 2: Simulation Loop
    target_race_ids = ['20250101', '20250102', '20250103'] # A(Done), B(Broken), C(New)
    
    print("\n🚀 Starting Scraping Loop...")
    for rid in target_race_ids:
        if rid in verified_ids:
            print(f"⏭️ Skipping {rid} (Already Complete)")
            continue
            
        print(f"📥 Scraping {rid}...")
        
        # Mock Scrape Result
        # Scrape B (Fixing it) or C (New)
        if rid == '20250102':
             # Return Fixed Version
             new_data = [
                {'race_id': '20250102', 'horse_id': 'h3', 'horse_name': 'Horse A3 (Fixed)', 'rank': 1, 'jockey': 'J3', 'date': '2025-01-02'}, 
                {'race_id': '20250102', 'horse_id': 'h4', 'horse_name': 'Horse B2', 'rank': 2, 'jockey': 'J4', 'date': '2025-01-02'},
            ]
        elif rid == '20250103':
            # New Race
             new_data = [
                {'race_id': '20250103', 'horse_id': 'h5', 'horse_name': 'Horse C1', 'rank': 1, 'jockey': 'J5', 'date': '2025-01-03'}, 
            ]
            
        df_new = pd.DataFrame(new_data)
        
        # Integrity Check
        if check_integrity(df_new):
            print(f"  ✅ Data Valid. Saving.")
            # Save to DB (In reality, use safe_append)
            # For B, we might need to overwrite or append? 
            # Appending 'fixed' data creates duplicates, but deduplication happens at end or load.
            # User requirement: "Check... if missing values... get data... write"
            # It usually implies appending. We rely on distinct cleanup step or 'drop_duplicates' later.
            df_new.to_csv(DB_FILE, mode='a', header=False, index=False)
            
            # Update Cache
            pd.DataFrame({'race_id': [rid]}).to_csv(VERIFIED_FILE, mode='a', header=False, index=False)
            verified_ids.add(rid)
        else:
            print(f"  ❌ Scraped data invalid. Skipping save.")

    # Final Check
    print("\n📊 Final Status:")
    final_verified = init_verified_cache(DB_FILE, VERIFIED_FILE)
    print(f"Final Verified IDs: {final_verified}")
    assert '20250101' in final_verified
    assert '20250102' in final_verified
    assert '20250103' in final_verified
    
    print("🎉 Verification Successful!")

if __name__ == "__main__":
    run_differential_logic()
