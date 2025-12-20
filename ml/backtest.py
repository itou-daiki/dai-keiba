"""
バックテスト機能
過去データでモデルの実際の収支を検証
"""

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split


def run_backtest(model_path, data_path, betting_strategy='ev_positive', bet_amount=100):
    """
    バックテストを実行

    Args:
        model_path: 学習済みモデルのパス
        data_path: 検証用データのパス
        betting_strategy: 賭け方
            - 'ev_positive': EV > 0 の馬すべてに賭ける
            - 'top_ev': 各レースでEV最大の馬に賭ける
            - 'top3': AI予測確率トップ3に賭ける
        bet_amount: 1レースあたりの賭け金（円）

    Returns:
        dict: バックテスト結果
    """

    # Load model
    if not os.path.exists(model_path):
        print(f"Model file {model_path} not found.")
        return None

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # Load data
    if not os.path.exists(data_path):
        print(f"Data file {data_path} not found.")
        return None

    df = pd.read_csv(data_path)

    # Prepare features
    target_col = 'target_top3'
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']

    # Keep race_id and rank for evaluation
    race_ids = df['race_id'].copy() if 'race_id' in df.columns else None
    actual_ranks = df['rank'].copy() if 'rank' in df.columns else None
    horse_names = df['馬名'].copy() if '馬名' in df.columns else None

    drop_cols = [c for c in df.columns if c in meta_cols or c == target_col]
    X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])

    if len(X) == 0:
        print("No features available.")
        return None

    # Predict
    print("Running predictions...")
    predictions = model.predict(X)

    # Create results DataFrame
    results_df = pd.DataFrame({
        'race_id': race_ids if race_ids is not None else range(len(predictions)),
        'horse_name': horse_names if horse_names is not None else ['Horse_' + str(i) for i in range(len(predictions))],
        'actual_rank': actual_ranks if actual_ranks is not None else [0] * len(predictions),
        'ai_prob': predictions
    })

    # Assume odds (if not available, use random odds for simulation)
    # In real scenario, odds should be in the data
    # For now, let's use inverse of AI probability as a proxy
    results_df['odds'] = results_df['ai_prob'].apply(lambda p: max(1.5, min(100, 1.0 / max(p, 0.01))))

    # Calculate EV
    # EV = (AI_Prob × Odds) - 1.0
    results_df['ev'] = (results_df['ai_prob'] * results_df['odds']) - 1.0

    # Is actual top3?
    results_df['is_top3'] = (results_df['actual_rank'] <= 3).astype(int)

    # Backtest per race
    unique_races = results_df['race_id'].unique()

    total_bet = 0
    total_return = 0
    hit_count = 0
    total_races = len(unique_races)
    bet_count = 0

    race_results = []

    print(f"Testing {total_races} races with strategy: {betting_strategy}")

    for race_id in unique_races:
        race_horses = results_df[results_df['race_id'] == race_id].copy()

        # Sort by AI probability
        race_horses = race_horses.sort_values('ai_prob', ascending=False)

        # Decide which horses to bet on
        bet_horses = pd.DataFrame()

        if betting_strategy == 'ev_positive':
            # Bet on all horses with EV > 0
            bet_horses = race_horses[race_horses['ev'] > 0]

        elif betting_strategy == 'top_ev':
            # Bet only on the horse with highest EV
            if len(race_horses) > 0:
                max_ev_idx = race_horses['ev'].idxmax()
                bet_horses = race_horses.loc[[max_ev_idx]]

        elif betting_strategy == 'top3':
            # Bet on top 3 AI predictions
            bet_horses = race_horses.head(3)

        # Calculate returns for this race
        race_bet = 0
        race_return = 0
        race_hits = 0

        for idx, horse in bet_horses.iterrows():
            race_bet += bet_amount
            bet_count += 1

            # If horse finished in top 3, we win (assume fukusho betting)
            # Payout = bet_amount × odds (simplified)
            if horse['is_top3'] == 1:
                race_return += bet_amount * horse['odds']
                race_hits += 1
                hit_count += 1

        total_bet += race_bet
        total_return += race_return

        race_results.append({
            'race_id': race_id,
            'bet_amount': race_bet,
            'return': race_return,
            'profit': race_return - race_bet,
            'hits': race_hits
        })

    # Calculate metrics
    hit_rate = (hit_count / bet_count * 100) if bet_count > 0 else 0
    recovery_rate = (total_return / total_bet * 100) if total_bet > 0 else 0
    roi = ((total_return - total_bet) / total_bet * 100) if total_bet > 0 else 0
    profit = total_return - total_bet

    # Create cumulative profit chart data
    race_results_df = pd.DataFrame(race_results)
    if len(race_results_df) > 0:
        race_results_df['cumulative_profit'] = race_results_df['profit'].cumsum()
    else:
        race_results_df['cumulative_profit'] = []

    print("\n" + "=" * 50)
    print("バックテスト結果")
    print("=" * 50)
    print(f"賭け方: {betting_strategy}")
    print(f"総レース数: {total_races}")
    print(f"総ベット回数: {bet_count}")
    print(f"総賭け金: {total_bet:,}円")
    print(f"総払戻: {total_return:,}円")
    print(f"収支: {profit:+,}円")
    print(f"的中率: {hit_rate:.1f}%")
    print(f"回収率: {recovery_rate:.1f}%")
    print(f"ROI: {roi:+.1f}%")
    print("=" * 50)

    return {
        'strategy': betting_strategy,
        'total_races': total_races,
        'bet_count': bet_count,
        'total_bet': total_bet,
        'total_return': total_return,
        'profit': profit,
        'hit_rate': hit_rate,
        'recovery_rate': recovery_rate,
        'roi': roi,
        'race_results': race_results_df,
        'detailed_results': results_df
    }


def compare_strategies(model_path, data_path, strategies=['ev_positive', 'top_ev', 'top3']):
    """
    複数の賭け方を比較
    """
    print("\n複数の賭け方を比較中...\n")

    comparison = []

    for strategy in strategies:
        result = run_backtest(model_path, data_path, betting_strategy=strategy)
        if result:
            comparison.append({
                '賭け方': strategy,
                '総レース数': result['total_races'],
                'ベット回数': result['bet_count'],
                '総賭け金': result['total_bet'],
                '総払戻': result['total_return'],
                '収支': result['profit'],
                '的中率': f"{result['hit_rate']:.1f}%",
                '回収率': f"{result['recovery_rate']:.1f}%",
                'ROI': f"{result['roi']:.1f}%"
            })

    comparison_df = pd.DataFrame(comparison)
    print("\n" + "=" * 100)
    print("戦略比較")
    print("=" * 100)
    print(comparison_df.to_string(index=False))
    print("=" * 100)

    return comparison_df


if __name__ == "__main__":
    # Test
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "models", "lgbm_model.pkl")
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "processed_data.csv")

    # Run single backtest
    result = run_backtest(model_path, data_path, betting_strategy='ev_positive')

    # Compare strategies
    comparison = compare_strategies(model_path, data_path)
