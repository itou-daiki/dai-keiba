import pandas as pd
import lightgbm as lgb
import pickle
import os
import sys

# Add paths
sys.path.append(os.path.abspath('scraper'))
sys.path.append(os.path.abspath('ml'))

import auto_scraper
import feature_engineering

RACE_ID = "202545121701" # Kawasaki 1R
MODE = "NAR"
MODEL_PATH = "ml/models/lgbm_model_nar.pkl"

print(f"--- Checking features for {RACE_ID} ---")

# 1. Get Generated Features
try:
    df = auto_scraper.scrape_shutuba_data(RACE_ID, mode=MODE)
    processed_df = feature_engineering.process_data(df, use_venue_features=True)
    
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    generated_features = set([c for c in processed_df.columns if c not in meta_cols and c != 'target_win'])
    print(f"Generated features count: {len(generated_features)}")
except Exception as e:
    print(f"Generation failed: {e}")
    sys.exit(1)

# 2. Get Model Features
try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    model_features = set(model.feature_name())
    print(f"Model features count: {len(model_features)}")
except Exception as e:
    print(f"Model load failed: {e}")
    sys.exit(1)

# 3. Diff
unused = generated_features - model_features
missing = model_features - generated_features

print("\n--- Summary ---")
print(f"Unused features (Generated but not in Model): {len(unused)}")
for f in unused:
    print(f"- {f}")

print(f"\nMissing features (In Model but not Generated): {len(missing)}")
for f in missing:
    print(f"- {f}")
