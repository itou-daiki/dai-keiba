import pandas as pd
import lightgbm as lgb
import pickle
import os
import mlflow
import optuna
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.ensemble import VotingClassifier

def train_and_save_model(data_path, model_path, params=None):
    if not os.path.exists(data_path):
        print(f"Data file {data_path} not found.")
        return None

    df = pd.read_csv(data_path)
    
    # Check if we have enough data
    if len(df) < 10:
        print("Not enough data to train (need > 10 samples).")
        return None

    # Define Target and Features
    target_col = 'target_top3'
    
    # Identify feature columns (numeric)
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
    
    # Drop valid string columns
    drop_cols = [c for c in df.columns if c in meta_cols or c == target_col]
    
    X = df.drop(columns=drop_cols, errors='ignore')
    
    # Ensure only numeric
    X = X.select_dtypes(include=['number'])
    
    y = df[target_col]
    
    feature_names = list(X.columns)
    positive_rate = y.mean()
    print(f"Features: {feature_names}")
    print(f"Target: {target_col} (Positive Rate: {positive_rate:.2%})")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # LightGBM Dataset
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    # Default Params
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
    
    evals_result = {}
    
    # Start MLflow Run
    # Set experiment name
    mlflow.set_experiment("keiba_prediction")
    
    with mlflow.start_run(run_name="manual_train_run"):
        mlflow.log_params(lgb_params)
        
        print("Training LightGBM model...")
        bst = lgb.train(
            lgb_params,
            train_data,
            num_boost_round=100,
            valid_sets=[train_data, test_data],
            valid_names=['train', 'valid'],
            callbacks=[
                lgb.log_evaluation(10),
                lgb.record_evaluation(evals_result)
            ]
        )
        
        # Evaluate
        y_pred = bst.predict(X_test, num_iteration=bst.best_iteration)
        y_pred_binary = [1 if p > 0.5 else 0 for p in y_pred]
        acc = accuracy_score(y_test, y_pred_binary)
        try:
            auc = roc_auc_score(y_test, y_pred)
        except:
            auc = 0.0
            
        print(f"Model Accuracy: {acc:.4f}")
        print(f"Model AUC: {auc:.4f}")
        
        # Log Metrics
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("auc", auc)
        
        # Save
        with open(model_path, 'wb') as f:
            pickle.dump(bst, f)
            
        print(f"Model saved to {model_path}")
        
        # Log Model (optional, saving local pickle is enough for app usage)
        mlflow.log_artifact(model_path)
        
        # Feature Importance
        importance = bst.feature_importance(importance_type='gain')
        feature_imp = pd.DataFrame({'Feature': feature_names, 'Value': importance})
        feature_imp = feature_imp.sort_values(by='Value', ascending=False).head(20).to_dict('records')
        
        return {
            'accuracy': acc,
            'auc': auc,
            'feature_importance': feature_imp,
            'evals_result': evals_result,
            'features': feature_names,
            'positive_rate': positive_rate
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
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "processed_data.csv")
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "lgbm_model.pkl")

    train_and_save_model(data_path, model_path)
