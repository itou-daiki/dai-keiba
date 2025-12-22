"""
キャリブレーション曲線の可視化

モデルの予測確率が実際の確率とどれだけ一致しているかを評価
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
import os
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def plot_calibration_curve(y_true, y_pred_proba, model_name="Model", n_bins=10, save_path=None):
    """
    キャリブレーション曲線をプロット

    Args:
        y_true: 実際のラベル
        y_pred_proba: 予測確率
        model_name: モデル名
        n_bins: ビン数
        save_path: 保存先パス

    Returns:
        matplotlib figure
    """
    # キャリブレーション曲線の計算
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_true, y_pred_proba, n_bins=n_bins, strategy='uniform'
    )

    # Brier Scoreの計算
    brier_score = brier_score_loss(y_true, y_pred_proba)

    # プロット
    fig, ax = plt.subplots(figsize=(10, 10))

    # キャリブレーション曲線
    ax.plot(mean_predicted_value, fraction_of_positives, marker='o', linewidth=2,
            label=f'{model_name} (Brier: {brier_score:.4f})')

    # 完全にキャリブレーションされたモデル（対角線）
    ax.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfectly Calibrated')

    ax.set_xlabel('Mean Predicted Probability', fontsize=14)
    ax.set_ylabel('Fraction of Positives (True Probability)', fontsize=14)
    ax.set_title(f'Calibration Plot - {model_name}', fontsize=16)
    ax.legend(loc='upper left', fontsize=12)
    ax.grid(True, alpha=0.3)

    # 対角線からの距離を可視化
    ax.fill_between(mean_predicted_value, fraction_of_positives, mean_predicted_value,
                     alpha=0.2, color='red', label='Calibration Error')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Calibration plot saved to {save_path}")

    return fig


def evaluate_model_calibration(model_path, data_path, target_col='target_win', output_dir='ml/visualizations'):
    """
    モデルのキャリブレーションを評価して可視化

    Args:
        model_path: モデルファイルのパス
        data_path: テストデータのパス
        target_col: 目標変数のカラム名
        output_dir: 出力ディレクトリ

    Returns:
        calibration results dict
    """
    logger.info(f"Loading model from {model_path}")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    logger.info(f"Loading data from {data_path}")
    df = pd.read_csv(data_path)

    if target_col not in df.columns:
        logger.error(f"Target column '{target_col}' not found")
        return None

    # 特徴量の準備
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    exclude_cols = ['target_top3', 'target_win', 'target_show']
    drop_cols = [c for c in df.columns if c in meta_cols or c in exclude_cols]

    X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
    y = df[target_col]

    # 予測
    logger.info("Generating predictions...")
    y_pred_proba = model.predict(X)

    # キャリブレーション評価
    logger.info("Evaluating calibration...")
    brier_score = brier_score_loss(y, y_pred_proba)

    # プロット作成
    os.makedirs(output_dir, exist_ok=True)
    model_name = os.path.basename(model_path).replace('.pkl', '')
    save_path = os.path.join(output_dir, f'{model_name}_calibration.png')

    fig = plot_calibration_curve(y, y_pred_proba, model_name=model_name, save_path=save_path)

    # ビン別の詳細統計
    logger.info("\n=== Calibration Details (by bin) ===")
    fraction_of_positives, mean_predicted_value = calibration_curve(y, y_pred_proba, n_bins=10)

    for i, (pred_prob, true_prob) in enumerate(zip(mean_predicted_value, fraction_of_positives)):
        error = abs(true_prob - pred_prob)
        logger.info(f"Bin {i+1}: Predicted={pred_prob:.3f}, Actual={true_prob:.3f}, Error={error:.3f}")

    results = {
        'brier_score': brier_score,
        'calibration_curve': (fraction_of_positives, mean_predicted_value),
        'plot_path': save_path
    }

    logger.info(f"\n=== Overall Calibration ===")
    logger.info(f"Brier Score: {brier_score:.4f} (lower is better, 0=perfect)")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='モデルのキャリブレーション評価')
    parser.add_argument('--model', default='ml/models/lgbm_model.pkl', help='モデルファイルパス')
    parser.add_argument('--data', default='ml/processed_data.csv', help='データファイルパス')
    parser.add_argument('--target', default='target_win', help='目標変数カラム名')
    parser.add_argument('--output', default='ml/visualizations', help='出力ディレクトリ')

    args = parser.parse_args()

    results = evaluate_model_calibration(
        model_path=args.model,
        data_path=args.data,
        target_col=args.target,
        output_dir=args.output
    )

    if results:
        print(f"\n✅ Calibration plot saved to: {results['plot_path']}")
        print(f"📊 Brier Score: {results['brier_score']:.4f}")
