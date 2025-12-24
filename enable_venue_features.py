#!/usr/bin/env python3
"""
会場特性特徴量を有効にするスクリプト

このスクリプトは以下を実行します：
1. JRA/NAR両方の特徴量を再生成（use_venue_features=True）
2. 公開ページの設定を自動更新

実行後、管理画面でモデルを再学習してください。
"""

import sys
import os

# パスの追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml'))

from feature_engineering import calculate_features

def main():
    print("=" * 60)
    print("会場特性特徴量を有効化")
    print("=" * 60)

    # ステップ1: JRAの特徴量を再生成
    print("\n[1/2] JRAの特徴量を再生成中...")
    try:
        calculate_features(
            'database.csv',
            'ml/processed_data.csv',
            lambda_decay=0.2,
            use_venue_features=True  # 会場特性を有効化
        )
        print("✅ JRAの特徴量を再生成しました")
    except Exception as e:
        print(f"❌ エラー: {e}")
        return

    # ステップ2: NARの特徴量を再生成
    print("\n[2/2] NARの特徴量を再生成中...")
    try:
        calculate_features(
            'database_nar.csv',
            'ml/processed_data_nar.csv',
            lambda_decay=0.2,
            use_venue_features=True  # 会場特性を有効化
        )
        print("✅ NARの特徴量を再生成しました")
    except Exception as e:
        print(f"❌ エラー: {e}")
        return

    print("\n" + "=" * 60)
    print("✅ 特徴量の再生成が完了しました！")
    print("=" * 60)

    print("\n次のステップ:")
    print("1. public_app.py:349を修正")
    print("   X_df = process_data(df, use_venue_features=True)")
    print("")
    print("2. 管理画面でモデルを再学習")
    print("   - JRAモード: 「学習開始」ボタンをクリック")
    print("   - NARモード: 「学習開始」ボタンをクリック")
    print("")
    print("3. 公開ページで予測を実行して確認")
    print("")
    print("追加される特徴量（11個）:")
    print("  - 脚質コード、脚質一貫性、序盤位置、位置変化")
    print("  - 会場×脚質相性、会場×距離相性")
    print("  - 直線距離、コース幅、勾配")
    print("  - 会場×馬場状態相性、枠番有利度")

if __name__ == "__main__":
    main()
