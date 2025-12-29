import pandas as pd
import numpy as np
import os
import math
import re
import zlib
try:
    from .venue_characteristics import (
        get_venue_characteristics,
        get_run_style_bias,
        get_distance_bias,
        get_distance_category
    )
    from .run_style_analyzer import (
        analyze_horse_run_style,
        get_run_style_code,
        calculate_run_style_consistency
    )
    VENUE_ANALYSIS_AVAILABLE = True
except ImportError:
    try:
        from venue_characteristics import (
            get_venue_characteristics,
            get_run_style_bias,
            get_distance_bias,
            get_distance_category
        )
        from run_style_analyzer import (
            analyze_horse_run_style,
            get_run_style_code,
            calculate_run_style_consistency
        )
        VENUE_ANALYSIS_AVAILABLE = True
    except ImportError:
        VENUE_ANALYSIS_AVAILABLE = False
        print("Warning: venue_characteristics or run_style_analyzer not found.")

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

def clean_id_str(val):
    try:
        return str(int(float(val)))
    except:
        return str(val)

def clean_stable_name(val):
    if not isinstance(val, str): return ""
    # Remove (Western), (Eastern), (Local) etc.
    # Remove all whitespace
    val = val.replace(" ", "").replace("　", "")
    # Remove text in parentheses
    import re
    val = re.sub(r'\(.*?\)', '', val)
    return val

def clean_jockey(name):
    if not isinstance(name, str): return ""
    # Remove symbols and ALL whitespace
    import re
    name = re.sub(r'[▲△☆◇★\d]', '', name)
    return name.replace(" ", "").replace("　", "").strip()

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
    if '馬体重(増減)' in df.columns:
        weight_data = df['馬体重(増減)'].apply(parse_weight_full)
        df['weight_num'] = weight_data.apply(lambda x: x[0])
        df['weight_change_num'] = weight_data.apply(lambda x: x[1])
    else:
        df['weight_num'] = np.nan
        df['weight_change_num'] = 0.0 # Change unknown, assume 0
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
        else:
             df[f'past_{i}_time_seconds'] = np.nan

        # 7. Parse Distance & Course Type (New)
        p_dist_col = f'past_{i}_distance'
        if p_dist_col in df.columns:
             df[f'past_{i}_distance'] = pd.to_numeric(df[p_dist_col], errors='coerce')
        else:
             df[f'past_{i}_distance'] = np.nan

        p_course_col = f'past_{i}_course_type'
        # If it exists, it might be '芝' or 'ダ' or nan.
        # We want to maybe keep it as string or map to code?
        # Helper function to map course type string to code
        def map_course_type_hist(x):
            if not isinstance(x, str): return 0 # 0=Unknown
            if '芝' in x: return 1
            if 'ダ' in x: return 2
            if '障' in x: return 3
            return 0
            
        if p_course_col in df.columns:
             df[f'past_{i}_course_type_code'] = df[p_course_col].apply(map_course_type_hist)
        else:
             df[f'past_{i}_course_type_code'] = 0

        # 8. Calculate Speed (New)
        # Speed = Distance / Time
        # past_i_speed = past_i_distance / past_i_time_seconds
        d_col = f'past_{i}_distance'
        t_col = f'past_{i}_time_seconds'
        if d_col in df.columns and t_col in df.columns:
             # Handle division by zero or NaN
             df[f'past_{i}_speed'] = df[d_col] / df[t_col]
             # Replace inf with nan
             df[f'past_{i}_speed'] = df[f'past_{i}_speed'].replace([np.inf, -np.inf], np.nan)
        else:
             df[f'past_{i}_speed'] = np.nan
        
        # De-fragment inside loop to prevent buildup
        df = df.copy()

    # Clean up current weight change (calculated above)
    # Already done: df['weight_change_num']

    
    # De-fragment after helper loop
    df = df.copy()

    return df

