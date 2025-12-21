#!/usr/bin/env python3
"""
本番運用版のモデル学習スクリプト

改善点:
1. TimeSeriesSplitによる時系列分割（ルックアヘッドバイアス解消）
2. ターゲット変数を1着のみに変更（target_win）
3. Brier Scoreによるキャリブレーション評価
4. 詳細なログ出力
5. データ検証パイプライン

使用方法:
    python ml/train_model_production.py
"""

import pandas as pd
import lightgbm as lgb
import pickle
import os
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    brier_score_loss,
    log_loss,
    precision_score,
    recall_score,
    f1_score
)
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


def validate_data(df):
    """
    データの品質を検証

    Args:
        df: DataFrame

    Returns:
        bool: 検証結果
    """
    print("\n" + "=" * 60)
    print("データ品質検証")
    print("=" * 60)

    issues = []

    # 1. データ量チェック
    if len(df) < 500:
        issues.append(f"⚠️ データ量不足: {len(df)}行（推奨: 500行以上）")
    else:
        print(f"✅ データ量: {len(df):,}行")

    # 2. ターゲット変数チェック
    if 'target_win' in df.columns:
        win_rate = df['target_win'].mean()
        print(f"✅ 1着率: {win_rate:.2%}")

        if win_rate < 0.03 or win_rate > 0.20:
            issues.append(f"⚠️ 1着率が異常: {win_rate:.2%}（通常: 5-10%）")
    else:
        issues.append("❌ target_win列が見つかりません")

    # 3. 欠損値チェック
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0]

    if len(missing_cols) > 0:
        print(f"\n⚠️ 欠損値が存在する列: {len(missing_cols)}個")
        for col, count in missing_cols.head(5).items():
            print(f"  - {col}: {count}件 ({count/len(df):.1%})")
    else:
        print("✅ 欠損値なし")

    # 4. 日付の存在チェック（時系列分割用）
    if 'date' not in df.columns:
        issues.append("❌ date列が見つかりません（時系列分割に必須）")
    else:
        print("✅ date列あり")

    # 結果サマリー
    print("\n" + "-" * 60)
    if len(issues) == 0:
        print("✅ すべての検証に合格")
        return True
    else:
        print(f"⚠️ {len(issues)}個の問題が見つかりました:")
        for issue in issues:
            print(f"  {issue}")
        return False


