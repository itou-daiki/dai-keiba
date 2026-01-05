import pandas as pd
import lightgbm as lgb
import pickle
import os
import sys

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "processed_data_nar.parquet")
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "lgbm_model_nar.pkl")

# Ensure model dir exists
os.makedirs(MODEL_DIR, exist_ok=True)

print(f"Loading data from {DATA_PATH}...")
if not os.path.exists(DATA_PATH):
    # Fallback to CSV if Parquet not found
    CSV_DATA_PATH = DATA_PATH.replace(".parquet", ".csv")
    if os.path.exists(CSV_DATA_PATH):
         print(f"Parquet not found, using CSV: {CSV_DATA_PATH}")
         DATA_PATH = CSV_DATA_PATH
    else:
        print(f"Error: {DATA_PATH} does not exist.")
        sys.exit(1)

if DATA_PATH.endswith('.parquet'):
    df = pd.read_parquet(DATA_PATH)
else:
    df = pd.read_csv(DATA_PATH)
print(f"Data shape: {df.shape}")

# Prepare data
target_col = 'target_win' # Standardize on target_win as per train_model.py P0-3
if target_col not in df.columns:
    if 'target_top3' in df.columns:
        print(f"target_win not found, using target_top3 instead.")
        target_col = 'target_top3'
    else:
        print("Error: No target column found.")
        sys.exit(1)

meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順', 'target_top3', 'target_win', 'target_show']
drop_cols = [c for c in df.columns if c in meta_cols]

# Keep only numeric features
X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
y = df[target_col]

print(f"Features: {X.shape[1]}")
print(f"Samples: {len(X)}")

# LightGBM params (Basic config)
lgb_params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'verbose': -1,
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'is_unbalance': True,  # Handle class imbalance
}

print("Training model...")
train_data = lgb.Dataset(X, label=y)

bst = lgb.train(
    lgb_params,
    train_data,
    num_boost_round=150 # Quick train
)

print(f"Saving model to {MODEL_PATH}...")
with open(MODEL_PATH, 'wb') as f:
    pickle.dump(bst, f)

print("Done. Model retrained and saved.")
