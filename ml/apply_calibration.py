"""
Apply probability calibration to existing trained models
This script calibrates existing models without retraining
"""
import os
import pickle
import json
import pandas as pd
import numpy as np
import logging
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calibrate_probabilities(model, X_cal, y_cal, method='isotonic'):
    """
    確率較正（Probability Calibration）

    Args:
        model: LightGBM model
        X_cal: 較正用データ（特徴量）
        y_cal: 較正用データ（ラベル）
        method: 較正手法（'isotonic' or 'sigmoid'）

    Returns:
        CalibratedClassifierCV: 較正済みモデル
    """
    from sklearn.calibration import CalibratedClassifierCV

    # LightGBM wrapper for sklearn compatibility
    class LGBMWrapper:
        def __init__(self, model):
            self.model = model

        def predict_proba(self, X):
            preds = self.model.predict(X)
            # Return 2D array for binary classification
            return np.column_stack([1 - preds, preds])

        def fit(self, X, y):
            # No-op (already trained)
            return self

    wrapped_model = LGBMWrapper(model)
    calibrated = CalibratedClassifierCV(
        wrapped_model,
        method=method,
        cv='prefit'  # Model already trained
    )

    calibrated.fit(X_cal, y_cal)

    logger.info("Calibration complete")
    return calibrated


