
import pickle
import os
import pandas as pd
import sys

# Add paths
sys.path.append('ml')

model_path = 'ml/models/lgbm_model.pkl'
if not os.path.exists(model_path):
    print("Model not found.")
    sys.exit(0)

with open(model_path, 'rb') as f:
    model = pickle.load(f)

print(f"Model Type: {type(model)}")

if hasattr(model, 'feature_name'):
    print("Model expects features:")
    print(model.feature_name())
    print(f"Count: {len(model.feature_name())}")
else:
    print("Model object doesn't have feature_name() method.")

# Check current processed data columns
csv_path = 'ml/processed_data.csv'
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    target_col = 'target_top3'
    features = [c for c in df.columns if c not in meta_cols and c != target_col]
    features_numeric = [c for c in features if pd.api.types.is_numeric_dtype(df[c])]
    
    print("-" * 20)
    print("Current processed_data.csv contains numeric features:")
    print(features_numeric)
    print(f"Count: {len(features_numeric)}")
