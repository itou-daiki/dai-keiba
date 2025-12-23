import pandas as pd
import lightgbm as lgb
import pickle
import os
import mlflow
import optuna
import numpy as np
import logging
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold, TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, roc_auc_score, precision_score, recall_score,
    f1_score, brier_score_loss, log_loss, confusion_matrix
)
from sklearn.ensemble import VotingClassifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml/training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def train_and_save_model(data_path, model_path, params=None, use_timeseries_split=True,
                         optimize_hyperparams=False, n_trials=50, find_threshold=True,
                         calibrate=False):
    """
    モデルの訓練と保存（TimeSeriesSplit対応版＋最適化機能）

    Args:
        data_path: データファイルのパス
        model_path: モデル保存先パス
        params: LightGBMパラメータ（オプション、optimize_hyperparams=Trueの場合は無視）
        use_timeseries_split: TimeSeriesSplitを使用するか（デフォルトTrue）
        optimize_hyperparams: Optunaで自動最適化するか（デフォルトFalse）
        n_trials: Optuna試行回数（デフォルト50）
        find_threshold: 最適閾値を探索するか（デフォルトTrue）
        calibrate: 確率較正を行うか（デフォルトFalse）

    Returns:
        trained model or None
    """
    if not os.path.exists(data_path):
        logger.error(f"Data file {data_path} not found.")
        return None

    logger.info(f"Loading data from {data_path}")
    df = pd.read_csv(data_path)

    # Check if we have enough data
    if len(df) < 100:
        logger.warning(f"Limited data: {len(df)} samples. Recommended: 500+")
        if len(df) < 10:
            logger.error("Not enough data to train (need > 10 samples).")
            return None

    # === Optunaハイパーパラメータ最適化 ===
    if optimize_hyperparams:
        logger.info("\n" + "="*60)
        logger.info("HYPERPARAMETER OPTIMIZATION MODE")
        logger.info("="*60)
        optimization_result = optimize_hyperparameters(
            data_path,
            n_trials=n_trials,
            use_timeseries_split=use_timeseries_split
        )

        if optimization_result:
            params = optimization_result['best_params']
            logger.info(f"Using optimized parameters (AUC: {optimization_result['best_auc']:.4f})")
        else:
            logger.warning("Optimization failed, using default parameters")
            optimize_hyperparams = False

    # === P0-3: Target変数の統一 ===
    # target_win (1着のみ) を使用してEVと整合させる
    target_col = 'target_win'  # Changed from 'target_top3'

    if target_col not in df.columns:
        logger.error(f"Target column '{target_col}' not found in data.")
        logger.info(f"Available columns: {list(df.columns)}")
        return None

    # === P1-4: データ品質検証パイプライン ===
    logger.info("=== データ品質検証 ===")

    # 1. データ量チェック
    logger.info(f"Total records: {len(df)}")

    # 2. 目標変数の分布チェック
    y = df[target_col]
    win_rate = y.mean()
    logger.info(f"Win rate: {win_rate:.2%} ({y.sum()} wins / {len(y)} races)")

    if win_rate < 0.03 or win_rate > 0.20:
        logger.warning(f"⚠️ Abnormal win rate: {win_rate:.2%} (expected: 5-10%)")

    # 3. 重複チェック
    if 'race_id' in df.columns and '馬 番' in df.columns:
        duplicates = df.duplicated(subset=['race_id', '馬 番'], keep=False)
        if duplicates.sum() > 0:
            logger.warning(f"⚠️ Found {duplicates.sum()} duplicate records (race_id + 馬番)")
            df = df.drop_duplicates(subset=['race_id', '馬 番'], keep='first')
            logger.info(f"After deduplication: {len(df)} records")

    # 4. 欠損値チェック
    missing_cols = df.isnull().sum()
    missing_cols = missing_cols[missing_cols > 0].sort_values(ascending=False)
    if len(missing_cols) > 0:
        logger.warning(f"⚠️ Missing values found in {len(missing_cols)} columns:")
        for col, count in missing_cols.head(10).items():
            logger.warning(f"  - {col}: {count} ({count/len(df)*100:.1f}%)")

    # 5. 特徴量の準備
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    exclude_cols = ['target_top3', 'target_win', 'target_show']

    drop_cols = [c for c in df.columns if c in meta_cols or c in exclude_cols]

    X = df.drop(columns=drop_cols, errors='ignore')

    # Ensure only numeric
    X = X.select_dtypes(include=['number'])

    # 6. 外れ値検出（IQR法）
    logger.info("=== 外れ値検出（サンプル） ===")
    for col in X.columns[:5]:  # 最初の5カラムのみ表示
        Q1 = X[col].quantile(0.25)
        Q3 = X[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers = ((X[col] < Q1 - 1.5*IQR) | (X[col] > Q3 + 1.5*IQR)).sum()
        if outliers > 0:
            logger.info(f"  {col}: {outliers} outliers ({outliers/len(X)*100:.1f}%)")

    feature_names = list(X.columns)
    logger.info(f"Features ({len(feature_names)}): {feature_names[:10]}...")

    # === P0-1: TimeSeriesSplit実装 ===
    if use_timeseries_split:
        logger.info("=== TimeSeriesSplit (5-fold) ===")

        # dateカラムでソート（時系列順）
        if 'date' in df.columns:
            df_sorted = df.sort_values('date').reset_index(drop=True)
            X = df_sorted.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
            y = df_sorted[target_col]
            logger.info("Data sorted by date for time series split")
        else:
            logger.warning("'date' column not found. Using data as-is for TimeSeriesSplit")

        tscv = TimeSeriesSplit(n_splits=5)

        # 交差検証の各折で評価
        cv_scores = {
            'auc': [], 'accuracy': [], 'precision': [], 'recall': [],
            'f1': [], 'brier': [], 'logloss': []
        }

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
            logger.info(f"\n--- Fold {fold}/5 ---")
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            logger.info(f"Train: {len(train_idx)} samples, Test: {len(test_idx)} samples")
            logger.info(f"Train win rate: {y_train.mean():.2%}, Test win rate: {y_test.mean():.2%}")

            # LightGBM Dataset
            train_data = lgb.Dataset(X_train, label=y_train)
            test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

            # LightGBM params
            lgb_params = {
                'objective': 'binary',
                'metric': 'auc',
                'boosting_type': 'gbdt',
                'verbose': -1,
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'is_unbalance': True,  # 1着率5-10%の不均衡対応
            }

            if params:
                lgb_params.update(params)

            # Conflict resolution: scale_pos_weight cannot be used with is_unbalance
            if 'scale_pos_weight' in lgb_params:
                lgb_params['is_unbalance'] = False

            # Train
            bst = lgb.train(
                lgb_params,
                train_data,
                num_boost_round=200,
                valid_sets=[test_data],
                valid_names=['valid'],
                callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
            )

            # Predict
            y_pred = bst.predict(X_test, num_iteration=bst.best_iteration)
            y_pred_binary = (y_pred > 0.5).astype(int)

            # Metrics
            try:
                cv_scores['auc'].append(roc_auc_score(y_test, y_pred))
                cv_scores['accuracy'].append(accuracy_score(y_test, y_pred_binary))
                cv_scores['precision'].append(precision_score(y_test, y_pred_binary, zero_division=0))
                cv_scores['recall'].append(recall_score(y_test, y_pred_binary, zero_division=0))
                cv_scores['f1'].append(f1_score(y_test, y_pred_binary, zero_division=0))
                cv_scores['brier'].append(brier_score_loss(y_test, y_pred))
                cv_scores['logloss'].append(log_loss(y_test, y_pred))

                logger.info(f"  AUC: {cv_scores['auc'][-1]:.4f}, "
                           f"Accuracy: {cv_scores['accuracy'][-1]:.4f}, "
                           f"F1: {cv_scores['f1'][-1]:.4f}")
            except Exception as e:
                logger.error(f"Metric calculation error: {e}")

        # 平均スコアを表示
        logger.info("\n=== Cross-Validation Results (Mean ± Std) ===")
        for metric, scores in cv_scores.items():
            if scores:
                mean_score = np.mean(scores)
                std_score = np.std(scores)
                logger.info(f"{metric.upper()}: {mean_score:.4f} ± {std_score:.4f}")

        # === P0-3改善: 最終モデルを全データで訓練 ===
        logger.info("\n=== Training final model on ALL data ===")
        # CVで評価済みなので、最終モデルは全データを使う
        X_train, y_train = X, y
        # 評価用に最後の20%を別途保持（メタデータ保存用）
        split_idx = int(len(X) * 0.8)
        X_test, y_test = X[split_idx:], y[split_idx:]
    else:
        # 従来のランダム分割（後方互換性のため残す）
        logger.info("=== Random Split (80/20) ===")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # LightGBM Dataset for final training
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    # LightGBM params
    lgb_params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'verbose': -1,
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'is_unbalance': True,
    }

    if params:
        lgb_params.update(params)

    # Conflict resolution: scale_pos_weight cannot be used with is_unbalance
    if 'scale_pos_weight' in lgb_params:
        lgb_params['is_unbalance'] = False

    evals_result = {}

    # Start MLflow Run
    mlflow.set_experiment("keiba_prediction")

    run_name = f"timeseries_split_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if use_timeseries_split else "random_split"

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(lgb_params)
        mlflow.log_param("use_timeseries_split", use_timeseries_split)
        mlflow.log_param("target_variable", target_col)
        mlflow.log_param("total_samples", len(df))
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("test_samples", len(X_test))

        logger.info("Training final LightGBM model...")
        bst = lgb.train(
            lgb_params,
            train_data,
            num_boost_round=300,
            valid_sets=[train_data, test_data],
            valid_names=['train', 'valid'],
            callbacks=[
                lgb.log_evaluation(20),
                lgb.record_evaluation(evals_result),
                lgb.early_stopping(stopping_rounds=30)
            ]
        )

        # Evaluate on test set
        y_pred = bst.predict(X_test, num_iteration=bst.best_iteration)
        y_pred_binary = (y_pred > 0.5).astype(int)

        # Comprehensive metrics
        acc = accuracy_score(y_test, y_pred_binary)
        precision = precision_score(y_test, y_pred_binary, zero_division=0)
        recall = recall_score(y_test, y_pred_binary, zero_division=0)
        f1 = f1_score(y_test, y_pred_binary, zero_division=0)

        try:
            auc = roc_auc_score(y_test, y_pred)
            brier = brier_score_loss(y_test, y_pred)
            logloss = log_loss(y_test, y_pred)
        except Exception as e:
            logger.error(f"Metric calculation error: {e}")
            auc, brier, logloss = 0.0, 1.0, 1.0

        logger.info("\n=== Final Model Performance ===")
        logger.info(f"AUC: {auc:.4f}")
        logger.info(f"Accuracy: {acc:.4f}")
        logger.info(f"Precision: {precision:.4f}")
        logger.info(f"Recall: {recall:.4f}")
        logger.info(f"F1 Score: {f1:.4f}")
        logger.info(f"Brier Score: {brier:.4f}")
        logger.info(f"Log Loss: {logloss:.4f}")

        # Log Metrics to MLflow
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("auc", auc)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1", f1)
        mlflow.log_metric("brier_score", brier)
        mlflow.log_metric("log_loss", logloss)

        if use_timeseries_split and cv_scores:
            for metric, scores in cv_scores.items():
                if scores:
                    mlflow.log_metric(f"cv_mean_{metric}", np.mean(scores))
                    mlflow.log_metric(f"cv_std_{metric}", np.std(scores))

        # === 最適閾値の探索 ===
        optimal_threshold = 0.5  # デフォルト
        if find_threshold:
            logger.info("\n=== Finding Optimal Threshold ===")
            optimal_threshold = find_optimal_threshold(y_test, y_pred, metric='f1')
            mlflow.log_metric("optimal_threshold", optimal_threshold)

        # === 確率較正 ===
        calibrated_model = None
        if calibrate and len(X_test) > 50:  # 較正には十分なデータが必要
            logger.info("\n=== Calibrating Probabilities ===")
            try:
                calibrated_model = calibrate_probabilities(
                    bst, X_test, y_test, method='isotonic'
                )
                # 較正後の性能を評価
                y_pred_cal = calibrated_model.predict_proba(X_test)[:, 1]
                brier_cal = brier_score_loss(y_test, y_pred_cal)
                logger.info(f"Brier Score after calibration: {brier_cal:.4f} (before: {brier:.4f})")
                mlflow.log_metric("brier_score_calibrated", brier_cal)
            except Exception as e:
                logger.warning(f"Calibration failed: {e}")
                calibrated_model = None

        # Save model
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(bst, f)

        logger.info(f"Model saved to {model_path}")

        # Log Model to MLflow
        mlflow.log_artifact(model_path)

        # Feature Importance
        importance = bst.feature_importance(importance_type='gain')
        feature_imp = pd.DataFrame({'Feature': feature_names, 'Value': importance})
        feature_imp_sorted = feature_imp.sort_values(by='Value', ascending=False)

        logger.info("\n=== Top 10 Feature Importance ===")
        for idx, row in feature_imp_sorted.head(10).iterrows():
            logger.info(f"  {row['Feature']}: {row['Value']:.2f}")

        # Update model metadata JSON
        try:
            import json
            meta_path = model_path.replace('.pkl', '_meta.json')

            metadata = {
                "model_id": os.path.basename(model_path).replace('.pkl', ''),
                "model_type": "LightGBM Binary Classification",
                "target": target_col,
                "trained_at": datetime.now().isoformat(),
                "data_source": os.path.basename(data_path),
                "data_stats": {
                    "total_records": len(df),
                    "train_records": len(X_train),
                    "test_records": len(X_test),
                    "win_rate": float(win_rate)
                },
                "performance": {
                    "auc": float(auc),
                    "accuracy": float(acc),
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1": float(f1),
                    "brier_score": float(brier),
                    "log_loss": float(logloss)
                },
                "cv_results": {metric: {"mean": float(np.mean(scores)), "std": float(np.std(scores))}
                              for metric, scores in cv_scores.items() if scores} if use_timeseries_split and cv_scores else {},
                "features": feature_names,
                "hyperparameters": lgb_params,
                "training_config": {
                    "use_timeseries_split": use_timeseries_split,
                    "n_folds": 5 if use_timeseries_split else None,
                    "num_boost_round": 300,
                    "early_stopping_rounds": 30,
                    "hyperparameter_optimization": optimize_hyperparams,
                    "n_trials": n_trials if optimize_hyperparams else None,
                    "optimal_threshold": float(optimal_threshold),
                    "calibrated": calibrate and calibrated_model is not None,
                    "trained_on_all_data": use_timeseries_split  # CVで評価後、全データで学習
                },
                "warnings": []
            }

            # Add warnings
            if len(df) < 1000:
                metadata["warnings"].append(f"⚠️ データ量が少ない（{len(df)}件）- 推奨は5000件以上")
            if len(df) < 5000 and not optimize_hyperparams:
                metadata["warnings"].append("💡 ハイパーパラメータ最適化を推奨（optimize_hyperparams=True）")
            if not use_timeseries_split:
                metadata["warnings"].append("⚠️ TimeSeriesSplitを使用していません（Look-ahead biasの可能性）")
            if target_col != 'target_win':
                metadata["warnings"].append("⚠️ target_winではなく他の目標変数を使用しています")
            if not calibrate and brier > 0.15:
                metadata["warnings"].append("💡 Brier Scoreが高い - 確率較正を推奨（calibrate=True）")
            if optimize_hyperparams:
                metadata["warnings"].append(f"✅ Optunaで最適化済み（{n_trials}試行、AUC改善の可能性）")

            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Metadata saved to {meta_path}")
            mlflow.log_artifact(meta_path)

        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

        return {
            'model': bst,
            'accuracy': acc,
            'auc': auc,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'brier_score': brier,
            'log_loss': logloss,
            'feature_importance': feature_imp_sorted.head(20).to_dict('records'),
            'evals_result': evals_result,
            'features': feature_names,
            'win_rate': win_rate,
            'cv_scores': cv_scores if use_timeseries_split else None
        }