def process_data(df, lambda_decay=0.2, use_venue_features=False, input_stats=None, return_stats=False):
    # FIRST: Add history features
    df = add_history_features(df)
    
    # Filter valid rows (must have past data or be the target)
    # Convert '着 順' to numeric if available (for training)
    if '着 順' in df.columns:
        df['rank'] = pd.to_numeric(df['着 順'], errors='coerce')
    else:
        df['rank'] = np.nan
    
    # Calculate Weights
    # 一般的な競馬予測の重み付け比率を採用
    # 前走: 55%, 前々走: 25%, 3走前: 12%, 4走前: 6%, 5走前: 2%
    #
    # 従来の指数減衰（lambda=0.2）からの変更理由:
    # - 競馬では前走の情報が圧倒的に重要（50-60%）
    # - 指数減衰では前走が30%程度で、重要度が低すぎる
    # - プロの予想家や指数計算で採用される標準的な比率を採用
    # Adjusted Weights for Stability (slightly smoother decay)
    # 55% was too aggressive. 50% is standard strong emphasis.
    base_weights = [0.50, 0.25, 0.13, 0.08, 0.04]  # Total 1.0

    # 動的な重み調整（後で実装）
    # - 休養期間が長い場合、前走の重みを下げる
    # - 馬齢が若い（2-3歳）場合、前走の重みを上げる（成長曲線）
    # - コース条件が似ている走の重みを上げる
    norm_weights = base_weights
    
    # Feature Columns to generate
    # Added interval, speed
    # Feature Columns to generate
    # Added interval, speed, trend
    features = ['rank', 'run_style', 'last_3f', 'horse_weight', 'odds', 'weather', 'weight_change', 'interval', 'speed']
    feature_cols = []
    
    # Calculate Trend (Linear Slope for Rank & Last 3F)
    # We want to know if the horse is improving (Rank getting smaller, Time getting smaller)
    # Slope > 0 means increasing (Worsening Rank/Time)
    # Slope < 0 means decreasing (Improving Rank/Time)
    
    def calculate_trend(row, prefix):
        # Extract values for past 1..5
        y = []
        x = []
        valid_count = 0
        for i in range(1, 6):
            col = f"past_{i}_{prefix}"
            if col in row.index and pd.notna(row[col]):
                val = row[col]
                # Filter out obvious filler values if possible, but hard to know.
                # Assuming NaNs were handled but maybe not perfectly.
                y.append(float(val))
                x.append(i) # 1=Recent, 5=Old
                valid_count += 1
        
        if valid_count < 2:
            return 0.0
            
        # We want slope relative to time. 
        # X axis: [1, 2, 3, 4, 5] (1 is recent)
        # If values are [1, 2, 3] (Rank 1 recent, Rank 3 old) -> Improving.
        # Linear Regression: y = ax + b
        # X is [1, 2, 3...]
        # If Rank=1(x=1), Rank=2(x=2), Rank=3(x=3). Slope approx +1.
        # Wait, x=1 is recent.
        # Rank 1 (Recent) < Rank 3 (Old).
        # Slope = (y2-y1)/(x2-x1) = (3-1)/(3-1) = +1.
        # So Positive Slope means "Old values were larger than recent values" -> IMPROVING.
        # Wait.
        # x: 1(Recent), 2, 3(Old). 
        # y: 1(Good), 2, 3(Bad).
        # P1(1,1), P3(3,3). 
        # Slope = (3-1)/(3-1) = 1. Positive Slope = "Improving" (Recent is smaller/better).
        # Let's double check.
        # y = slope * x + intercept
        # 1 = slope * 1 + b
        # 3 = slope * 3 + b
        # 2 = 2 * slope -> slope = 1.
        # Positive Slope -> Value increases as we go back in time (Old is Larger).
        # Since Rank/Time: Lower is Better.
        # "Old is Larger" means "Old was Worse".
        # So Positive Slope = Improving.
        
        try:
            slope, _ = np.polyfit(x, y, 1)
            return slope
        except:
            return 0.0

    # Apply Trend for Rank & Last 3F
    df['trend_rank'] = df.apply(lambda row: calculate_trend(row, 'rank'), axis=1)
    df['trend_last_3f'] = df.apply(lambda row: calculate_trend(row, 'last_3f'), axis=1) # Note: last_3f LOWER is usually better (faster)? 
    # Yes, 33.0 is better than 34.0. So Positive Slope = Improving.
    
    feature_cols.extend(['trend_rank', 'trend_last_3f'])
    
    # De-fragment
    df = df.copy()
    
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
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(100.0).infer_objects() 
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

        col = f"past_{i}_weather"
        if col in df.columns:
            df[col] = df[col].fillna(2)
        else:
            df[col] = 2

        # Speed
        col = f"past_{i}_speed"
        if col in df.columns:
            # Average speed? ~1000m/60s = 16.6 m/s
            # 1600m / 95s = 16.8
            df[col] = df[col].fillna(16.0)
        else:
            df[col] = 16.0

    # Calculate Weighted Averages
    for feat in features:
        df[f'weighted_avg_{feat}'] = 0.0
        for i in range(1, 6):
            df[f'weighted_avg_{feat}'] += df[f"past_{i}_{feat}"] * norm_weights[i-1]
        feature_cols.append(f'weighted_avg_{feat}')
    
    # De-fragment
    df = df.copy()

    # ========== 新規特徴量: 現在レースのメタ情報 (Moved for dependencies) ==========
    
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

    # 6. Current Odds (単勝)
    if '単勝' in df.columns:
        df['odds'] = pd.to_numeric(df['単勝'], errors='coerce').fillna(0.0)
        feature_cols.append('odds')
    elif 'odds' in df.columns:
        # Already exists (e.g. inference with prepared df)
        df['odds'] = pd.to_numeric(df['odds'], errors='coerce').fillna(0.0)
        feature_cols.append('odds')
    else:
        df['odds'] = 0.0
        feature_cols.append('odds')

    # 7. Current Weight & Change (Already parsed to weight_num, weight_change_num)
    if 'weight_num' in df.columns:
        df['horse_weight'] = df['weight_num'].fillna(470) # Standard fill
        feature_cols.append('horse_weight')
    else:
        df['horse_weight'] = 470
        feature_cols.append('horse_weight')
        
    if 'weight_change_num' in df.columns:
        df['weight_change'] = df['weight_change_num'].fillna(0)
        feature_cols.append('weight_change')
    else:
        df['weight_change'] = 0
        feature_cols.append('weight_change')

    # ========== 新規特徴量: コース・馬場適性 (Global History) ==========
    
    # Global Sort (Already done for Jockey Compat, but ensure it)
    if not df.index.equals(df.sort_values('date_dt').index):
        df.sort_values('date_dt', inplace=True)

    # Global Sort (Already done for Jockey Compat, but ensure it)
    if not df.index.equals(df.sort_values('date_dt').index):
        df.sort_values('date_dt', inplace=True)
    
    # De-fragment before heavy group operations
    df = df.copy()

    # Helper: Global Expanding Mean by Horse
    # We use 'hj_key' part 'horse_id' which we probably need to define cleanly.
    
    # Helper: Global Expanding Mean by Horse
    # We use 'hj_key' part 'horse_id' which we probably need to define cleanly.
    
    if 'horse_id' in df.columns:
        df['h_key'] = df['horse_id'].apply(clean_id_str)
    else:
        df['h_key'] = df['馬名'].astype(str)

    # 1. Turf/Dirt Compatibility
    # Prepare flags
    # course_type_code: 1=Turf, 2=Dirt
    # We need to rely on the row's own course type for the 'is_turf' check of THAT race.
    # Wait, for expanding mean, we need to know if the PAST race was Turf or Dirt using that row's data.
    # `course_type_code` in `df` represents the CURRENT race info (if we are predicting) 
    # OR the race info of that row (if training).
    # In `database.csv`, each row is a race result. So `df['course_type_code']` is the course type of that race.
    # Correct.
    
    # Masks
    is_turf = (df['course_type_code'] == 1)
    is_dirt = (df['course_type_code'] == 2)
    
    # Calculate Ranks for specific conditions (NaN if not matching)
    df['rank_if_turf'] = np.where(is_turf, df['rank'], np.nan)
    df['rank_if_dirt'] = np.where(is_dirt, df['rank'], np.nan)
    
    # Expanding Mean
    # Group by Horse, Shift 1 (past), Expanding Mean
    # Expanding Mean
    # Group by Horse, Shift 1 (past), Expanding Mean
    
    if input_stats:
        # Inference Mode: Use pre-calculated stats
        if 'horse_turf' in input_stats:
             df['turf_compatibility'] = df['h_key'].map(input_stats['horse_turf']).fillna(10.0)
        else:
             df['turf_compatibility'] = 10.0
             
        if 'horse_dirt' in input_stats:
             df['dirt_compatibility'] = df['h_key'].map(input_stats['horse_dirt']).fillna(10.0)
        else:
             df['dirt_compatibility'] = 10.0
    else:
        # Training Mode
        df['turf_compatibility'] = df.groupby('h_key')['rank_if_turf'].transform(
            lambda x: x.shift(1).expanding().mean()
        ).fillna(10.0)
        
        df['dirt_compatibility'] = df.groupby('h_key')['rank_if_dirt'].transform(
            lambda x: x.shift(1).expanding().mean()
        ).fillna(10.0)

    # 2. Condition Compatibility
    # Good: 1, Heavy: 3 or 4 (Heavy/Bad)
    is_good = (df['condition_code'] == 1)
    is_heavy = (df['condition_code'] >= 3)
    
    df['rank_if_good'] = np.where(is_good, df['rank'], np.nan)
    df['rank_if_heavy'] = np.where(is_heavy, df['rank'], np.nan)
    
    if input_stats:
        if 'horse_heavy' in input_stats:
             df['heavy_condition_avg'] = df['h_key'].map(input_stats['horse_heavy']).fillna(10.0)
        else:
             df['heavy_condition_avg'] = 10.0
             
        if 'horse_good' in input_stats:
             df['good_condition_avg'] = df['h_key'].map(input_stats['horse_good']).fillna(10.0)
        else:
             df['good_condition_avg'] = 10.0
    else:
        df['good_condition_avg'] = df.groupby('h_key')['rank_if_good'].transform(
            lambda x: x.shift(1).expanding().mean()
        ).fillna(10.0)
        
        df['heavy_condition_avg'] = df.groupby('h_key')['rank_if_heavy'].transform(
            lambda x: x.shift(1).expanding().mean()
        ).fillna(10.0)

    # 3. Jockey Compatibility
    # Clean Jockey Name
    df['jockey_clean'] = df['騎手'].astype(str).apply(clean_jockey)
    
    # Generate Stable Key (t_key)
    if '厩舎' in df.columns:
        df['t_key'] = df['厩舎'].astype(str).apply(clean_stable_name)
    else:
        df['t_key'] = ""
        
    df['hj_key'] = df['h_key'] + '_' + df['jockey_clean']
    df['tj_key'] = df['t_key'] + '_' + df['jockey_clean']
    
    
    # Initialize jockey_compatibility to NaN (will be filled by stats map or fallback)
    df['jockey_compatibility'] = np.nan
    
    if input_stats:
        if 'hj_compatibility' in input_stats:
             df['jockey_compatibility'] = df['hj_key'].map(input_stats['hj_compatibility'])
             
        if 'tj_compatibility' in input_stats:
             df['trainer_jockey_compatibility'] = df['tj_key'].map(input_stats['tj_compatibility'])
    
    # De-fragment
    df = df.copy()
    
    # 3. Distance Compatibility
    dist_val = df['distance_val'].fillna(1600)
    # Use explicit bins mapping
    cats = ['Sprint', 'Mile', 'Intermediate', 'Long']
    # Use pandas cut but handle category type carefully
    df['dist_cat'] = pd.cut(dist_val, bins=[0, 1399, 1899, 2499, 9999], labels=cats)
    
    # Init column
    df['distance_compatibility'] = 10.0

    if input_stats:
        # Inference: Lookup based on CURRENT dist_cat
        # We need a map: {h_key: {'Sprint': val, 'Mile': val...}} -> complex?
        # Or simple flat maps: 'horse_dist_Sprint', 'horse_dist_Mile'
        for cat in cats:
            stat_key = f'horse_dist_{cat}'
            if stat_key in input_stats:
                # Map only for rows where category matches
                is_cat = (df['dist_cat'] == cat)
                if is_cat.any():
                    # Create a Series for this cat
                    mapped = df.loc[is_cat, 'h_key'].map(input_stats[stat_key]).fillna(10.0)
                    df.loc[is_cat, 'distance_compatibility'] = mapped
    else:
        # Training
        for cat in cats:
            is_cat = (df['dist_cat'] == cat)
            col_name = f'rank_if_{cat}'
            df[col_name] = np.where(is_cat, df['rank'], np.nan)
            
            # Temporary avg column
            avg_col = f'avg_rank_{cat}'
            df[avg_col] = df.groupby('h_key')[col_name].transform(
                lambda x: x.shift(1).expanding().mean()
            ).fillna(10.0)
            
            # Apply to distance_compatibility
            df.loc[is_cat, 'distance_compatibility'] = df.loc[is_cat, avg_col]

    # Calculate Speed (Global Avg Speed?) - Optional, user request mentions speed
    # Currently handled in weighted_avg_speed (past 5). Global speed might be useful too but task focus is compatibility.
    
    # De-fragment before dropping
    df = df.copy()
    
    # Cleanup temps
    
    # Cleanup temps
    drop_temp_cols = ['h_key', 'rank_if_turf', 'rank_if_dirt', 'rank_if_good', 'rank_if_heavy', 'dist_cat']
    if not input_stats:
        for cat in cats:
            drop_temp_cols.append(f'rank_if_{cat}')
            drop_temp_cols.append(f'avg_rank_{cat}')
        
    df.drop(columns=drop_temp_cols, inplace=True, errors='ignore')

    # ========== 新規特徴量: レース間隔関連 (Optimized) ==========

    # 4. is_rest_comeback / interval
    # Calculate interval from previous date globally (much faster/more accurate than past_1)
    # Group by Horse, Shift Date
    # df is sorted by date
    
    df['prev_date'] = df.groupby('horse_id' if 'horse_id' in df.columns else '馬名')['date_dt'].shift(1)
    df['interval_days'] = (df['date_dt'] - df['prev_date']).dt.days
    
    # Fill missing interval (First race) with large number (e.g. 180 or 999)
    df['interval_days'] = df['interval_days'].fillna(999)
    
    df['is_rest_comeback'] = (df['interval_days'] >= 90).astype(int)
    df['is_consecutive'] = (df['interval_days'] <= 14).astype(int)
    
    # Interval Category
    # 1: <=14, 2: <=30, 3: <=60, 4: >60
    df['interval_category'] = 4
    df.loc[df['interval_days'] <= 60, 'interval_category'] = 3
    df.loc[df['interval_days'] <= 30, 'interval_category'] = 2
    df.loc[df['interval_days'] <= 14, 'interval_category'] = 1
    
    # Drop prev_date
    df.drop(columns=['prev_date', 'interval_days'], inplace=True, errors='ignore') # We might want to keep interval_days as specific feature?
    # Original features had 'weighted_avg_interval'.
    # Keeping raw 'interval' for current race might be useful as feature?
    # But `process_data` defines features list.
    # Let's strictly replace the section 447-606.


    # Optimize Memory (De-fragmentation)
    # The previous steps added many columns, causing fragmentation warnings.
    df = df.copy()

    # ========== 新規特徴量: 騎手との相性 ==========

    # 7. 現在の騎手との過去成績（過去5走で同じ騎手の時の平均着順）


    # ========== 新規特徴量: 騎手との相性 (Global & Trainer Fallback) ==========

    # 7. 騎手との相性（Global）
    # 過去5走だけでなく、過去3年間の全データから相性を算出
    # 優先度:
    # 1. 馬×騎手の通算成績 (Global Expanding Mean)
    # 2. 厩舎×騎手の通算成績 (Global Expanding Mean) - Fallback
    # 3. デフォルト (10.0)

    if not input_stats:
        # Training Mode (Expanding Mean)
        if 'rank' not in df.columns:
             df['rank'] = pd.to_numeric(df['着 順'], errors='coerce')
        
        # Global Sort by Date (Crucial for expanding)
        df.sort_values(['date_dt'], inplace=True)
        
        # 1. Horse-Jockey Compatibility
        # Calculate average rank of previous races
        df['prev_rank'] = df.groupby('hj_key')['rank'].shift(1)
        
        # Expanding mean (Optimized)
        # Returns MultiIndex (Key, OriginalIndex), we drop Key to align with df via Index
        df['jockey_compatibility'] = df.groupby('hj_key')['prev_rank'].expanding().mean().reset_index(level=0, drop=True)
        
        # 2. Trainer-Jockey Compatibility
        df['prev_rank_tj'] = df.groupby('tj_key')['rank'].shift(1)
        df['trainer_jockey_compatibility'] = df.groupby('tj_key')['prev_rank_tj'].expanding().mean().reset_index(level=0, drop=True)
        
        # Drop temp
        df.drop(columns=['prev_rank', 'prev_rank_tj'], inplace=True, errors='ignore')

    # Fallback Logic
    df['jockey_compatibility'] = df['jockey_compatibility'].fillna(df['trainer_jockey_compatibility'])
    df['jockey_compatibility'] = df['jockey_compatibility'].fillna(10.0) # Default Average
        
    # Clean temp keys
    # DEBUG: Keep keys for verification
    # df.drop(columns=['hj_key', 'tj_key', 'trainer_jockey_compatibility'], inplace=True, errors='ignore')
    df.drop(columns=['trainer_jockey_compatibility'], inplace=True, errors='ignore')
    df['debug_ver'] = "v1_nodrop"


    # ========== 新規特徴量: レースクラス・条件 ==========

    # 8. レースクラスコード（新馬/未勝利/1勝/2勝/3勝/オープン/G3/G2/G1）
    df['race_class'] = 0  # デフォルト

    if 'レース名' in df.columns:
        def classify_race(name):
            if not isinstance(name, str):
                return 0
            name = str(name)
            if 'G1' in name or 'ＧⅠ' in name:
                return 9
            elif 'G2' in name or 'ＧⅡ' in name:
                return 8
            elif 'G3' in name or 'ＧⅢ' in name:
                return 7
            elif 'オープン' in name or 'OP' in name or 'A1' in name:
                return 6
            elif '3勝' in name or 'A2' in name or 'B1' in name:
                return 5
            elif '2勝' in name or 'B2' in name or 'B3' in name:
                return 4
            elif '1勝' in name or 'C1' in name:
                return 3
            elif '未勝利' in name or 'C2' in name:
                return 2
            elif '新馬' in name or 'C3' in name:
                return 1
            return 0

        df['race_class'] = df['レース名'].apply(classify_race)
        feature_cols.append('race_class') # Append single first

    # Register new grouped features to feature_cols
    feature_cols.extend([
        'turf_compatibility', 'dirt_compatibility', 
        'good_condition_avg', 'heavy_condition_avg', 
        'distance_compatibility', 
        'is_rest_comeback', 'is_consecutive', 'interval_category',
        'jockey_compatibility'
    ])

    # 9. 重賞フラグ
    df['is_graded'] = 0
    if '重賞' in df.columns:
        df['is_graded'] = df['重賞'].notna().astype(int)

    # 10. 年齢制限（2歳限定/3歳限定/3歳以上など）
    df['age_limit'] = 0  # 0: 制限なし, 2: 2歳限定, 3: 3歳限定, 4: 3歳以上

    if 'レース名' in df.columns:
        def extract_age_limit(name):
            if not isinstance(name, str):
                return 0
            if '2歳' in name:
                return 2
            elif '3歳' in name:
                if '以上' in name or '上' in name:
                    return 4
                return 3
            return 0

        df['age_limit'] = df['レース名'].apply(extract_age_limit)

    # ========== 新規特徴量: 中央/地方競馬の区別 ==========

    # 11. レースタイプ（JRA/NAR）
    df['race_type'] = 'UNKNOWN'
    df['race_type_code'] = -1

    if '会場' in df.columns:
        # Import race classifier
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from race_classifier import classify_race_type, get_race_type_code

            df['race_type'] = df['会場'].apply(classify_race_type)
            df['race_type_code'] = df['race_type'].apply(get_race_type_code)
        except ImportError:
            # Fallback: simple classification
            jra_venues = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']

            def simple_classify(venue):
                if not isinstance(venue, str):
                    return 'UNKNOWN'
                return 'JRA' if venue in jra_venues else 'NAR'

            df['race_type'] = df['会場'].apply(simple_classify)
            df['race_type_code'] = df['race_type'].apply(lambda x: 1 if x == 'JRA' else 0)
    else:
        # Fallback if '会場' is missing
        # Try to infer from race_id if available
        if 'race_id' in df.columns:
             # Very basic heuristic: JRA IDs are usually simple YYYYPP... but netkeiba format is standardized.
             pass 
        
        # Default to NAR if unknown? Or JRA?
        # Safe default to avoid crash
        df['race_type'] = 'NAR' 
        df['race_type_code'] = 0

    # 12. 中央/地方別の過去成績
    df['jra_compatibility'] = 10.0  # JRAでの平均着順（デフォルト10着）
    df['nar_compatibility'] = 10.0  # NARでの平均着順（デフォルト10着）
    df['jra_count'] = 0
    df['nar_count'] = 0

    for i in range(1, 6):
        race_name_col = f'past_{i}_race_name'
        rank_col = f'past_{i}_rank'

        if race_name_col in df.columns and rank_col in df.columns:
            # JRAレースの判定（重賞、G1/G2/G3などのキーワード）
            is_jra_race = df[race_name_col].astype(str).str.contains('G1|G2|G3|重賞|オープン|OP|JRA', na=False, case=False)

            # JRA成績集計
            df.loc[is_jra_race, 'jra_compatibility'] += df.loc[is_jra_race, rank_col]
            df.loc[is_jra_race, 'jra_count'] += 1

            # NAR成績集計
            df.loc[~is_jra_race, 'nar_compatibility'] += df.loc[~is_jra_race, rank_col]
            df.loc[~is_jra_race, 'nar_count'] += 1

    # 平均化
    df['jra_compatibility'] = df.apply(
        lambda x: x['jra_compatibility'] / x['jra_count'] if x['jra_count'] > 0 else 10.0, axis=1
    )
    df['nar_compatibility'] = df.apply(
        lambda x: x['nar_compatibility'] / x['nar_count'] if x['nar_count'] > 0 else 10.0, axis=1
    )

    # 13. 中央からの転入馬フラグ（地方競馬で重要）
    df['is_jra_transfer'] = 0

    # 過去5走にJRAレースがあれば転入馬
    for i in range(1, 6):
        race_name_col = f'past_{i}_race_name'
        if race_name_col in df.columns:
            has_jra_past = df[race_name_col].astype(str).str.contains('G1|G2|G3|重賞|オープン|JRA', na=False, case=False)
            df.loc[has_jra_past, 'is_jra_transfer'] = 1

    # ========== 動的重み付けのための特徴量 ==========

    # 14. 前走の信頼度（休養期間による調整）
    df['last_race_reliability'] = 1.0  # デフォルト: 信頼度100%

    if 'past_1_interval' in df.columns:
        # 休養期間が長いほど、前走の信頼度を下げる
        # 0-30日: 100%
        # 31-60日: 90%
        # 61-90日: 80%
        # 91-180日: 60%（休養明け）
        # 180日以上: 40%（長期休養明け）
        interval = df['past_1_interval']
        df.loc[interval > 180, 'last_race_reliability'] = 0.4
        df.loc[(interval > 90) & (interval <= 180), 'last_race_reliability'] = 0.6
        df.loc[(interval > 60) & (interval <= 90), 'last_race_reliability'] = 0.8
        df.loc[(interval > 30) & (interval <= 60), 'last_race_reliability'] = 0.9

    # 15. コース親和性スコア（過去5走の中で最も今回と似ているレースの順位）
    df['best_similar_course_rank'] = 18.0  # デフォルト: 最下位想定

    # 今回のコース条件を取得
    current_course = df.get('コースタイプ', pd.Series([''] * len(df)))
    current_distance = df.get('distance_val', pd.Series([1600] * len(df)))

    # 過去5走を調べて、最も似ているレースの着順を取得
    for i in range(1, 6):
        # 過去走のコースタイプと距離が今回と似ているかチェック
        # （この実装は簡略化版。本来はpast_i_course_typeなどが必要）
        rank_col = f'past_{i}_rank'
        if rank_col in df.columns:
            # 単純に最良着順を取る（コース条件の詳細情報がない場合）
            df['best_similar_course_rank'] = df[[rank_col, 'best_similar_course_rank']].min(axis=1)

    # 16. 成長曲線スコア（馬齢による調整）
    df['growth_factor'] = 1.0  # デフォルト: 標準

    if '性齢' in df.columns:
        age = df['age'] if 'age' in df.columns else df['性齢'].astype(str).str.extract(r'(\d+)').astype(float).fillna(3.0).iloc[:, 0]

        # 2歳: 急成長期（前走の重みを大きく）
        df.loc[age == 2, 'growth_factor'] = 1.3

        # 3歳: 成長期（やや前走重視）
        df.loc[age == 3, 'growth_factor'] = 1.15

        # 4-5歳: ピーク期（標準）
        df.loc[(age == 4) | (age == 5), 'growth_factor'] = 1.0

        # 6歳以上: ベテラン（過去平均を重視、前走は控えめ）
        df.loc[age >= 6, 'growth_factor'] = 0.85

    # 17. 前走の着順と着差による信頼度
    df['last_race_performance'] = 1.0  # デフォルト: 標準

    if 'past_1_rank' in df.columns:
        last_rank = df['past_1_rank']

        # 前走好走（1-3着）→ 信頼度UP
        df.loc[last_rank <= 3, 'last_race_performance'] = 1.2

        # 前走惨敗（10着以下）→ 信頼度DOWN
        df.loc[last_rank >= 10, 'last_race_performance'] = 0.8

        # 前走大敗（15着以下）→ 大幅DOWN（展開が合わなかった可能性）
        df.loc[last_rank >= 15, 'last_race_performance'] = 0.6

    # 18. 前走と今回のレース間の着順差（連続性）
    df['rank_trend'] = 0.0  # 0: 変化なし、+: 上昇傾向、-: 下降傾向

    if 'past_1_rank' in df.columns and 'past_2_rank' in df.columns:
        # 前走 - 前々走（負の値=成績向上）
        df['rank_trend'] = df['past_2_rank'] - df['past_1_rank']
        # -5以下（大幅向上）、+5以上（大幅悪化）でクリップ
        df['rank_trend'] = df['rank_trend'].clip(-5, 5)

    # 新規特徴量をリストに追加
    new_features = [
        'turf_compatibility',
        'dirt_compatibility',
        'good_condition_avg',
        'heavy_condition_avg',
        'distance_compatibility',
        'jockey_compatibility',
        'last_race_reliability',
        'best_similar_course_rank',
        'growth_factor',
        'last_race_performance',
        'rank_trend',
        'race_class',
        'race_type_code',
        'is_rest_comeback',
        'interval_category',
        'is_consecutive',
        'jra_compatibility',
        'nar_compatibility',
        'is_jra_transfer',
        'is_graded',
        'age_limit'
    ]

    # ========== 新規特徴量: 騎手・厩舎の全体成績（Global Stats） ==========
    # 注意: リークを防ぐため、そのレース以前の成績のみを使用する
    
    # データを日付順にソート（念のため）
    if 'date_dt' not in df.columns:
        df['date_dt'] = pd.to_datetime(df['日付'], format='%Y年%m月%d日', errors='coerce')
    
    df = df.sort_values('date_dt')
    
    # ターゲット変数の準備（NaNは計算対象外）
    if 'rank' not in df.columns:
         df['rank'] = pd.to_numeric(df['着 順'], errors='coerce')
    
    # helper for rolling stats
    def calculate_rolling_stats(series_group, window=None):
        # Shift 1 to avoid using current race result
        # expanding().mean()
        return series_group.shift(1).expanding().mean()
        
    def calculate_rolling_count_sum(df_in, group_col, target_mask_col, new_col_name):
        # Calculate sum of target_mask (wins/top3) and count of races
        # Group by group_col (e.g., Jockey)
        
        # We need a clean way. 
        # rolling_sum = df_in.groupby(group_col)[target_mask_col].transform(lambda x: x.shift(1).expanding().sum())
        # rolling_count = df_in.groupby(group_col)[target_mask_col].transform(lambda x: x.shift(1).expanding().count())
        
        # Optimization: Use global accumulation if dataset is huge, but transform is safe.
        # Ensure we categorize or use string for grouping
        
        # Win flag
        # Calculate rolling mean directly
        return df_in.groupby(group_col)[target_mask_col].transform(lambda x: x.shift(1).expanding().mean())

    # 19. 騎手の直近成績（通算勝率・複勝率）
    if '騎手' in df.columns:
        df['jockey_clean'] = df['騎手'].astype(str).apply(clean_jockey)
        
        # 1着フラグ等 (計算用)
        df['is_win'] = (df['rank'] == 1).astype(int)
        df['is_top3'] = (df['rank'] <= 3).astype(int)

        if input_stats and 'jockey' in input_stats:
             # Inference Mode: Map from stats
             j_stats = input_stats['jockey']
             # map returns NaN if not found -> fillna(0) or average? 0 is safer for now.
             df['jockey_win_rate'] = df['jockey_clean'].map(j_stats['win_rate']).fillna(0.0)
             df['jockey_top3_rate'] = df['jockey_clean'].map(j_stats['top3_rate']).fillna(0.0)
             # Log count? If not in stats, 0.
             if 'count' in j_stats:
                 df['jockey_races_log'] = np.log1p(df['jockey_clean'].map(j_stats['count']).fillna(0))
             else:
                 df['jockey_races_log'] = 0.0
        else:
            # Training Mode: Rolling Stats
            df['jockey_win_rate'] = calculate_rolling_stats(
                df.groupby('jockey_clean')['is_win']
            ).fillna(0.0)
            
            df['jockey_top3_rate'] = calculate_rolling_stats(
                df.groupby('jockey_clean')['is_top3']
            ).fillna(0.0)
            
            df['jockey_races_log'] = np.log1p(
                df.groupby('jockey_clean')['rank'].transform(lambda x: x.shift(1).expanding().count()).fillna(0)
            )
        
        new_features.extend(['jockey_win_rate', 'jockey_top3_rate', 'jockey_races_log'])

        # Now fill missing Jockey Compatibility using Jockey Stats (Proxy)
        # Scale: WinRate is 0.0-1.0 approx (Top Jockeys ~0.15-0.20)
        # Compatibility is Rank (1-18, Lower better).
        # Wait, compatibility was Avg Rank. 5.0 is Good (5th place). 10.0 is Avg.
        # If High Win Rate -> Low Rank (Good).
        # Let's map Top3 Rate (0.0-1.0) to Rank (18.0 - 1.0)
        # Avg Top3 is ~0.25? -> Rank 9?
        # Top Jockey (0.50) -> Rank 4?
        # Low Jockey (0.10) -> Rank 12?
        # Formula: Base 14 - (Top3Rate * 20) -> restricted to 1.0-18.0
        # Example: 0.5 * 20 = 10. 14-10 = 4.0 (Good)
        # Example: 0.1 * 20 = 2. 14-2 = 12.0 (Bad)
        # Example: 0.0 -> 14.0 (Bad)
        
        fallback_compat = 14.0 - (df['jockey_top3_rate'] * 20.0)
        fallback_compat = fallback_compat.clip(1.0, 18.0)
        
        df['jockey_compatibility'] = df['jockey_compatibility'].fillna(fallback_compat)


    # 20. 厩舎の直近成績
    if '厩舎' in df.columns:
        df['stable_clean'] = df['厩舎'].astype(str).str.strip()
        
        if input_stats and 'stable' in input_stats:
             s_stats = input_stats['stable']
             df['stable_win_rate'] = df['stable_clean'].map(s_stats['win_rate']).fillna(0.0)
             df['stable_top3_rate'] = df['stable_clean'].map(s_stats['top3_rate']).fillna(0.0)
        else:
            df['stable_win_rate'] = calculate_rolling_stats(
                df.groupby('stable_clean')['is_win']
            ).fillna(0.0)
            
            df['stable_top3_rate'] = calculate_rolling_stats(
                df.groupby('stable_clean')['is_top3']
            ).fillna(0.0)
        
        new_features.extend(['stable_win_rate', 'stable_top3_rate'])

    # 21. 詳細なコース適性（会場×距離）
    # 会場 + 距離 の識別子を作成
    if '会場' in df.columns and '距離' in df.columns:
        df['course_id'] = df['会場'].astype(str) + '_' + df['距離'].astype(str)
        
        # 馬ごとのコース別成績平均
        # Group by Horse + Course ID
        # Calculate expanding mean of rank
        # We need 'rank'
        
        # Horse ID available?
        if 'horse_id' in df.columns:
            h_id_key = df['horse_id'].apply(clean_id_str)
        else:
            h_id_key = df['馬名'].astype(str)
        
        # Create a grouping key
        df['horse_course_key'] = h_id_key + '_' + df['course_id']
        
        # Calculate Avg Rank in this course previously
        # Calculate Avg Rank in this course previously
        if input_stats and 'course_horse' in input_stats:
             df['course_distance_record'] = df['horse_course_key'].map(input_stats['course_horse']).fillna(10.0)
        else:
            df['course_distance_record'] = df.groupby('horse_course_key')['rank'].transform(
                lambda x: x.shift(1).expanding().mean()
            ).fillna(10.0) # Default to 10th place
        
        new_features.append('course_distance_record')
        
        # Run Style Compatibility with Course
        # Calculate which run style wins most at this course?
        # This requires aggregation of ALL horses at this course, then mapping back.
        # Might be expensive/complex for this step. Skip for now or simpler version:
        # Just use pre-calculated biases if available (venue_characteristics.py)
        pass

    # Cleanup temp columns
    cols_to_drop = ['course_id', 'date_dt']
    # 'jockey_clean', 'stable_clean', 'horse_course_key', 'is_win', 'is_top3' kept if return_stats needed
    
    if not return_stats:
        cols_to_drop.extend(['jockey_clean', 'stable_clean', 'horse_course_key', 'is_win', 'is_top3'])
        
    df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True, errors='ignore')




    # Features to save
    feature_cols = [f'weighted_avg_{f}' for f in features] + new_features
    
    # Add scalar features (Age)
    if '性齢' in df.columns:
         df['age'] = df['性齢'].astype(str).str.extract(r'(\d+)').astype(float).fillna(3.0)
    else:
         df['age'] = 3.0
    feature_cols.append('age')
    


    # ========== 新規特徴量: 騎手・調教師関連（続き） ==========

    # 8. 乗り替わりフラグ（前走と騎手が違う場合）
    df['is_jockey_change'] = 0
    if '騎手' in df.columns and 'past_1_jockey' in df.columns:
        curr_j = df['騎手'].astype(str).str.replace(r'[▲△☆◇★\d]', '', regex=True).str.strip()
        past_j = df['past_1_jockey'].astype(str).str.replace(r'[▲△☆◇★\d]', '', regex=True).str.strip()
        # If past is empty/nan, treat as 0 (no info) or 1? Treat as 0.
        df['is_jockey_change'] = ((curr_j != past_j) & (past_j != "") & (curr_j != "")).astype(int)
    feature_cols.append('is_jockey_change')

    # ========== ID特徴量 (Hashing) ==========
    # 文字列を数値IDに変換してLightGBMのcategory/int特徴量として使用
    
    def hash_str_stable(s):
        if not isinstance(s, str): return 0
        return zlib.adler32(s.encode('utf-8')) & 0xffffffff # Ensure unsigned positive

    # 血統
    for col in ['father', 'mother', 'bms']:
        feat_name = f"{col}_id"
        if col in df.columns:
            df[feat_name] = df[col].apply(hash_str_stable)
        else:
            df[feat_name] = 0
        feature_cols.append(feat_name)
    
    # 騎手・調教師ID
    if '騎手' in df.columns:
         df['jockey_id'] = df['騎手'].astype(str).apply(hash_str_stable)
    else:
         df['jockey_id'] = 0
    feature_cols.append('jockey_id')
    
    if '厩舎' in df.columns: # Trainer
         df['trainer_id'] = df['厩舎'].astype(str).apply(hash_str_stable)
    else:
         df['trainer_id'] = 0
    feature_cols.append('trainer_id')

    # ========== 会場特性×馬タイプの相性特徴量 ==========
    # NOTE: これらの特徴量を使用するには、モデルを再学習する必要があります
    # use_venue_features=True で有効化

    if use_venue_features:
        # Import venue and run style analyzers
        try:
            from venue_characteristics import (
                get_venue_characteristics,
                get_run_style_bias,
                get_distance_bias,
                get_distance_category
            )
            from run_style_analyzer import (
                analyze_horse_run_style,
                get_run_style_code,
                calculate_run_style_consistency
            )
            venue_analysis_available = True
        except ImportError:
            venue_analysis_available = False
            print("Warning: venue_characteristics or run_style_analyzer not found")
    else:
        venue_analysis_available = False

    # ========== 脚質分析特徴量 (常に有効化) ==========
    if VENUE_ANALYSIS_AVAILABLE:
        # 1. 馬の脚質を判定（過去5走のコーナー通過順から）
        if 'run_style_code' not in df.columns:
            df['run_style_cls'] = 'unknown' # Internal temp
            df['run_style_code'] = 0
            df['run_style_consistency'] = 0.0
            df['avg_early_position'] = np.nan
            df['position_change'] = np.nan

            # 一意な馬ごとに計算（少し重いが特徴量として有効）
            # GroupBy apply is cleaner
            def apply_run_style_analysis(sub_df):
                # Take first row's past corners (since specific race row has past history)
                # But wait, past_i_run_style columns are present in EACH row.
                # All rows for the same horse in "database.csv" represent DIFFERENT races.
                # BUT the "past_i_run_style" columns for a specific row are FOR THAT SNAPSHOT.
                # So we can calculate row-by-row OR if history is static?
                # Actually, `add_history_features` builds past_N columns relative to `date_dt`.
                # So each row has the correct past N run styles for THAT moment.
                # So we can just iterate rows or use apply on the dataframe columns!
                pass
            
            # Using loop is slow but safe for now given existing logic structure.
            # But iterating unique horses assumes past history is same? NO. 
            # In database.csv, "past_1" changes for every race of the horse.
            # So we must compute PER ROW.
            
            # Vectorized approach:
            # Construct a list of 'corner_strings' for each row: [past_1_rs, past_2_rs, ...]
            # Then map analyze_horse_run_style.
            
            p_cols = [f'past_{i}_run_style' for i in range(1, 6)]
            # Filter cols that exist
            p_cols = [c for c in p_cols if c in df.columns]
            
            if p_cols:
                # Helper to process one row's corner list
                def analyze_row_styles(row):
                    # Get values
                    corners = [str(row[c]) for c in p_cols if pd.notna(row[c]) and '-' in str(row[c])]
                    if not corners: return 0, 0.0
                    res = analyze_horse_run_style(corners)
                    return get_run_style_code(res['primary_style']), res.get('style_distribution', {}).get(res['primary_style'], 0.0)
                
                # Apply (might catch settingWithCopy warning implies creating new df cols is safer)
                # For speed, maybe just run_style_code?
                # Let's use a simplified apply
                results = df.apply(analyze_row_styles, axis=1, result_type='expand')
                df['run_style_code'] = results[0].astype(int)
                df['run_style_consistency'] = results[1]
                
                feature_cols.extend(['run_style_code', 'run_style_consistency'])

    # ========== 会場特性×馬タイプの相性特徴量 ==========
    if use_venue_features and VENUE_ANALYSIS_AVAILABLE:
        # Load logic requires run_style string which we calculated above?
        # Re-calc 'run_style' string from code if needed or map back?
        # get_run_style_bias takes string.
        # Let's map code to string if needed.
        code_map = {1: 'nige', 2: 'senko', 3: 'sashi', 4: 'oikomi', 0: 'unknown'}
        
        # 2. 会場×脚質の相性スコア
        df['venue_run_style_compatibility'] = 1.0
        
        if '会場' in df.columns and 'run_style_code' in df.columns:
             for idx, row in df.iterrows():
                venue = row['会場']
                rs_code = row['run_style_code']
                run_style_str = code_map.get(rs_code, 'unknown')

                if pd.notna(venue) and run_style_str != 'unknown':
                    compatibility = get_run_style_bias(venue, run_style_str)
                    df.at[idx, 'venue_run_style_compatibility'] = compatibility

        feature_cols.append('venue_run_style_compatibility')

        # 3. 会場×距離の相性スコア
        df['venue_distance_compatibility'] = 1.0

        if '会場' in df.columns and 'distance_val' in df.columns:
            for idx, row in df.iterrows():
                venue = row['会場']
                distance = row['distance_val']

                if pd.notna(venue) and pd.notna(distance):
                    compatibility = get_distance_bias(venue, int(distance))
                    df.at[idx, 'venue_distance_compatibility'] = compatibility

        feature_cols.append('venue_distance_compatibility')

        # 4. 会場特性数値化
        df['straight_length'] = 300.0  # デフォルト
        df['track_width_code'] = 1  # 0=narrow, 1=medium, 2=wide
        df['slope_code'] = 0  # 0=flat, 1=up-down, 2=steep

        if '会場' in df.columns:
            width_map = {'narrow': 0, 'medium': 1, 'wide': 2}
            slope_map = {'flat': 0, 'up-down': 1, 'steep': 2}

            for idx, row in df.iterrows():
                venue = row['会場']

                if pd.notna(venue):
                    char = get_venue_characteristics(venue)

                    # コースタイプに応じた直線長
                    course_type = row.get('コースタイプ', '芝')
                    if '芝' in str(course_type):
                        df.at[idx, 'straight_length'] = char.get('turf_straight', 300.0) or 300.0
                    else:
                        df.at[idx, 'straight_length'] = char['dirt_straight']

                    # 幅と勾配
                    df.at[idx, 'track_width_code'] = width_map.get(char['track_width'], 1)
                    df.at[idx, 'slope_code'] = slope_map.get(char['slope'], 0)

        feature_cols.extend(['straight_length', 'track_width_code', 'slope_code'])

        # 5. 馬場状態×会場の相性（会場ごとに馬場の特性が異なる）
        df['venue_condition_compatibility'] = 1.0

        if '会場' in df.columns and '馬場状態' in df.columns:
            for idx, row in df.iterrows():
                venue = row['会場']
                condition = row['馬場状態']

                if pd.notna(venue) and pd.notna(condition):
                    char = get_venue_characteristics(venue)
                    course_type = row.get('コースタイプ', '芝')

                    # 芝質/ダート質に応じた補正
                    if '芝' in str(course_type):
                        surface = char.get('turf_surface')
                        if surface == 'soft' and '重' in str(condition):
                            # 柔らかい芝で重馬場 -> 相性良い
                            df.at[idx, 'venue_condition_compatibility'] = 1.1
                        elif surface == 'firm' and '良' in str(condition):
                            # 硬い芝で良馬場 -> 相性良い
                            df.at[idx, 'venue_condition_compatibility'] = 1.1
                    else:
                        surface = char.get('dirt_surface')
                        if surface == 'deep' and '重' in str(condition):
                            # 深いダートで重馬場 -> やや不利
                            df.at[idx, 'venue_condition_compatibility'] = 0.95
                        elif surface == 'shallow' and '良' in str(condition):
                            # 浅いダートで良馬場 -> 相性良い
                            df.at[idx, 'venue_condition_compatibility'] = 1.05

        feature_cols.append('venue_condition_compatibility')

        # 6. 枠番の有利度（会場によって外枠/内枠の有利度が異なる）
        df['frame_advantage'] = 1.0

        if '会場' in df.columns and '枠' in df.columns:
            for idx, row in df.iterrows():
                venue = row['会場']
                frame = row['枠']

                if pd.notna(venue) and pd.notna(frame):
                    char = get_venue_characteristics(venue)
                    outer_advantage = char.get('outer_track_advantage', 1.0)

                    # 枠番が大きい（外枠）ほど補正
                    # frame: 1-8の範囲を想定
                    frame_num = int(frame)
                    if frame_num >= 6:  # 外枠
                        df.at[idx, 'frame_advantage'] = outer_advantage
                    elif frame_num <= 3:  # 内枠
                        df.at[idx, 'frame_advantage'] = 2.0 - outer_advantage

        feature_cols.append('frame_advantage')

    # ========== Data-Driven Course Characteristics (If Stats Provided) ==========
    if input_stats:
         # Construct Key
         if 'course_bias_key' not in df.columns:
             df['course_bias_key'] = (
                 df['会場'].astype(str) + '_' + 
                 df['distance_val'].astype(int).astype(str) + '_' + 
                 df['course_type_code'].astype(str) + '_' + 
                 df['rotation_code'].astype(str)
             )
         
         # 1. Frame Bias
         if 'course_frame_bias' in input_stats and '枠' in df.columns:
             # Map is tricky with nested dict.
             # df.apply is easiest but slow.
             # Optimized: Create a flat key comparison?
             # Or just apply lambda.
             stats_fb = input_stats['course_frame_bias']
             def get_fb(row):
                 k = row['course_bias_key']
                 w = str(row['枠'])
                 if k in stats_fb and w in stats_fb[k]:
                     return stats_fb[k][w]
                 return 0.08 # Default avg win rate ~1/12? Max 1/8=0.125. 16/18 head -> 0.05. 0.07 is distinct.
             
             df['dd_frame_bias'] = df.apply(get_fb, axis=1)
             feature_cols.append('dd_frame_bias')
         
         # 2. Run Style Bias
         if 'course_run_style_bias' in input_stats and 'run_style_code' in df.columns:
             stats_rsb = input_stats['course_run_style_bias']
             def get_rsb(row):
                 k = row['course_bias_key']
                 r = str(row['run_style_code'])
                 if k in stats_rsb and r in stats_rsb[k]:
                     return stats_rsb[k][r]
                 return 0.0
             
             df['dd_run_style_bias'] = df.apply(get_rsb, axis=1)
             feature_cols.append('dd_run_style_bias')

    else:
         # Training Mode: Calculate Rolling Bias
         # Ensure is_win exists (it might have been dropped)
         if 'is_win' not in df.columns:
             if 'rank' in df.columns:
                 df['is_win'] = (df['rank'] == 1).astype(int)
             else:
                 # Should not happen in training but safe fallback
                 df['is_win'] = 0

         # Ensure course_bias_key exists
         if 'course_bias_key' not in df.columns:
             df['course_bias_key'] = (
                 df['会場'].astype(str) + '_' + 
                 df['distance_val'].astype(int).astype(str) + '_' + 
                 df['course_type_code'].astype(str) + '_' + 
                 df['rotation_code'].astype(str)
             )
         
         # 1. Frame Bias
         if '枠' in df.columns:
             # Group by Key + Frame
             # We can concat key + frame for simple groupby
             df['key_frame'] = df['course_bias_key'] + '_' + df['枠'].astype(str)
             df['dd_frame_bias'] = df.groupby('key_frame')['is_win'].transform(
                 lambda x: x.shift(1).expanding().mean()
             ).fillna(0.0) # Default 0 ok? Or avg? 0 is fine if feature is rate.
             feature_cols.append('dd_frame_bias')
             
         # 2. Run Style Bias
         if 'run_style_code' in df.columns:
             df['key_run'] = df['course_bias_key'] + '_' + df['run_style_code'].astype(str)
             df['dd_run_style_bias'] = df.groupby('key_run')['is_win'].transform(
                 lambda x: x.shift(1).expanding().mean()
             ).fillna(0.0)
             feature_cols.append('dd_run_style_bias')
             
         # Remove temp keys
         df.drop(columns=['key_frame', 'key_run'], inplace=True, errors='ignore')



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
    
    # Return Logic with Stats
    if return_stats:
        stats_data = {}
        # Jockey Stats
        if 'jockey_clean' in df.columns:
            j_grp = df.groupby('jockey_clean')
            stats_data['jockey'] = {
                'win_rate': j_grp['is_win'].mean().to_dict(),
                'top3_rate': j_grp['is_top3'].mean().to_dict(),
                'count': j_grp['rank'].count().to_dict()
            }
            
        # Stable Stats
        if 'stable_clean' in df.columns:
            s_grp = df.groupby('stable_clean')
            stats_data['stable'] = {
                'win_rate': s_grp['is_win'].mean().to_dict(),
                'top3_rate': s_grp['is_top3'].mean().to_dict()
            }
            
        # Course Stats
        # Re-calc key if needed
        if 'horse_course_key' not in df.columns and 'venue_id' in df.columns and 'distance' in df.columns:
             h_id_col = 'horse_id' if 'horse_id' in df.columns else '馬名'
             c_id = df['venue_id'].astype(str) + '_' + df['distance'].astype(str)
             df['horse_course_key'] = df[h_id_col].astype(str) + '_' + c_id

        if 'horse_course_key' in df.columns:
             stats_data['course_horse'] = df.groupby('horse_course_key')['rank'].mean().to_dict()

        # Add Jockey-Horse & Jockey-Trainer Stats
        # Re-construct keys if missing (likely dropped)
        if 'hj_key' not in df.columns or 'tj_key' not in df.columns:
             jockey_series = df['騎手'].astype(str).apply(clean_jockey) if '騎手' in df.columns else pd.Series(['']*len(df))
             h_key = df['horse_id'].apply(clean_id_str) if 'horse_id' in df.columns else df['馬名'].astype(str)
             
             # Use same cleaner for stable
             t_key = df['厩舎'].astype(str).apply(clean_stable_name) if '厩舎' in df.columns else pd.Series(['']*len(df))
             
             df['hj_key'] = h_key + '_' + jockey_series
             df['tj_key'] = t_key + '_' + jockey_series
             
        stats_data['hj_compatibility'] = df.groupby('hj_key')['rank'].mean().to_dict()
        stats_data['tj_compatibility'] = df.groupby('tj_key')['rank'].mean().to_dict()

        # Add Stats for Global Features
        # Determine h_key again just in case (though it was dropped)
        if 'horse_id' in df.columns:
            df['h_key'] = df['horse_id'].apply(clean_id_str)
        else:
            df['h_key'] = df['馬名'].astype(str)

        # Re-create masks if needed? No, we need to re-calc group means for the WHOLE dataset
        # We can just groupby h_key and apply logic? No, conditional mean.
        # Use helper
        def get_group_mean(mask_name):
            # Create masked rank
            masked_rank = np.where(df[mask_name], df['rank'], np.nan)
            return pd.Series(masked_rank).groupby(df['h_key']).mean().dropna().to_dict()

        # Course Type
        
        # Temp masks for stats
        df['is_turf_temp'] = (df['course_type_code'] == 1)
        df['is_dirt_temp'] = (df['course_type_code'] == 2)
        stats_data['horse_turf'] = df[df['is_turf_temp']].groupby('h_key')['rank'].mean().to_dict()
        stats_data['horse_dirt'] = df[df['is_dirt_temp']].groupby('h_key')['rank'].mean().to_dict()

        # Condition
        df['is_good_temp'] = (df['condition_code'] == 1)
        df['is_heavy_temp'] = (df['condition_code'] >= 3)
        stats_data['horse_good'] = df[df['is_good_temp']].groupby('h_key')['rank'].mean().to_dict()
        stats_data['horse_heavy'] = df[df['is_heavy_temp']].groupby('h_key')['rank'].mean().to_dict()
        
        # Distance
        # Re-calc cats
        dist_val_s = df['distance_val'].fillna(1600)
        df['dist_cat_temp'] = pd.cut(dist_val_s, bins=[0, 1399, 1899, 2499, 9999], labels=['Sprint', 'Mile', 'Intermediate', 'Long'])
        for cat in ['Sprint', 'Mile', 'Intermediate', 'Long']:
            stats_data[f'horse_dist_{cat}'] = df[df['dist_cat_temp'] == cat].groupby('h_key')['rank'].mean().to_dict()
            
        # Stable Stats
        # Re-create t_key for stats
        if 't_key' not in df.columns:
            df['t_key'] = df['厩舎'].astype(str).apply(clean_stable_name) if '厩舎' in df.columns else ""
        
        # Calculate Win Rate (Rank 1)
        stats_data['stable_win_rate'] = df.groupby('t_key')['is_win'].mean().to_dict()
        
        # Calculate Top 3 Rate (Rank <= 3)
        # Check if is_top3 exists, or calc it
        df['is_top3_temp'] = (df['rank'] <= 3).astype(int)
        stats_data['stable_top3_rate'] = df.groupby('t_key')['is_top3_temp'].mean().to_dict()
        
        # Cleanup
        df.drop(columns=['h_key', 't_key', 'is_top3_temp', 'is_turf_temp', 'is_dirt_temp', 'is_good_temp', 'is_heavy_temp', 'dist_cat_temp'], inplace=True, errors='ignore')


        # Course Bias Stats (Frame & RunStyle)
        # Key: Venue_Distance_CourseType_Rotation
        if 'course_bias_key' not in df.columns:
             # Construct key
             df['course_bias_key'] = (
                 df['会場'].astype(str) + '_' + 
                 df['distance_val'].astype(int).astype(str) + '_' + 
                 df['course_type_code'].astype(str) + '_' + 
                 df['rotation_code'].astype(str)
             )
        
        # 1. Frame Bias (Waku)
        if '枠' in df.columns:
            # Group by [Key, Waku] -> Win Rate
            # We want a nested dict: Key -> {Waku: Rate}
            # Or simpler: Key_Waku -> Rate? Nested matches structure.
            # Let's use MultiIndex to dict
            fb = df.groupby(['course_bias_key', '枠'])['is_win'].mean()
            # Convert to {key: {waku: rate}} is hard directly from series?
            # Iterate unique keys?
            # Optimized:
            stats_data['course_frame_bias'] = {}
            # Reset index to iterate
            fb_df = fb.reset_index()
            for _, row in fb_df.iterrows():
                k = row['course_bias_key']
                w = str(row['枠']) # Ensure str key for JSON/Pickle
                v = row['is_win']
                if k not in stats_data['course_frame_bias']:
                    stats_data['course_frame_bias'][k] = {}
                stats_data['course_frame_bias'][k][w] = v

        # 2. Run Style Bias
        if 'run_style_code' in df.columns:
            rsb = df.groupby(['course_bias_key', 'run_style_code'])['is_win'].mean()
            stats_data['course_run_style_bias'] = {}
            rsb_df = rsb.reset_index()
            for _, row in rsb_df.iterrows():
                k = row['course_bias_key']
                r = str(row['run_style_code'])
                v = row['is_win']
                if k not in stats_data['course_run_style_bias']:
                    stats_data['course_run_style_bias'][k] = {}
                stats_data['course_run_style_bias'][k][r] = v


        return df[keep_cols].copy(), stats_data

    return df[keep_cols].copy()

