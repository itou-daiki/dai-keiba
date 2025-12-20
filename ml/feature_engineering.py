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

def add_history_features(df):
    """
    Groups by horse and sorts by date to add past N race features.
    """
    def parse_jp_date(s):
        if not isinstance(s, str): return pd.NaT
        try:
            return pd.to_datetime(s, format='%Y年%m月%d日')
        except:
            return pd.to_datetime(s, errors='coerce')

    if '日付' in df.columns:
        df['date_dt'] = df['日付'].apply(parse_jp_date)
    else:
        # If no date, can't sort properly
        return df

    # Sort
    df = df.sort_values(['馬名', 'date_dt'])
    
    # Target columns to shift
    # Map raw col to expected feature name base
    # rank -> 着 順
    # run_style -> コーナー 通過順 (Need processing)
    # last_3f -> 後3F
    # horse_weight -> 馬体重 (増減)
    # odds -> 単勝 オッズ
    # weather -> (Not in DB? Assuming always '晴' or need to scrape?)
    # DB columns: 日付,会場,レース番号,レース名,重賞,着 順,枠,馬 番,馬名,性齢,斤量,騎手,タイム,着差,人 気,単勝 オッズ,後3F,コーナー 通過順,厩舎,馬体重 (増減),race_id
    
    # Process raw cols first to be numeric
    # Handle missing columns for prediction mode
    if '着 順' in df.columns:
        df['rank_num'] = pd.to_numeric(df['着 順'], errors='coerce')
    else:
        df['rank_num'] = np.nan

    if '後3F' in df.columns:
        df['last_3f_num'] = pd.to_numeric(df['後3F'], errors='coerce')
    else:
        df['last_3f_num'] = np.nan

    if '単勝 オッズ' in df.columns:
        df['odds_num'] = pd.to_numeric(df['単勝 オッズ'], errors='coerce')
    else:
        df['odds_num'] = np.nan
    
    # Run Style Process: "2-2-2" -> take first number? Or avg? 
    # Usually "1-1" is nige (1), "10-10" is oikomi (4). 
    # Let's simple logic: 1=Nige, 2=Senko, 3=Sashi, 4=Oikomi
    # But for now let's just use the raw first number as position.
    def get_run_pos(s):
        if not isinstance(s, str): return np.nan
        try:
            return float(s.split('-')[0])
        except:
            return np.nan
    # Remove shifting loop that overwrites data
    # We will use existing columns directly
    
    # Process Time
    if 'タイム' in df.columns:
        df['time_seconds'] = df['タイム'].apply(parse_time)
    else:
        df['time_seconds'] = np.nan
    
    # Process Distance
    if '距離' in df.columns:
        df['distance_num'] = pd.to_numeric(df['距離'], errors='coerce')
    else:
        df['distance_num'] = np.nan
        
    # Process Weight and Weight Change
    def parse_weight_full(val):
        # Returns (weight, change)
        if not isinstance(val, str):
            return np.nan, np.nan
        # Match '460(0)', '460(+2)', '460(-6)', '460'
        match = re.search(r'(\d{3,4})\s*\(([-+]?\d+)\)', val)
        if match:
            return float(match.group(1)), float(match.group(2))
        
        # Match just number
        match_num = re.search(r'(\d{3,4})', val)
        if match_num:
            return float(match_num.group(1)), 0.0 # Assume 0 change if not specified
        return np.nan, np.nan

    # Apply parse_weight_full
    # We need to zip results to two columns
    weight_data = df['馬体重(増減)'].apply(parse_weight_full)
    df['weight_num'] = weight_data.apply(lambda x: x[0])
    df['weight_change_num'] = weight_data.apply(lambda x: x[1])
    df['weather_num'] = 2 
    # Pre-calculate Current Date for Interval
    # Already done at top
    # df['date_dt'] = df['日付'].apply(parse_jp_date)

    # Iterate 1..5 to process existing past columns
    for i in range(1, 6):
        # 1. Parse Date & Interval
        p_date_col = f'past_{i}_date'
        if p_date_col in df.columns:
            # Past date seems to be '2025/11/08', standard format
            p_dt = pd.to_datetime(df[p_date_col], errors='coerce')
            df[f'past_{i}_interval'] = (df['date_dt'] - p_dt).dt.days
        else:
            df[f'past_{i}_interval'] = np.nan

        # 2. Parse Rank (Handle '除', '中' etc by coercion)
        p_rank_col = f'past_{i}_rank'
        if p_rank_col in df.columns:
             # Already likely strings, convert
             df[f'past_{i}_rank'] = pd.to_numeric(df[p_rank_col], errors='coerce')

        # 3. Parse Weight & Change
        p_weight_col = f'past_{i}_horse_weight'
        if p_weight_col in df.columns:
            # Apply parse_weight_full
            w_data = df[p_weight_col].apply(parse_weight_full)
            # Tuple unpacking is tricky in one go if NaNs, so:
            df[f'past_{i}_horse_weight'] = w_data.apply(lambda x: x[0])
            df[f'past_{i}_weight_change'] = w_data.apply(lambda x: x[1])
        else:
            df[f'past_{i}_weight_change'] = np.nan

        # 4. Parse Weather & Condition
        # Maps defined inside/outside? Let's define maps.
        w_map = {'晴': 1, '曇': 2, '雨': 3, '小雨': 4, '雪': 5}
        c_map = {'良': 1, '稍重': 2, '重': 3, '不良': 4}

        p_weather_col = f'past_{i}_weather'
        if p_weather_col in df.columns:
            def map_w(x):
                if not isinstance(x, str): return 2
                for k, v in w_map.items():
                    if k in x: return v
                return 2
            df[f'past_{i}_weather'] = df[p_weather_col].apply(map_w)
        
        p_cond_col = f'past_{i}_condition'
        if p_cond_col in df.columns:
             def map_c(x):
                if not isinstance(x, str): return 1
                for k, v in c_map.items():
                    if k in x: return v
                return 1
             df[f'past_{i}_condition'] = df[p_cond_col].apply(map_c) # New feature likely needed in list

        # 5. Speed?
        # We DON'T have past distance easily.
        # But we have `past_i_last_3f`.
        # We'll rely on last_3f for speed-like metric.
        # No change needed for last_3f if it's already numeric or simple string
        p_3f_col = f'past_{i}_last_3f'
        if p_3f_col in df.columns:
             df[f'past_{i}_last_3f'] = pd.to_numeric(df[p_3f_col], errors='coerce')

        # 6. Parse Time (Optional, useful if valid)
        p_time_col = f'past_{i}_time'
        if p_time_col in df.columns:
             df[f'past_{i}_time_seconds'] = df[p_time_col].apply(parse_time)

    # Clean up current weight change (calculated above)
    # Already done: df['weight_change_num']

    return df

