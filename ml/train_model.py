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

def train_and_save_model(data_path, model_path, params=None, use_timeseries_split=True):
    """
    モデルの訓練と保存（TimeSeriesSplit対応版）

    Args:
        data_path: データファイルのパス
        model_path: モデル保存先パス
        params: LightGBMパラメータ（オプション）
        use_timeseries_split: TimeSeriesSplitを使用するか（デフォルトTrue）

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

        # 最終モデルを全データで訓練
        logger.info("\n=== Training final model on all data ===")
        X_train, X_test, y_train, y_test = X, X[-len(X)//5:], y, y[-len(y)//5:]  # 最後の20%をテスト
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
                    "early_stopping_rounds": 30
                },
                "warnings": []
            }

            # Add warnings
            if len(df) < 1000:
                metadata["warnings"].append(f"⚠️ データ量が少ない（{len(df)}件）- 推奨は5000件以上")
            if not use_timeseries_split:
                metadata["warnings"].append("⚠️ TimeSeriesSplitを使用していません（Look-ahead biasの可能性）")
            if target_col != 'target_win':
                metadata["warnings"].append("⚠️ target_winではなく他の目標変数を使用しています")

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

def optimize_hyperparameters(data_path, n_trials=10):
    if not os.path.exists(data_path):
        return None

    df = pd.read_csv(data_path)
    if len(df) < 10:
        return None

    target_col = 'target_top3'
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    drop_cols = [c for c in df.columns if c in meta_cols or c == target_col]
    X = df.drop(columns=drop_cols, errors='ignore').select_dtypes(include=['number'])
    y = df[target_col]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    def objective(trial):
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'verbose': -1,
            'feature_pre_filter': False,
            'num_leaves': trial.suggest_int('num_leaves', 20, 100),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
            'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
            'bagging_freq': trial.suggest_int('bagging_freq', 1, 7),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
        }
        
        # We can also use MLflow nested runs for each trial
        with mlflow.start_run(nested=True):
            bst = lgb.train(params, train_data, valid_sets=[test_data], callbacks=[lgb.log_evaluation(False)])
            preds = bst.predict(X_test)
            auc = roc_auc_score(y_test, preds)
            mlflow.log_params(params)
            mlflow.log_metric("auc", auc)
            
        return auc

    mlflow.set_experiment("keiba_optimization")
    with mlflow.start_run(run_name="optuna_optimization"):
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        
        best_params = study.best_params
        best_value = study.best_value
        
        mlflow.log_params(best_params)
        mlflow.log_metric("best_auc", best_value)
        
        return {
            'best_params': best_params,
            'best_auc': best_value,
            'trials': len(study.trials)
        }

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
