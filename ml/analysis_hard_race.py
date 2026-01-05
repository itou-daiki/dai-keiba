import pandas as pd
import numpy as np

def calculate_hard_race_metrics(df):
    """
    Calculates metrics to identify 'hard' (predictable/firm) races based on odds distribution.
    
    Metrics:
    - odds_gap_X_Y: Difference in odds between popularity rank X and Y.
    - odds_std_1_2_3: Standard deviation of odds for top 3 popular horses.
    - odds_std_1_6: Standard deviation of odds for top 6 popular horses.
    
    Args:
        df: DataFrame containing at least 'race_id', '単勝' (Odds), and '人 気' (Popularity).
            If columns are named differently, they will be coerced.
            
    Returns:
        DataFrame: One row per race_id with calculated metrics.
    """
    # 1. Preprocessing
    # Ensure necessary columns exist or map them
    req_cols = ['race_id']
    
    # Odds column mapping
    if 'odds' in df.columns:
        odds_col = 'odds'
    elif '単勝' in df.columns:
        odds_col = '単勝'
    elif '単勝 オッズ' in df.columns:
        odds_col = '単勝 オッズ'
    else:
        # Cannot calculate without odds
        return pd.DataFrame()

    # Popularity column mapping
    if 'popularity' in df.columns:
        pop_col = 'popularity'
    elif '人 気' in df.columns:
        pop_col = '人 気'
    else:
        # Cannot calculate without popularity
        return pd.DataFrame()

    # Create working copy
    work_df = df[['race_id', odds_col, pop_col]].copy()
    
    # Coerce numeric
    work_df['odds_val'] = pd.to_numeric(work_df[odds_col], errors='coerce')
    work_df['pop_val'] = pd.to_numeric(work_df[pop_col], errors='coerce')
    
    # Drop invalid rows
    work_df.dropna(subset=['odds_val', 'pop_val'], inplace=True)
    
    # 2. Calculation per Race
    results = []
    
    # Group by race_id
    grouped = work_df.groupby('race_id')
    
    for race_id, group in grouped:
        # Sort by popularity (ascending: 1, 2, 3...)
        group = group.sort_values('pop_val')
        
        # Get odds for top 6
        # We use 'pop_val' to ensure we get the actual 1st popular, 2nd popular etc.
        # But sometimes popularity might be missing or duplicate. 
        # Safety: Take top 6 sorted rows.
        top_6 = group.head(6)
        
        # Need at least 2 horses for gap, 3 for std 1-2-3
        if len(top_6) < 2:
            continue
            
        metrics = {'race_id': race_id}
        
        # Extract odds values as list
        # Ensure we have odds for rank 1, 2, 3, 4, 5, 6
        # We can map pop_val to odds if strictly 1..6 exist
        # Or just take position in sorted list as approximation if pop_val is messy
        # Let's strictly use pop_val if possible, else positional
        
        odds_map = {}
        for _, row in top_6.iterrows():
            p = int(row['pop_val'])
            o = row['odds_val']
            odds_map[p] = o
            
        # Calculate Gaps
        # 1-2
        if 1 in odds_map and 2 in odds_map:
            metrics['odds_gap_1_2'] = odds_map[2] - odds_map[1]
        else:
            metrics['odds_gap_1_2'] = np.nan
            
        # 2-3
        if 2 in odds_map and 3 in odds_map:
            metrics['odds_gap_2_3'] = odds_map[3] - odds_map[2]
        else:
            metrics['odds_gap_2_3'] = np.nan
            
        # 3-4
        if 3 in odds_map and 4 in odds_map:
            metrics['odds_gap_3_4'] = odds_map[4] - odds_map[3]
        else:
            metrics['odds_gap_3_4'] = np.nan

        # 4-5
        if 4 in odds_map and 5 in odds_map:
            metrics['odds_gap_4_5'] = odds_map[5] - odds_map[4]
        else:
            metrics['odds_gap_4_5'] = np.nan
            
        # 5-6
        if 5 in odds_map and 6 in odds_map:
            metrics['odds_gap_5_6'] = odds_map[6] - odds_map[5]
        else:
            metrics['odds_gap_5_6'] = np.nan
            
        # Calculate Std Dev 1-2-3
        top_3_odds = [odds_map[p] for p in [1, 2, 3] if p in odds_map]
        if len(top_3_odds) >= 2: # Std dev needs at least 2? Ideally 3 for "1-2-3"
             metrics['odds_std_1_2_3'] = np.std(top_3_odds, ddof=1) # Sample std dev
        else:
             metrics['odds_std_1_2_3'] = np.nan
             
        # Calculate Std Dev 1-6
        top_6_odds = [odds_map[p] for p in range(1, 7) if p in odds_map]
        if len(top_6_odds) >= 2:
             metrics['odds_std_1_6'] = np.std(top_6_odds, ddof=1)
        else:
             metrics['odds_std_1_6'] = np.nan

        results.append(metrics)
        
    return pd.DataFrame(results)