def calculate_features(input_csv, output_path, lambda_decay=0.5, use_venue_features=False):
    """
    特徴量を計算してCSVに保存

    Args:
        input_csv: 入力CSVパス（database.csvまたはdatabase_nar.csv）
        output_path: 出力CSVパス（processed_data.csvまたはprocessed_data_nar.csv）
        lambda_decay: 時間減衰パラメータ（デフォルト0.5）
        use_venue_features: 会場特性特徴量を使用するか（デフォルトFalse）
                           Trueにすると11個の会場関連特徴量が追加される
    """
    print(f"Loading {input_csv}...")
    df = pd.read_csv(input_csv)

    print(f"  use_venue_features={use_venue_features}")
    processed = process_data(df, lambda_decay, use_venue_features=use_venue_features)
    
    # For training, we need binary target
    # 変更: 3着以内 → 1着のみ（単勝予測に適した設定）
    #
    # 理由:
    # - EV計算では単勝オッズを使用しているため、1着予測が正しい
    # - 3着以内を勝ちとすると、モデル出力とEV計算が矛盾する
    # - 競馬予測の目的は「1着を当てること」
    if 'rank' in processed.columns:
        processed['target_win'] = (processed['rank'] == 1).astype(int)  # 1着のみ
        processed['target_top3'] = (processed['rank'] <= 3).astype(int)  # 互換性のため残す
    else:
        processed['target_win'] = 0
        processed['target_top3'] = 0
    
    # Clean NaNs in features?
    processed = processed.fillna(0) # Simple imputation
    
    processed.to_csv(output_path, index=False)
    print(f"Saved processed data to {output_path} ({len(processed)} rows)")

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "database.csv")
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "processed_data.csv")
    calculate_features(db_path, out_path)
