import pandas as pd
import numpy as np
import os
import math
import re

def parse_time(t_str):
    if not isinstance(t_str, str):
        return np.nan
    try:
        # 1:35.2 or 59.5
        parts = t_str.split(':')
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        else:
            return float(t_str)
    except:
        return np.nan

def process_data(df, lambda_decay=0.2):
    # Filter valid rows (must have past data or be the target)
    # Convert '着 順' to numeric if available (for training)
    if '着 順' in df.columns:
        df['rank'] = pd.to_numeric(df['着 順'], errors='coerce')
    else:
        df['rank'] = np.nan
    
    # Calculate Weights
    # W_i = e^(-lambda * (i-1))
    # i = 1..5
    weights = [math.exp(-lambda_decay * (i-1)) for i in range(1, 6)]
    sum_weights = sum(weights)
    norm_weights = [w / sum_weights for w in weights]
    
    # Feature Columns to generate
    # columns: rank, run_style, last_3f, horse_weight
    
    features = ['rank', 'run_style', 'last_3f', 'horse_weight']
    
    # Pre-process columns
    for i in range(1, 6):
        # Rank
        col = f"past_{i}_rank"
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(18)
        else:
            df[col] = 18
            
        # Run Style
        col = f"past_{i}_run_style"
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(3)
        else:
            df[col] = 3

        # Last 3F (Time) - e.g. "34.5"
        col = f"past_{i}_last_3f"
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(40.0) # Slow default
        else:
            df[col] = 40.0
            
        # Horse Weight - e.g. "480(0)" -> extract 480
        col = f"past_{i}_horse_weight"
        if col in df.columns:
            # might be numeric or string "480(-2)"
            def parse_weight(val):
                if isinstance(val, (int, float)): return val
                if not isinstance(val, str): return 470.0
                match = re.search(r'(\d{3,4})', val)
                return float(match.group(1)) if match else 470.0
            
            df[col] = df[col].apply(parse_weight)
        else:
            df[col] = 470.0

        # Odds - e.g. "2.4"
        col = f"past_{i}_odds"
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(100.0) 
        else:
            df[col] = 100.0

        # Weather - Map to int
        col = f"past_{i}_weather"
        # 晴=1, 曇=2, 雨=3, 小雨=4, 雪=5
        w_map = {'晴': 1, '曇': 2, '雨': 3, '小雨': 4, '雪': 5}
        if col in df.columns:
            def map_weather(val):
                if not isinstance(val, str): return 2 # Default Cloudy
                for k, v in w_map.items():
                    if k in val: return v
                return 2
            df[col] = df[col].apply(map_weather)
        else:
            df[col] = 2

    # Calculate Weighted Averages
    # We add odds and weather to features list to average them
    features = ['rank', 'run_style', 'last_3f', 'horse_weight', 'odds', 'weather']
    
    for feat in features:
        df[f'weighted_avg_{feat}'] = 0.0
        for i in range(1, 6):
            df[f'weighted_avg_{feat}'] += df[f"past_{i}_{feat}"] * norm_weights[i-1]

    # Features to save
    feature_cols = [f'weighted_avg_{f}' for f in features]
    
    # Add scalar features (Age)
    if '性齢' in df.columns:
         df['age'] = df['性齢'].astype(str).str.extract(r'(\d+)').astype(float).fillna(3.0)
    else:
         df['age'] = 3.0
         
    feature_cols.append('age')
    
    # Return DF with features + target if available
    # Also keep meta info if needed (horse name, id)
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id']
    for c in meta_cols:
        if c not in df.columns:
             df[c] = ""
    
    # Combine
    final_cols = meta_cols + feature_cols + ['rank'] 
    
    # Filter columns that exist
    final_cols = [c for c in final_cols if c in df.columns]
    
    return df[final_cols].copy()

def calculate_features(input_csv, output_path, lambda_decay=0.5):
    print(f"Loading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    processed = process_data(df, lambda_decay)
    
    # For training, we need binary target
    processed['target_top3'] = (processed['rank'] <= 3).astype(int)
    
    # Clean NaNs in features?
    processed = processed.fillna(0) # Simple imputation
    
    processed.to_csv(output_path, index=False)
    print(f"Saved processed data to {output_path} ({len(processed)} rows)")

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "processed_data.csv")
    calculate_features(db_path, out_path)