def apply_calibration_to_model(model_path, data_path, output_path=None, cal_fraction=0.2):
    """
    Apply calibration to an existing model

    Args:
        model_path: Path to existing model file
        data_path: Path to training data (for calibration)
        output_path: Path to save calibrated model (default: model_path with _calibrated suffix)
        cal_fraction: Fraction of data to use for calibration
    """
    logger.info("=" * 80)
    logger.info(f"Applying Calibration to {model_path}")
    logger.info("=" * 80)

    # Load existing model
    logger.info(f"Loading model from {model_path}")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # Load metadata
    meta_path = model_path.replace('.pkl', '_meta.json')
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}

    # Load training data
    logger.info(f"Loading data from {data_path}")
    if data_path.endswith('.parquet'):
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    # Prepare features
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    exclude_cols = ['target_top3', 'target_win', 'target_show']
    drop_cols = [c for c in df.columns if c in meta_cols or c in exclude_cols]

    X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
    y = df['target_win']

    # Get model features
    if hasattr(model, 'feature_name'):
        model_features = model.feature_name()
        # Ensure all features exist
        for f in model_features:
            if f not in X.columns:
                logger.warning(f"Missing feature: {f}, defaulting to 0")
                X[f] = 0
        X = X[model_features]

    logger.info(f"Total samples: {len(X)}")

    # Split calibration set (use most recent data for calibration)
    cal_size = int(len(X) * cal_fraction)
    logger.info(f"Using {cal_size} samples ({cal_fraction*100:.0f}%) for calibration")

    X_cal = X.iloc[-cal_size:]
    y_cal = y.iloc[-cal_size:]

    # Evaluate before calibration
    logger.info("\n=== Before Calibration ===")
    y_pred_before = model.predict(X_cal)
    brier_before = brier_score_loss(y_cal, y_pred_before)
    logloss_before = log_loss(y_cal, y_pred_before)
    logger.info(f"Brier Score: {brier_before:.6f}")
    logger.info(f"Log Loss: {logloss_before:.6f}")

    # Apply calibration
    logger.info("\n=== Applying Isotonic Calibration ===")
    calibrated_model = calibrate_probabilities(model, X_cal, y_cal, method='isotonic')

    # Evaluate after calibration
    logger.info("\n=== After Calibration ===")
    y_pred_after = calibrated_model.predict_proba(X_cal)[:, 1]
    brier_after = brier_score_loss(y_cal, y_pred_after)
    logloss_after = log_loss(y_cal, y_pred_after)
    logger.info(f"Brier Score: {brier_after:.6f}")
    logger.info(f"Log Loss: {logloss_after:.6f}")

    # Calculate improvement
    logger.info("\n=== Improvement ===")
    brier_improvement = ((brier_before - brier_after) / brier_before) * 100
    logloss_improvement = ((logloss_before - logloss_after) / logloss_before) * 100
    logger.info(f"Brier Score: {brier_improvement:+.2f}%")
    logger.info(f"Log Loss: {logloss_improvement:+.2f}%")

    # Save calibrated model
    if output_path is None:
        output_path = model_path.replace('.pkl', '_calibrated.pkl')

    logger.info(f"\n=== Saving Calibrated Model ===")
    logger.info(f"Output path: {output_path}")

    with open(output_path, 'wb') as f:
        pickle.dump(calibrated_model, f)

    # Update metadata
    if metadata:
        metadata['calibrated'] = True
        metadata['calibration_method'] = 'isotonic'
        metadata['calibration_samples'] = cal_size
        metadata['performance_before_calibration'] = {
            'brier_score': float(brier_before),
            'log_loss': float(logloss_before)
        }
        metadata['performance_after_calibration'] = {
            'brier_score': float(brier_after),
            'log_loss': float(logloss_after)
        }
        metadata['improvement'] = {
            'brier_score_pct': float(brier_improvement),
            'log_loss_pct': float(logloss_improvement)
        }

        meta_output_path = output_path.replace('.pkl', '_meta.json')
        with open(meta_output_path, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Metadata saved to {meta_output_path}")

    logger.info("✅ Calibration complete!")

    return {
        'brier_before': brier_before,
        'brier_after': brier_after,
        'logloss_before': logloss_before,
        'logloss_after': logloss_after,
        'brier_improvement_pct': brier_improvement,
        'logloss_improvement_pct': logloss_improvement
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Apply calibration to existing models')
    parser.add_argument('--jra-only', action='store_true', help='Calibrate JRA model only')
    parser.add_argument('--nar-only', action='store_true', help='Calibrate NAR model only')
    parser.add_argument('--cal-fraction', type=float, default=0.2, help='Fraction of data for calibration')

    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(__file__))
    ml_dir = os.path.join(base_dir, "ml")
    model_dir = os.path.join(ml_dir, "models")

    results = {}

    # Calibrate JRA model
    if not args.nar_only:
        jra_model_path = os.path.join(model_dir, "lgbm_model.pkl")
        jra_data_path = os.path.join(ml_dir, "processed_data.parquet")

        if os.path.exists(jra_model_path) and os.path.exists(jra_data_path):
            results['JRA'] = apply_calibration_to_model(
                jra_model_path,
                jra_data_path,
                cal_fraction=args.cal_fraction
            )
        else:
            logger.warning(f"JRA model or data not found")

    # Calibrate NAR model
    if not args.jra_only:
        nar_model_path = os.path.join(model_dir, "lgbm_model_nar.pkl")
        nar_data_path = os.path.join(ml_dir, "processed_data_nar.parquet")

        if os.path.exists(nar_model_path) and os.path.exists(nar_data_path):
            results['NAR'] = apply_calibration_to_model(
                nar_model_path,
                nar_data_path,
                cal_fraction=args.cal_fraction
            )
        else:
            logger.warning(f"NAR model or data not found")

    # Summary
    print("\n" + "=" * 80)
    print("CALIBRATION SUMMARY")
    print("=" * 80)

    for model_name, res in results.items():
        print(f"\n{model_name} Model:")
        print(f"  Brier Score: {res['brier_before']:.6f} → {res['brier_after']:.6f} ({res['brier_improvement_pct']:+.2f}%)")
        print(f"  Log Loss: {res['logloss_before']:.6f} → {res['logloss_after']:.6f} ({res['logloss_improvement_pct']:+.2f}%)")

    print("\n✅ All calibrations complete!")
    print("\nNOTE: Calibrated models saved as *_calibrated.pkl")
    print("To use calibrated models, update references in app/public_app.py")
