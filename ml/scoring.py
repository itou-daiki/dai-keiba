import pandas as pd
import numpy as np

def calculate_pure_compat(row, weights={'jockey': 0.4, 'distance': 0.3, 'course': 0.3}):
    """
    Calculates pure compatibility index (0-100) based on Jockey, Distance, and Course compatibility.
    Accepts dynamic sub-weights.
    """
    scores = []
    active_weights = []
    
    # Weighted Compatibility Calculation
    if pd.notna(row.get('jockey_compatibility')): 
        scores.append(float(row['jockey_compatibility']) * weights['jockey'])
        active_weights.append(weights['jockey'])
        
    if pd.notna(row.get('distance_compatibility')): 
        scores.append(float(row['distance_compatibility']) * weights['distance'])
        active_weights.append(weights['distance'])
        
    if pd.notna(row.get('course_compatibility')): 
        scores.append(float(row['course_compatibility']) * weights['course'])
        active_weights.append(weights['course'])
    
    if not active_weights: return 50.0
    
    # Weighted Average Rank
    avg_rank = sum(scores) / sum(active_weights)
    
    # Normalize Rank (1.0 - 18.0) to Score (100 - 0)
    score = (18.0 - avg_rank) / 17.0 * 100
    return max(0, min(100, score))

def calculate_bloodline_index(row):
    """
    Calculates bloodline index (0-100) based on Sire and BMS win rates.
    """
    if pd.isna(row.get('sire_win_rate')): return 50.0 
    
    sire = row.get('sire_win_rate', 0.08)
    bms = row.get('bms_win_rate', 0.07)
    # Weighted Rate
    rate = (sire * 0.7) + (bms * 0.3)
    # Scaling
    score = rate * 625
    return max(0, min(100, score))

def calculate_d_index(row, config):
    """
    Calculates the final D-Index based on provided config.
    Config structure:
    {
        "top_level": {"ai": 0.4, ...},
        "compat_sub_weights": {"jockey": 0.4, ...}
    }
    """
    weights = config.get('top_level', {'ai': 0.4, 'compat': 0.5, 'blood': 0.1})
    sub_weights = config.get('compat_sub_weights', {'jockey': 0.4, 'distance': 0.3, 'course': 0.3})

    # Recalculate component indices if they are missing or if we want to ensure latest weights are used
    # Ideally, Compat_Index in row might be old if weights changed, so preferably we calculate on fly if possible.
    # But usually 'row' comes from DF. Let's support passing raw components or calculating them.
    
    ai_score = row.get('AI_Score', 0)
    # Re-calculate compat index with dynamic weights
    compat_index = calculate_pure_compat(row, sub_weights)
    blood_index = row.get('Bloodline_Index', calculate_bloodline_index(row))
    
    d_index = (ai_score * weights['ai']) + (compat_index * weights['compat']) + (blood_index * weights['blood'])
    return max(1, min(99, d_index))
