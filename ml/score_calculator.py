import pandas as pd
import numpy as np

def calculate_pure_compat(row, weights=None):
    """
    純粋な適性指数（Compat_Index）を計算
    
    Args:
        row: DataFrameの行
        weights: 重み辞書 {'jockey': 0.4, 'distance': 0.3, 'course': 0.3}
                 Noneの場合はデフォルト値を使用
    """
    if weights is None:
        weights = {'jockey': 0.4, 'distance': 0.3, 'course': 0.3}
        
    scores = []
    active_weights = []
    
    # 騎手適性 (Jockey)
    if 'jockey_compatibility' in row and pd.notna(row['jockey_compatibility']):
        scores.append(float(row['jockey_compatibility']) * weights.get('jockey', 0.4))
        active_weights.append(weights.get('jockey', 0.4))
        
    # 距離適性 (Distance)
    if 'distance_compatibility' in row and pd.notna(row['distance_compatibility']):
        scores.append(float(row['distance_compatibility']) * weights.get('distance', 0.3))
        active_weights.append(weights.get('distance', 0.3))
        
    # コース適性 (Course)
    # 事前に course_compatibility が計算されている前提
    if 'course_compatibility' in row and pd.notna(row['course_compatibility']):
        scores.append(float(row['course_compatibility']) * weights.get('course', 0.3))
        active_weights.append(weights.get('course', 0.3))
    
    if not active_weights: return 50.0
    
    # Weighted Average Rank
    avg_rank = sum(scores) / sum(active_weights)
    
    # Normalize Rank (1.0 - 18.0) to Score (100 - 0)
    # 1位=100点, 18位=0点
    score = (18.0 - avg_rank) / 17.0 * 100
    return max(0, min(100, score))

def calculate_bloodline_index(row, weights=None):
    """
    血統指数（Bloodline_Index）を計算
    
    Args:
        row: DataFrameの行
        weights: 重み辞書 {'sire': 0.7, 'bms': 0.3}
                 Noneの場合はデフォルト値を使用
    """
    if weights is None:
        weights = {'sire': 0.7, 'bms': 0.3}
        
    if 'sire_win_rate' not in row or pd.isna(row['sire_win_rate']):
        return 50.0
    
    sire = row.get('sire_win_rate', 0.08)
    bms = row.get('bms_win_rate', 0.07)
    
    # Weighted Rate
    rate = (sire * weights.get('sire', 0.7)) + (bms * weights.get('bms', 0.3))
    
    # Scaling (Average win rate ~8-10% -> Score 50-60)
    # 0.08 * 625 = 50
    score = rate * 625
    return max(0, min(100, score))

def calculate_d_index(df, config=None):
    """
    D指数を計算してDataFrameに追加する
    
    Args:
        df: 入力DataFrame (AI_Score, 各種適性値が必要)
        config: 設定辞書 (重み設定など)
               {
                   'd_index': {'ai': 0.4, 'compat': 0.5, 'blood': 0.1},
                   'compat': {'jockey': 0.4, 'distance': 0.3, 'course': 0.3},
                   'blood': {'sire': 0.7, 'bms': 0.3}
               }
    Returns:
        D指数が追加されたDataFrame
    """
    if config is None:
        # Defaults
        config = {
            'd_index': {'ai': 0.4, 'compat': 0.5, 'blood': 0.1},
            'compat': {'jockey': 0.4, 'distance': 0.3, 'course': 0.3},
            'blood': {'sire': 0.7, 'bms': 0.3}
        }
    
    # Ensure course_compatibility exists
    if 'course_compatibility' not in df.columns:
        # Logic from public_app to select turf/dirt
        if 'turf_compatibility' in df.columns and 'dirt_compatibility' in df.columns:
            if 'コースタイプ' in df.columns:
                df['course_compatibility'] = df.apply(
                    lambda row: row['turf_compatibility'] if '芝' in str(row.get('コースタイプ', ''))
                               else row['dirt_compatibility'] if 'ダ' in str(row.get('コースタイプ', ''))
                               else row['turf_compatibility'],
                    axis=1
                )
            else:
                 df['course_compatibility'] = df['turf_compatibility']
        elif 'turf_compatibility' in df.columns:
             df['course_compatibility'] = df['turf_compatibility']
        elif 'dirt_compatibility' in df.columns:
             df['course_compatibility'] = df['dirt_compatibility']
        else:
             df['course_compatibility'] = 10.0 # Default poor rank

    # 1. Calc Compat Index
    df['Compat_Index'] = df.apply(lambda row: calculate_pure_compat(row, config.get('compat')), axis=1)
    
    # 2. Calc Bloodline Index
    df['Bloodline_Index'] = df.apply(lambda row: calculate_bloodline_index(row, config.get('blood')), axis=1)
    
    # 3. Calc D-Index
    w_ai = config['d_index'].get('ai', 0.4)
    w_compat = config['d_index'].get('compat', 0.5)
    w_blood = config['d_index'].get('blood', 0.1)
    
    # If AI_Score is missing, fallback to 50 or calc from prob
    ai_score = df['AI_Score'] if 'AI_Score' in df.columns else (df['AI_Prob'] * 100 if 'AI_Prob' in df.columns else 50)
    
    df['D_Index'] = (ai_score * w_ai) + (df['Compat_Index'] * w_compat) + (df['Bloodline_Index'] * w_blood)
    df['D_Index'] = df['D_Index'].clip(1, 99)
    
    return df
