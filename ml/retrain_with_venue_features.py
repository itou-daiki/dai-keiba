#!/usr/bin/env python3
"""
会場特性を含む新しい特徴量でモデルを再学習するスクリプト

使用方法:
    python ml/retrain_with_venue_features.py

出力:
    - ml/models/lgbm_model_v2.pkl (新しいモデル)
    - ml/processed_data_v2.csv (新しい特徴量セット)
"""

import os
import sys
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.feature_engineering import process_data
from ml.train_model import train_model


def main():
    print("=" * 60)
    print("🔄 会場特性を含む新しい特徴量でモデルを再学習")
    print("=" * 60)
    print()

    # Paths
    db_path = "database.csv"
    processed_path = "ml/processed_data_v2.csv"
    model_path = "ml/models/lgbm_model_v2.pkl"

    # 1. データベースの確認
    if not os.path.exists(db_path):
        print(f"❌ エラー: {db_path} が見つかりません")
        return

    print(f"✅ データベース: {db_path}")
    df = pd.read_csv(db_path)
    print(f"   行数: {len(df):,}")
    print()

    # 2. 特徴量生成（会場特性を含む）
    print("📊 特徴量生成中（会場特性を含む）...")
    print("   use_venue_features=True")

    try:
        processed = process_data(df, lambda_decay=0.2, use_venue_features=True)
    except Exception as e:
        print(f"❌ 特徴量生成エラー: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. ターゲット変数を追加
    if 'rank' in processed.columns:
        processed['target_top3'] = (processed['rank'] <= 3).astype(int)
    else:
        print("⚠️ 警告: 'rank'列が見つかりません。ターゲット変数を設定できません")
        processed['target_top3'] = 0

    # 4. NaNを埋める
    processed = processed.fillna(0)

    # 5. 保存
    processed.to_csv(processed_path, index=False)
    print(f"✅ 処理済みデータを保存: {processed_path}")
    print(f"   行数: {len(processed):,}")

    # 特徴量数を表示
    feature_cols = [c for c in processed.columns if c not in [
        '馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順', 'target_top3'
    ]]
    print(f"   特徴量数: {len(feature_cols)}")
    print()

    # 6. モデル学習
    print("🤖 モデル学習中...")
    print(f"   出力先: {model_path}")

    try:
        # LightGBMパラメータ
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42
        }

        train_model(processed_path, model_path, params=params)
        print()
        print("✅ モデル学習完了")
    except Exception as e:
        print(f"❌ モデル学習エラー: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 60)
    print("🎉 すべての処理が完了しました！")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. public_app.py を編集:")
    print("   - line 171: process_data(df, use_venue_features=True)")
    print("   - line 130付近: MODEL_PATH = 'ml/models/lgbm_model_v2.pkl'")
    print()
    print("2. アプリを再起動して、新しい特徴量を使った予測を試してください")
    print()


if __name__ == "__main__":
    main()