def process_data(df, lambda_decay=0.2):
    # FIRST: Add history features
    df = add_history_features(df)
    
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
    # Feature Columns to generate
    # Feature Columns to generate
    # Added interval
    features = ['rank', 'run_style', 'last_3f', 'horse_weight', 'odds', 'weather', 'weight_change', 'interval']
    
    # Pre-process columns (Fill NaNs)
    for i in range(1, 6):
        # Rank
        col = f"past_{i}_rank"
        if col in df.columns:
            df[col] = df[col].fillna(18)
        else:
            df[col] = 18
            
        # Run Style - parse from 'past_i_run_style'?
        # The CSV has strings likely.
        # Need numeric logic? If scrape raw is '10-10', extract first.
        # Assuming simple parsing for 'run_style' was missed in step above.
        # Let's simple parse here if needed or assume feature is cleaner.
        # Actually `past_1_run_style` in CSV might be '12-10'.
        # We need a quick parse for it in loop above? 
        # For safety, let's treat it as numeric position if possible, or fill 10.
        col = f"past_{i}_run_style"
        # We didn't parse it above! 
        # Quick fix: standard simple parse
        def quick_run_pos(x):
            try:
                if isinstance(x, (int, float)): return float(x)
                if isinstance(x, str): return float(x.split('-')[0])
                return 10.0
            except: return 10.0
            
        if col in df.columns:
            df[col] = df[col].apply(quick_run_pos).fillna(10)
        else:
            df[col] = 10

        # Last 3F (Time)
        col = f"past_{i}_last_3f"
        if col in df.columns:
            df[col] = df[col].fillna(40.0)
        else:
            df[col] = 40.0
            
        # Horse Weight
        col = f"past_{i}_horse_weight"
        if col in df.columns:
            df[col] = df[col].fillna(470.0)
        else:
            df[col] = 470.0
            
        # Odds
        col = f"past_{i}_odds"
        if col in df.columns:
            df[col] = df[col].fillna(100.0) 
        else:
            df[col] = 100.0

        # Weight Change
        col = f"past_{i}_weight_change"
        if col in df.columns:
            df[col] = df[col].fillna(0.0)
        else:
            df[col] = 0.0
            
        # Interval
        col = f"past_{i}_interval"
        if col in df.columns:
            df[col] = df[col].fillna(180) # Default long interval if missing
        else:
            df[col] = 180

        # Weather
        col = f"past_{i}_weather"
        if col in df.columns:
            df[col] = df[col].fillna(2)
        else:
            df[col] = 2

    # Calculate Weighted Averages
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
    
    # --- New Course Features ---
    # Convert raw strings to numeric codes
    
    # 1. Course Type (course_type) -> 芝=1, ダ=2, 障=3
    if 'コースタイプ' in df.columns:
        def map_course(x):
            if not isinstance(x, str): return 0
            if '芝' in x: return 1
            if 'ダ' in x: return 2
            if '障' in x: return 3
            return 0
        df['course_type_code'] = df['コースタイプ'].apply(map_course)
        feature_cols.append('course_type_code')
    else:
        df['course_type_code'] = 0
        feature_cols.append('course_type_code')

    # 2. Distance -> Numeric
    if '距離' in df.columns:
        df['distance_val'] = pd.to_numeric(df['距離'], errors='coerce').fillna(1600)
        feature_cols.append('distance_val')
    else:
        df['distance_val'] = 1600
        feature_cols.append('distance_val')

    # 3. Rotation -> 右=1, 左=2, 直線=3, 他=0
    if '回り' in df.columns:
        def map_rot(x):
            if not isinstance(x, str): return 0
            if '右' in x: return 1
            if '左' in x: return 2
            if '直線' in x: return 3
            return 0
        df['rotation_code'] = df['回り'].apply(map_rot)
        feature_cols.append('rotation_code')
    else:
        df['rotation_code'] = 0
        feature_cols.append('rotation_code')

    # 4. Weather (Current Race) -> 晴=1, 曇=2, 雨=3, 小雨=4, 雪=5
    # Note: DB might have '天候' column
    w_map = {'晴': 1, '曇': 2, '雨': 3, '小雨': 4, '雪': 5}
    if '天候' in df.columns:
         def map_weather_curr(val):
            if not isinstance(val, str): return 2
            for k, v in w_map.items():
                if k in val: return v
            return 2
         df['weather_code'] = df['天候'].apply(map_weather_curr)
         feature_cols.append('weather_code')
    else:
         df['weather_code'] = 2
         feature_cols.append('weather_code')

    # 5. Condition (Current Race) -> 良=1, 稍重=2, 重=3, 不良=4
    c_map = {'良': 1, '稍重': 2, '重': 3, '不良': 4}
    if '馬場状態' in df.columns:
        def map_cond_curr(val):
            if not isinstance(val, str): return 1
            for k, v in c_map.items():
                if k in val: return v
            return 1
        df['condition_code'] = df['馬場状態'].apply(map_cond_curr)
        feature_cols.append('condition_code')
    else:
        df['condition_code'] = 1
        feature_cols.append('condition_code')
    
    # Meta cols
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    # Add date string if not exists
    if 'date' not in df.columns and '日付' in df.columns:
        df['date'] = df['日付']

    # Keep only relevant columns
    # We want to return a DF that has meta_cols + feature_cols + target info
    keep_cols = []
    
    # Add available meta cols
    for c in meta_cols:
        if c in df.columns:
            keep_cols.append(c)
            
    # Add feature cols
    keep_cols.extend(feature_cols)
    
    return df[keep_cols].copy()

def calculate_features(input_csv, output_path, lambda_decay=0.5):
    print(f"Loading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    processed = process_data(df, lambda_decay)
    
    # For training, we need binary target
    if 'rank' in processed.columns:
        processed['target_top3'] = (processed['rank'] <= 3).astype(int)
    else:
        processed['target_top3'] = 0
    
    # Clean NaNs in features?
    processed = processed.fillna(0) # Simple imputation
    
    processed.to_csv(output_path, index=False)
    print(f"Saved processed data to {output_path} ({len(processed)} rows)")

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.csv")
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "processed_data.csv")
    calculate_features(db_path, out_path)