def train_with_timeseries_split(data_path, model_path, params=None, n_splits=5):
    """
    TimeSeriesSplitによる時系列分割学習

    Args:
        data_path (str): 処理済みデータのパス
        model_path (str): モデル保存先
        params (dict): LightGBMパラメータ
        n_splits (int): 分割数

    Returns:
        model: 学習済みモデル
    """
    print("\n" + "=" * 60)
    print("本番運用版モデル学習")
    print("=" * 60)

    # 1. データ読み込み
    if not os.path.exists(data_path):
        print(f"❌ データファイルが見つかりません: {data_path}")
        return None

    df = pd.read_csv(data_path)
    print(f"\n📊 データ読み込み: {len(df):,}行")

    # 2. データ検証
    if not validate_data(df):
        print("\n⚠️ データ品質に問題があります。学習を続行しますか？")
        print("   続行する場合はEnterを押してください...")
        # input()  # 本番では有効化

    # 3. 特徴量とターゲットの準備
    target_col = 'target_win'  # 1着のみ

    if target_col not in df.columns:
        print(f"❌ ターゲット列が見つかりません: {target_col}")
        print("   target_top3を使用します（非推奨）")
        target_col = 'target_top3'

    # メタカラムを除外
    meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順',
                 'target_win', 'target_top3', 'run_style']

    # 特徴量を選択（数値型のみ）
    feature_cols = [c for c in df.columns if c not in meta_cols]
    X = df[feature_cols].select_dtypes(include=['number'])
    y = df[target_col]

    print(f"\n📈 特徴量数: {len(X.columns)}")
    print(f"   ターゲット: {target_col}")
    print(f"   正例率: {y.mean():.2%}")

    # 4. 日付でソート（時系列分割のため）
    if 'date' in df.columns:
        df_sorted = df.sort_values('date').reset_index(drop=True)
        X = df_sorted[feature_cols].select_dtypes(include=['number'])
        y = df_sorted[target_col]
        print("✅ 日付順にソート済み")
    else:
        print("⚠️ date列がないため、現在の順序で分割します")

    # 5. TimeSeriesSplitで学習
    tscv = TimeSeriesSplit(n_splits=n_splits)

    print(f"\n🔄 TimeSeriesSplit ({n_splits}分割) で学習...")
    print("   ルックアヘッドバイアスを防ぐため、時系列順に分割\n")

    # デフォルトパラメータ
    lgb_params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'random_state': 42,
        'is_unbalance': True,  # 不均衡データ対応
    }

    if params:
        lgb_params.update(params)

    # 評価指標を格納
    metrics = {
        'auc': [],
        'brier': [],
        'logloss': [],
        'accuracy': [],
        'precision': [],
        'recall': [],
        'f1': []
    }

    fold = 1
    best_model = None
    best_auc = 0

    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        print(f"\n【Fold {fold}/{n_splits}】")
        print(f"  学習データ: {len(X_train):,}行 ({train_idx[0]} - {train_idx[-1]})")
        print(f"  テストデータ: {len(X_test):,}行 ({test_idx[0]} - {test_idx[-1]})")
        print(f"  学習期間 1着率: {y_train.mean():.2%}")
        print(f"  テスト期間 1着率: {y_test.mean():.2%}")

        # LightGBM学習
        train_data = lgb.Dataset(X_train, label=y_train)
        test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        model = lgb.train(
            lgb_params,
            train_data,
            num_boost_round=200,
            valid_sets=[test_data],
            valid_names=['valid'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=20, verbose=False),
                lgb.log_evaluation(period=50)
            ]
        )

        # 予測
        y_pred_proba = model.predict(X_test)
        y_pred = (y_pred_proba > 0.5).astype(int)

        # 評価
        auc = roc_auc_score(y_test, y_pred_proba)
        brier = brier_score_loss(y_test, y_pred_proba)
        logloss = log_loss(y_test, y_pred_proba)
        accuracy = accuracy_score(y_test, y_pred)

        # Precision, Recall, F1（ゼロ除算対策）
        try:
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
        except:
            precision = recall = f1 = 0.0

        metrics['auc'].append(auc)
        metrics['brier'].append(brier)
        metrics['logloss'].append(logloss)
        metrics['accuracy'].append(accuracy)
        metrics['precision'].append(precision)
        metrics['recall'].append(recall)
        metrics['f1'].append(f1)

        print(f"  📊 AUC: {auc:.4f}")
        print(f"  📊 Brier Score: {brier:.4f}")
        print(f"  📊 Log Loss: {logloss:.4f}")
        print(f"  📊 Accuracy: {accuracy:.4f}")
        print(f"  📊 Precision: {precision:.4f}")
        print(f"  📊 Recall: {recall:.4f}")
        print(f"  📊 F1: {f1:.4f}")

        # 最良モデルを保存
        if auc > best_auc:
            best_auc = auc
            best_model = model

        fold += 1

    # 6. 評価結果のサマリー
    print("\n" + "=" * 60)
    print("学習結果サマリー")
    print("=" * 60)

    for metric_name, values in metrics.items():
        mean_val = np.mean(values)
        std_val = np.std(values)
        print(f"{metric_name.upper():12s}: {mean_val:.4f} ± {std_val:.4f}")

    # 7. 最終モデルで全データを学習
    print("\n🔄 最終モデルを全データで学習...")

    train_data = lgb.Dataset(X, label=y)
    final_model = lgb.train(
        lgb_params,
        train_data,
        num_boost_round=200,
        callbacks=[lgb.log_evaluation(period=50)]
    )

    # 8. モデル保存
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    with open(model_path, 'wb') as f:
        pickle.dump(final_model, f)

    print(f"\n✅ モデルを保存: {model_path}")

    # 9. 特徴量重要度の表示
    print("\n📊 特徴量重要度（Top 20）:")
    importance = final_model.feature_importance(importance_type='gain')
    feature_imp = pd.DataFrame({
        'Feature': X.columns,
        'Importance': importance
    }).sort_values(by='Importance', ascending=False)

    for idx, row in feature_imp.head(20).iterrows():
        print(f"  {row['Feature']:40s}: {row['Importance']:,.0f}")

    return final_model


def main():
    """
    メイン処理
    """
    print("\n" + "=" * 60)
    print("🏇 競馬予測 本番運用版モデル学習")
    print("=" * 60)

    # パス設定
    data_path = "ml/processed_data.csv"
    model_path = "ml/models/lgbm_model_production.pkl"

    # データの存在確認
    if not os.path.exists(data_path):
        print(f"\n❌ エラー: {data_path} が見つかりません")
        print("\n次のコマンドで特徴量を生成してください:")
        print("  python ml/feature_engineering.py")
        return

    # 学習実行
    model = train_with_timeseries_split(
        data_path=data_path,
        model_path=model_path,
        n_splits=5
    )

    if model:
        print("\n" + "=" * 60)
        print("✅ 学習完了")
        print("=" * 60)
        print("\n次のステップ:")
        print("1. public_app.py を編集:")
        print("   MODEL_PATH = 'ml/models/lgbm_model_production.pkl'")
        print("\n2. アプリを再起動:")
        print("   streamlit run public_app.py")
    else:
        print("\n❌ 学習に失敗しました")


if __name__ == "__main__":
    main()
