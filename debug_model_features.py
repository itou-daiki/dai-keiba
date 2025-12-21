import pickle
import os
import pandas as pd

# Load JRA model (or NAR if that's what's failing, assuming JRA/Default first)
# User didn't specify mode, but "AI expectation also disappeared" implies generic failure.
# Usually mismatch happens if model is old but code is new.

# Correct filenames based on public_app.py
model_path = "ml/models/lgbm_model.pkl"
if os.path.exists(model_path):
    print(f"Loading {model_path}...")
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    
    print(f"Expected Feature Count: {model.num_feature()}")
    print("Expected Features:")
    print(model.feature_name())
else:
    print(f"{model_path} not found.")

# Also check NAR model
model_path_nar = "ml/models/lgbm_model_nar.pkl"
if os.path.exists(model_path_nar):
    print(f"\nLoading {model_path_nar}...")
    with open(model_path_nar, "rb") as f:
        model_nar = pickle.load(f)
    print(f"Features: {model_nar.feature_name()}")
else:
    print(f"\n{model_path_nar} not found.")