def optimize_hyperparameters(data_path, n_trials=50, use_timeseries_split=True):
    """
    Optunaによるハイパーパラメータ最適化（TimeSeriesSplit対応）

    Args:
        data_path: データファイルパス
        n_trials: 試行回数（デフォルト50回）
        use_timeseries_split: TimeSeriesSplitを使用するか

    Returns:
        dict: 最適パラメータと結果
    """
    if not os.path.exists(data_path):
        logger.error(f"Data file {data_path} not found.")
        return None

    logger.info(f"=== Optuna Hyperparameter Optimization (n_trials={n_trials}) ===")
    df = pd.read_csv(data_path)

    if len(df) < 100:
        logger.warning("Not enough data for optimization (need 100+)")
        return None

    # === Target変数の統一 ===
    target_col = 'target_win'  # Changed from 'target_top3'

    if target_col not in df.columns:
        logger.error(f"Target column '{target_col}' not found.")
        return None

    # データ準備
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    exclude_cols = ['target_top3', 'target_win', 'target_show']
    drop_cols = [c for c in df.columns if c in meta_cols or c in exclude_cols]

    X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
    y = df[target_col]

    # TimeSeriesSplit用にソート
    if use_timeseries_split and 'date' in df.columns:
        df_sorted = df.sort_values('date').reset_index(drop=True)
        X = df_sorted.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
        y = df_sorted[target_col]
        logger.info("Data sorted by date for TimeSeriesSplit")

    # クラス不均衡の確認
    win_rate = y.mean()
    scale_pos_weight = (1 - win_rate) / win_rate if win_rate > 0 else 1.0
    logger.info(f"Win rate: {win_rate:.2%}, scale_pos_weight: {scale_pos_weight:.2f}")

    def objective(trial):
        """Optuna目的関数"""
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'verbose': -1,
            'is_unbalance': False,  # scale_pos_weightと併用しない

            # === 最適化するパラメータ ===
            'num_leaves': trial.suggest_int('num_leaves', 20, 150),
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.2, log=True),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
            'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
            'bagging_freq': trial.suggest_int('bagging_freq', 1, 10),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
            'min_gain_to_split': trial.suggest_float('min_gain_to_split', 0.0, 1.0),

            # === 正則化パラメータ ===
            'lambda_l1': trial.suggest_float('lambda_l1', 1e-8, 10.0, log=True),
            'lambda_l2': trial.suggest_float('lambda_l2', 1e-8, 10.0, log=True),

            # === クラス不均衡対応 ===
            'scale_pos_weight': trial.suggest_float('scale_pos_weight',
                                                    max(1.0, scale_pos_weight * 0.5),
                                                    scale_pos_weight * 2.0),
        }

        # TimeSeriesSplit or Random Splitでクロスバリデーション
        cv_aucs = []

        if use_timeseries_split:
            tscv = TimeSeriesSplit(n_splits=3)  # 高速化のため3分割
            splits = tscv.split(X)
        else:
            from sklearn.model_selection import StratifiedKFold
            skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
            splits = skf.split(X, y)

        for train_idx, val_idx in splits:
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

            bst = lgb.train(
                params,
                train_data,
                num_boost_round=200,
                valid_sets=[val_data],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=20, verbose=False),
                    lgb.log_evaluation(0)
                ]
            )

            preds = bst.predict(X_val, num_iteration=bst.best_iteration)
            auc = roc_auc_score(y_val, preds)
            cv_aucs.append(auc)

        mean_auc = np.mean(cv_aucs)
        return mean_auc

    # Optuna最適化実行
    logger.info("Starting Optuna optimization...")
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5)
    )

    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    best_value = study.best_value

    logger.info(f"\n=== Optimization Complete ===")
    logger.info(f"Best AUC: {best_value:.4f}")
    logger.info(f"Best Parameters:")
    for key, value in best_params.items():
        logger.info(f"  {key}: {value}")

    return {
        'best_params': best_params,
        'best_auc': best_value,
        'trials': len(study.trials),
        'study': study
    }

