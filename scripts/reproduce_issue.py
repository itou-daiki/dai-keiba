import sys
import os
import pandas as pd
import pickle
import traceback

# Add paths
sys.path.append(os.path.abspath('scraper'))
sys.path.append(os.path.abspath('ml'))

import auto_scraper
import feature_engineering

RACE_ID = "202545121701" # Kawasaki 1R
MODE = "NAR"
MODEL_PATH = "ml/models/lgbm_model_nar.pkl"

print(f"--- 1. Scraping Shutuba Data for {RACE_ID} ({MODE}) ---")
try:
    df = auto_scraper.scrape_shutuba_data(RACE_ID, mode=MODE)
    if df is not None:
        print("✅ Data fetched.")
    else:
        print("❌ Scrape returned None.")
        sys.exit(1)
except Exception as e:
    print(f"❌ Scrape crashed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n--- 2. Processing Data ---")
try:
    processed_df = feature_engineering.process_data(df, use_venue_features=True)
    print("✅ Processed Data.")
except Exception as e:
    print(f"❌ process_data crashed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n--- 3. Prediction Test ---")
if not os.path.exists(MODEL_PATH):
    print(f"❌ Model file not found: {MODEL_PATH}")
    # Try creating a dummy one or fail?
    # We really need the actual model to reproduce a feature mismatch.
    sys.exit(1)

try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    print("✅ Model loaded.")
    
    # Logic from public_app.py
    if hasattr(model, 'feature_name'):
         model_features = model.feature_name()
         # Ensure all features exist
         for f in model_features:
             if f not in processed_df.columns:
                 processed_df[f] = 0
         
         X_pred = processed_df[model_features].fillna(0)
    else:
         # Fallback
         meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
         features = [c for c in processed_df.columns if c not in meta_cols and c != 'target_win']
         X_pred = processed_df[features].select_dtypes(include=['number']).fillna(0)
    
    print(f"Features ({len(X_pred.columns)}): {X_pred.columns.tolist()}")
    
    # Predict
    probs = model.predict(X_pred)
    print("✅ Prediction success!")
    print(probs)
    
except Exception as e:
    print(f"❌ Prediction crashed: {e}")
    traceback.print_exc()
