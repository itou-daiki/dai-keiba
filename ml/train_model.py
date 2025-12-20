import pandas as pd
import lightgbm as lgb
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

def train_and_save_model(data_path, model_path):
    if not os.path.exists(data_path):
        print(f"Data file {data_path} not found.")
        return

    df = pd.read_csv(data_path)
    
    # Check if we have enough data
    if len(df) < 10:
        print("Not enough data to train (need > 10 samples).")
        return

    # Define Target and Features
    target_col = 'target_top3'
    
    # Identify feature columns (numeric)
    # Exclude meta columns and target
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    # Also exclude raw 'past_...' colums if any remained (process_data keeps weighted only usually, but let's be safe)
    # process_data returns meta + weighted_avg_... + rank.
    
    # Drop valid string columns
    drop_cols = [c for c in df.columns if c in meta_cols or c == target_col]
    
    X = df.drop(columns=drop_cols, errors='ignore')
    
    # Ensure only numeric
    X = X.select_dtypes(include=['number'])
    
    y = df[target_col]
    
    print(f"Features: {list(X.columns)}")
    print(f"Target: {target_col} (Positive Rate: {y.mean():.2%})")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # LightGBM Dataset
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    # Params
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9
    }
    
    print("Training LightGBM model...")
    bst = lgb.train(
        params,
        train_data,
        num_boost_round=100,
        valid_sets=[test_data]
    )
    
    # Evaluate
    y_pred = bst.predict(X_test, num_iteration=bst.best_iteration)
    y_pred_binary = [1 if p > 0.5 else 0 for p in y_pred]
    acc = accuracy_score(y_test, y_pred_binary)
    try:
        auc = roc_auc_score(y_test, y_pred)
    except:
        auc = 0.0
        
    print(f"Model Accuracy: {acc:.4f}")
    print(f"Model AUC: {auc:.4f}")
    
    # Save
    with open(model_path, 'wb') as f:
        pickle.dump(bst, f)
        
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "processed_data.csv")
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "lgbm_model.pkl")
    
    train_and_save_model(data_path, model_path)