def find_optimal_threshold(y_true, y_pred_proba, metric='f1'):
    """
    最適な予測閾値を探索

    Args:
        y_true: 正解ラベル
        y_pred_proba: 予測確率
        metric: 最適化する指標 ('f1', 'precision', 'recall', 'balanced')

    Returns:
        float: 最適閾値
    """
    thresholds = np.arange(0.05, 0.95, 0.05)
    best_score = 0
    best_threshold = 0.5

    for threshold in thresholds:
        y_pred_binary = (y_pred_proba >= threshold).astype(int)

        if metric == 'f1':
            score = f1_score(y_true, y_pred_binary, zero_division=0)
        elif metric == 'precision':
            score = precision_score(y_true, y_pred_binary, zero_division=0)
        elif metric == 'recall':
            score = recall_score(y_true, y_pred_binary, zero_division=0)
        elif metric == 'balanced':
            # Precision-Recallバランス
            prec = precision_score(y_true, y_pred_binary, zero_division=0)
            rec = recall_score(y_true, y_pred_binary, zero_division=0)
            score = 2 * (prec * rec) / (prec + rec + 1e-8)  # F1と同じ
        else:
            score = f1_score(y_true, y_pred_binary, zero_division=0)

        if score > best_score:
            best_score = score
            best_threshold = threshold

    logger.info(f"Optimal threshold: {best_threshold:.2f} ({metric}={best_score:.4f})")
    return best_threshold


