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
    # Added interval, speed
    features = ['rank', 'run_style', 'last_3f', 'horse_weight', 'odds', 'weather', 'weight_change', 'interval', 'speed']
    
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

    # ========== 新規特徴量: コース・馬場適性 ==========

    # 1. 芝適性（芝での平均着順）
    df['turf_compatibility'] = 10.0
    df['dirt_compatibility'] = 10.0
    
    # Vectorized calculation using numpy check
    # We can assume rows are independent
    # Correct logic: For each row (horse), calculate avg rank in Turf/Dirt
    
    # Initialize separate sums/counts for each row
    turf_sums = pd.Series(0.0, index=df.index)
    turf_counts = pd.Series(0, index=df.index)
    dirt_sums = pd.Series(0.0, index=df.index)
    dirt_counts = pd.Series(0, index=df.index)

    for i in range(1, 6):
        # Use course_type_code if available (1=Turf, 2=Dirt)
        # Fallback to race_name string check if needed? 
        # But we added course_type_code in add_history_features.
        
        c_code_col = f'past_{i}_course_type_code'
        rank_col = f'past_{i}_rank'
        
        # If code not computed (scraper not run yet, manual update?), fallback to name regex?
        # Let's rely on c_code_col first, if 0 try regex.
        
        # Actually straightforward:
        code_series = df[c_code_col] if c_code_col in df.columns else pd.Series(0, index=df.index)
        rank_series = df[rank_col] if rank_col in df.columns else pd.Series(18, index=df.index) # Use filled 18 if missing? existing logic filled it.

        # Logic for Turf (1)
        is_turf = (code_series == 1)
        # If code is 0 but name has '芝'?
        race_name_col = f'past_{i}_race_name'
        if race_name_col in df.columns:
             # Only fill if 0?
             is_turf_name = df[race_name_col].astype(str).str.contains('芝', na=False)
             is_turf = is_turf | ((code_series == 0) & is_turf_name)

        turf_sums += np.where(is_turf, rank_series, 0)
        turf_counts += np.where(is_turf, 1, 0)
        
        # Logic for Dirt (2)
        is_dirt = (code_series == 2)
        if race_name_col in df.columns:
             is_dirt_name = df[race_name_col].astype(str).str.contains('ダ', na=False)
             is_dirt = is_dirt | ((code_series == 0) & is_dirt_name)

        dirt_sums += np.where(is_dirt, rank_series, 0)
        dirt_counts += np.where(is_dirt, 1, 0)

    # Calculate Avg
    df['turf_compatibility'] = np.where(turf_counts > 0, turf_sums / turf_counts, 10.0)
    df['dirt_compatibility'] = np.where(dirt_counts > 0, dirt_sums / dirt_counts, 10.0)

    # 2. 馬場状態適性（良/稍重/重/不良での平均着順）
    df['good_condition_avg'] = 0.0
    df['heavy_condition_avg'] = 0.0
    df['good_count'] = 0
    df['heavy_count'] = 0

    for i in range(1, 6):
        cond_col = f'past_{i}_condition'
        rank_col = f'past_{i}_rank'

        if cond_col in df.columns and rank_col in df.columns:
            # 良馬場（1）
            is_good = df[cond_col] == 1
            df.loc[is_good, 'good_condition_avg'] += df.loc[is_good, rank_col]
            df.loc[is_good, 'good_count'] += 1

            # 重馬場（3以上: 重/不良）
            is_heavy = df[cond_col] >= 3
            df.loc[is_heavy, 'heavy_condition_avg'] += df.loc[is_heavy, rank_col]
            df.loc[is_heavy, 'heavy_count'] += 1

    # 平均化
    df['good_condition_avg'] = df.apply(
        lambda x: x['good_condition_avg'] / x['good_count'] if x['good_count'] > 0 else 10.0, axis=1
    )
    df['heavy_condition_avg'] = df.apply(
        lambda x: x['heavy_condition_avg'] / x['heavy_count'] if x['heavy_count'] > 0 else 10.0, axis=1
    )

    # 3. 距離適性（現在のレース距離との近さで判定）
    # 現在の距離に±200m以内の過去レースでの平均着順
    df['distance_compatibility'] = 10.0  # デフォルト

    # 3. 距離適性（現在のレース距離との近さで判定）
    # 現在の距離に±200m以内の過去レースでの平均着順
    df['distance_compatibility'] = 10.0  # デフォルト

    if '距離' in df.columns:
        current_distance = pd.to_numeric(df['距離'], errors='coerce').fillna(1600)
        
        dist_sums = pd.Series(0.0, index=df.index)
        dist_counts = pd.Series(0, index=df.index)

        for i in range(1, 6):
            rank_col = f'past_{i}_rank'
            dist_col_hist = f'past_{i}_distance' # New explicit column
            race_name_col = f'past_{i}_race_name'
            
            # Use explicit distance if available
            if dist_col_hist in df.columns:
                p_dist = df[dist_col_hist]
            else:
                 p_dist = pd.Series(np.nan, index=df.index)

            # Fallback to regex
            if race_name_col in df.columns:
                # Fill NaNs in p_dist with regex extraction
                def extract_distance(name):
                    if not isinstance(name, str): return np.nan
                    match = re.search(r'(\d{3,4})m?', name)
                    if match: return float(match.group(1))
                    return np.nan
                extracted = df[race_name_col].apply(extract_distance)
                p_dist = p_dist.fillna(extracted)

            rank_series = df[rank_col] if rank_col in df.columns else pd.Series(18, index=df.index)
            
            # Check diff
            # We align indices automatically? Series operations align by index.
            diff = (p_dist - current_distance).abs()
            is_match = (diff <= 200) & p_dist.notna() & current_distance.notna()
            
            dist_sums += np.where(is_match, rank_series, 0)
            dist_counts += np.where(is_match, 1, 0)

        df['distance_compatibility'] = np.where(dist_counts > 0, dist_sums / dist_counts, 10.0)

    # ========== 新規特徴量: レース間隔関連 ==========

    # 4. 休養明けフラグ（最小レース間隔が90日以上）
    df['is_rest_comeback'] = 0

    min_interval_cols = [f'past_{i}_interval' for i in range(1, 6) if f'past_{i}_interval' in df.columns]
    if min_interval_cols:
        min_interval = df[min_interval_cols].min(axis=1)
        df['is_rest_comeback'] = (min_interval >= 90).astype(int)

    # 5. レース間隔カテゴリ（直近レースからの間隔）
    # 1: 2週以内, 2: 1ヶ月以内, 3: 2ヶ月以内, 4: 3ヶ月以上
    df['interval_category'] = 2  # デフォルト

    if 'past_1_interval' in df.columns:
        df['interval_category'] = df['past_1_interval'].apply(
            lambda x: 1 if x <= 14 else (2 if x <= 30 else (3 if x <= 60 else 4))
        )

    # 6. 連闘フラグ（2週間以内の連続出走）
    df['is_consecutive'] = 0
    if 'past_1_interval' in df.columns:
        df['is_consecutive'] = (df['past_1_interval'] <= 14).astype(int)

    # ========== 新規特徴量: 騎手との相性 ==========

    # 7. 現在の騎手との過去成績（過去5走で同じ騎手の時の平均着順）
    df['jockey_compatibility'] = 10.0  # デフォルト

    # 7. 現在の騎手との過去成績（過去5走で同じ騎手の時の平均着順）
    df['jockey_compatibility'] = 10.0  # デフォルト

    # Helper to clean jockey name
    def clean_jockey(name):
        if not isinstance(name, str): return ""
        # Remove symbols like ▲, △, ☆, ◇, numbers?
        # Typically "▲丹内" -> "丹内"
        return re.sub(r'[▲△☆◇★\d]', '', name).strip()

    if '騎手' in df.columns:
        current_jockey = df['騎手'].astype(str).apply(clean_jockey)
        
        j_sums = pd.Series(0.0, index=df.index)
        j_counts = pd.Series(0, index=df.index)

        for i in range(1, 6):
            past_jockey_col = f'past_{i}_jockey'
            rank_col = f'past_{i}_rank'
            
            if past_jockey_col in df.columns:
                p_jockey = df[past_jockey_col].astype(str).apply(clean_jockey)
                rank_series = df[rank_col] if rank_col in df.columns else pd.Series(18, index=df.index)
                
                is_same = (p_jockey == current_jockey) & (current_jockey != "")
                
                j_sums += np.where(is_same, rank_series, 0)
                j_counts += np.where(is_same, 1, 0)

        df['jockey_compatibility'] = np.where(j_counts > 0, j_sums / j_counts, 10.0)

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
            elif 'オープン' in name or 'OP' in name:
                return 6
            elif '3勝' in name:
                return 5
            elif '2勝' in name:
                return 4
            elif '1勝' in name:
                return 3
            elif '未勝利' in name:
                return 2
            elif '新馬' in name:
                return 1
            return 0

        df['race_class'] = df['レース名'].apply(classify_race)

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

    # 新規特徴量をリストに追加
    new_features = [
        'turf_compatibility',
        'dirt_compatibility',
        'good_condition_avg',
        'heavy_condition_avg',
        'distance_compatibility',
        'is_rest_comeback',
        'interval_category',
        'is_consecutive',
        'jockey_compatibility',
        'race_class',
        'is_graded',
        'age_limit',
        'race_type_code',
        'jra_compatibility',
        'nar_compatibility',
        'is_jra_transfer'
    ]

    # Features to save
    feature_cols = [f'weighted_avg_{f}' for f in features] + new_features
    
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