def calibrate_probabilities(model, X_cal, y_cal, method='isotonic'):
    """
    確率較正（Probability Calibration）

    Args:
        model: 学習済みモデル
        X_cal: 較正用データ
        y_cal: 較正用ラベル
        method: 較正手法 ('isotonic' or 'sigmoid')

    Returns:
        CalibratedClassifierCV: 較正済みモデル
    """
    from sklearn.calibration import CalibratedClassifierCV

    logger.info(f"Calibrating probabilities with {method} method...")

    # LightGBMモデルをラップ
    class LGBMWrapper:
        def __init__(self, model):
            self.model = model

        def predict_proba(self, X):
            preds = self.model.predict(X)
            # LightGBMは確率を直接返すので、2列に変換
            return np.column_stack([1 - preds, preds])

        def fit(self, X, y):
            # 既に訓練済みなので何もしない
            return self

    wrapped_model = LGBMWrapper(model)

    # 較正
    calibrated = CalibratedClassifierCV(
        wrapped_model,
        method=method,
        cv='prefit'  # 既に訓練済み
    )

    calibrated.fit(X_cal, y_cal)

    logger.info("Calibration complete")
    return calibrated


def train_with_cross_validation(data_path, params=None, n_splits=5):
    """
    K分割クロスバリデーションでモデルを学習・評価
    """
    if not os.path.exists(data_path):
        print(f"Data file {data_path} not found.")
        return None

    df = pd.read_csv(data_path)

    if len(df) < 10:
        print("Not enough data to train.")
        return None

    # Prepare data
    target_col = 'target_top3'
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    drop_cols = [c for c in df.columns if c in meta_cols or c == target_col]

    X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
    y = df[target_col]

    feature_names = list(X.columns)

    # Default params
    lgb_params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'verbose': -1,
        'feature_pre_filter': False,
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
    }

    if params:
        lgb_params.update(params)

    # K-Fold Cross Validation
    kfold = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    cv_scores = []
    cv_accuracies = []

    print(f"Starting {n_splits}-Fold Cross Validation...")

    mlflow.set_experiment("keiba_cross_validation")

    with mlflow.start_run(run_name=f"{n_splits}_fold_cv"):
        mlflow.log_params(lgb_params)

        for fold, (train_idx, val_idx) in enumerate(kfold.split(X, y), 1):
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y.iloc[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_val_fold = y.iloc[val_idx]

            train_data = lgb.Dataset(X_train_fold, label=y_train_fold)
            val_data = lgb.Dataset(X_val_fold, label=y_val_fold, reference=train_data)

            bst = lgb.train(
                lgb_params,
                train_data,
                num_boost_round=100,
                valid_sets=[val_data],
                callbacks=[lgb.log_evaluation(False)]
            )

            # Evaluate
            y_pred = bst.predict(X_val_fold)
            y_pred_binary = [1 if p > 0.5 else 0 for p in y_pred]

            acc = accuracy_score(y_val_fold, y_pred_binary)
            auc = roc_auc_score(y_val_fold, y_pred)

            cv_scores.append(auc)
            cv_accuracies.append(acc)

            print(f"  Fold {fold}: AUC={auc:.4f}, Accuracy={acc:.4f}")

            mlflow.log_metric(f"fold_{fold}_auc", auc)
            mlflow.log_metric(f"fold_{fold}_accuracy", acc)

        mean_auc = np.mean(cv_scores)
        std_auc = np.std(cv_scores)
        mean_acc = np.mean(cv_accuracies)
        std_acc = np.std(cv_accuracies)

        print(f"\nCross Validation Results:")
        print(f"  Mean AUC: {mean_auc:.4f} ± {std_auc:.4f}")
        print(f"  Mean Accuracy: {mean_acc:.4f} ± {std_acc:.4f}")

        mlflow.log_metric("mean_auc", mean_auc)
        mlflow.log_metric("std_auc", std_auc)
        mlflow.log_metric("mean_accuracy", mean_acc)
        mlflow.log_metric("std_accuracy", std_acc)

        return {
            'mean_auc': mean_auc,
            'std_auc': std_auc,
            'mean_accuracy': mean_acc,
            'std_accuracy': std_acc,
            'cv_scores': cv_scores,
            'cv_accuracies': cv_accuracies
        }

def train_with_timeseries_split(data_path, model_path, params=None, n_splits=5):
    """
    時系列分割でモデルを学習（過去データで学習→未来データで検証）
    """
    if not os.path.exists(data_path):
        print(f"Data file {data_path} not found.")
        return None

    df = pd.read_csv(data_path)

    if len(df) < 10:
        print("Not enough data to train.")
        return None

    # Sort by date
    if 'date' in df.columns:
        df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.sort_values('date_dt')

    # Prepare data
    target_col = 'target_top3'
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順', 'date_dt']
    drop_cols = [c for c in df.columns if c in meta_cols or c == target_col]

    X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
    y = df[target_col]

    feature_names = list(X.columns)

    # Default params
    lgb_params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'verbose': -1,
        'feature_pre_filter': False,
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
    }

    if params:
        lgb_params.update(params)

    # Time Series Split
    tscv = TimeSeriesSplit(n_splits=n_splits)

    cv_scores = []
    cv_accuracies = []

    print(f"Starting Time Series {n_splits}-Split Cross Validation...")

    mlflow.set_experiment("keiba_timeseries_cv")

    with mlflow.start_run(run_name=f"timeseries_{n_splits}_split"):
        mlflow.log_params(lgb_params)

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y.iloc[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_val_fold = y.iloc[val_idx]

            train_data = lgb.Dataset(X_train_fold, label=y_train_fold)
            val_data = lgb.Dataset(X_val_fold, label=y_val_fold, reference=train_data)

            bst = lgb.train(
                lgb_params,
                train_data,
                num_boost_round=100,
                valid_sets=[val_data],
                callbacks=[lgb.log_evaluation(False)]
            )

            # Evaluate
            y_pred = bst.predict(X_val_fold)
            y_pred_binary = [1 if p > 0.5 else 0 for p in y_pred]

            acc = accuracy_score(y_val_fold, y_pred_binary)
            auc = roc_auc_score(y_val_fold, y_pred)

            cv_scores.append(auc)
            cv_accuracies.append(acc)

            print(f"  Split {fold}: AUC={auc:.4f}, Accuracy={acc:.4f}")

            mlflow.log_metric(f"split_{fold}_auc", auc)
            mlflow.log_metric(f"split_{fold}_accuracy", acc)

        mean_auc = np.mean(cv_scores)
        std_auc = np.std(cv_scores)
        mean_acc = np.mean(cv_accuracies)
        std_acc = np.std(cv_accuracies)

        print(f"\nTime Series CV Results:")
        print(f"  Mean AUC: {mean_auc:.4f} ± {std_auc:.4f}")
        print(f"  Mean Accuracy: {mean_acc:.4f} ± {std_acc:.4f}")

        mlflow.log_metric("mean_auc", mean_auc)
        mlflow.log_metric("std_auc", std_auc)
        mlflow.log_metric("mean_accuracy", mean_acc)
        mlflow.log_metric("std_accuracy", std_acc)

        # Train final model on all data
        print("\nTraining final model on all data...")
        train_data = lgb.Dataset(X, label=y)
        final_model = lgb.train(
            lgb_params,
            train_data,
            num_boost_round=100
        )

        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump(final_model, f)
        print(f"Model saved to {model_path}")

        mlflow.log_artifact(model_path)

        return {
            'mean_auc': mean_auc,
            'std_auc': std_auc,
            'mean_accuracy': mean_acc,
            'std_accuracy': std_acc,
            'cv_scores': cv_scores,
            'cv_accuracies': cv_accuracies
        }

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    ml_dir = os.path.join(base_dir, "ml")
    model_dir = os.path.join(ml_dir, "models")
    os.makedirs(model_dir, exist_ok=True)

    # 1. Train JRA
    data_path = os.path.join(ml_dir, "processed_data.csv")
    model_path = os.path.join(model_dir, "lgbm_model.pkl")
    print(f"Training JRA Model from {data_path}...")
    train_and_save_model(data_path, model_path)

    # 2. Train NAR
    data_path_nar = os.path.join(ml_dir, "processed_data_nar.csv")
    model_path_nar = os.path.join(model_dir, "lgbm_model_nar.pkl")
    if os.path.exists(data_path_nar):
        print(f"\nTraining NAR Model from {data_path_nar}...")
        train_and_save_model(data_path_nar, model_path_nar)
    else:
        print(f"NAR Data {data_path_nar} not found. Skipping.")
