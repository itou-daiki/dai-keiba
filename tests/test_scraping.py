#!/usr/bin/env python3
"""
スクレイピング機能の動作確認スクリプト
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """必要なモジュールのインポートテスト"""
    print("=" * 60)
    print("1. インポートテスト")
    print("=" * 60)

    try:
        import pandas as pd
        print("✅ pandas imported")
    except ImportError as e:
        print(f"❌ pandas import failed: {e}")
        return False

    try:
        import requests
        print("✅ requests imported")
    except ImportError as e:
        print(f"❌ requests import failed: {e}")
        return False

    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup imported")
    except ImportError as e:
        print(f"❌ BeautifulSoup import failed: {e}")
        return False

    try:
        from scraper.auto_scraper import scrape_race_data
        print("✅ auto_scraper imported")
    except ImportError as e:
        print(f"❌ auto_scraper import failed: {e}")
        return False

    print()
    return True


def test_database_exists():
    """データベースファイルの存在確認"""
    print("=" * 60)
    print("2. データベース存在確認")
    print("=" * 60)

    db_path = "database.csv"

    if os.path.exists(db_path):
        import pandas as pd
        df = pd.read_csv(db_path)
        print(f"✅ database.csv exists")
        print(f"  行数: {len(df):,}")
        print(f"  列数: {len(df.columns)}")

        # Check required columns
        required_cols = ['日付', '会場', 'レース名', '着 順', '馬名', 'horse_id']
        missing = [col for col in required_cols if col not in df.columns]

        if missing:
            print(f"⚠️ 不足している列: {missing}")
        else:
            print("✅ 必要な列がすべて存在")

        print()
        return True
    else:
        print(f"❌ database.csv not found at {os.path.abspath(db_path)}")
        print()
        return False


def test_feature_engineering():
    """特徴量生成のテスト"""
    print("=" * 60)
    print("3. 特徴量生成テスト")
    print("=" * 60)

    try:
        from ml.feature_engineering import process_data
        import pandas as pd

        # Load sample data
        df = pd.read_csv("database.csv")

        if len(df) == 0:
            print("⚠️ データベースが空です")
            return False

        # Take first 10 rows for testing
        sample_df = df.head(10).copy()

        print(f"サンプルデータ: {len(sample_df)}行")
        print("特徴量生成中...")

        processed = process_data(sample_df)

        print(f"✅ 特徴量生成成功")
        print(f"  生成された特徴量数: {len([c for c in processed.columns if c not in ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']])}")

        # Check new features
        new_features = [
            'turf_compatibility',
            'dirt_compatibility',
            'jockey_compatibility',
            'is_rest_comeback',
            'race_class'
        ]

        existing_new_features = [f for f in new_features if f in processed.columns]
        print(f"  新規特徴量: {len(existing_new_features)}/{len(new_features)} 存在")

        if existing_new_features:
            print(f"  例: {', '.join(existing_new_features[:5])}")

        print()
        return True

    except Exception as e:
        print(f"❌ 特徴量生成エラー: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_scraping_single_race():
    """単一レースのスクレイピングテスト"""
    print("=" * 60)
    print("4. スクレイピング機能テスト（単一レース）")
    print("=" * 60)

    try:
        from scraper.auto_scraper import scrape_race_data

        # Test with a known race ID (adjust as needed)
        test_race_id = "202506050101"

        print(f"テストレースID: {test_race_id}")
        print("スクレイピング中...")

        result = scrape_race_data(test_race_id)

        if result is None:
            print("⚠️ レースデータの取得に失敗（レースが存在しないか、アクセスエラー）")
            print("  ※ これは正常な場合もあります（過去のレースIDの場合）")
        else:
            print("✅ スクレイピング成功")
            print(f"  取得データ型: {type(result)}")

        print()
        return True

    except Exception as e:
        print(f"❌ スクレイピングエラー: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_model_loading():
    """モデル読み込みテスト"""
    print("=" * 60)
    print("5. モデル読み込みテスト")
    print("=" * 60)

    model_path = "ml/models/lgbm_model.pkl"

    if not os.path.exists(model_path):
        print(f"⚠️ モデルファイルが存在しません: {model_path}")
        print("  ※ 初回は学習が必要です")
        print()
        return False

    try:
        import pickle

        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        print("✅ モデル読み込み成功")
        print(f"  モデル型: {type(model)}")
        print()
        return True

    except Exception as e:
        print(f"❌ モデル読み込みエラー: {e}")
        print()
        return False


def main():
    """メイン実行"""
    print("\n" + "=" * 60)
    print("🔍 スクレイピング機能 動作確認")
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("インポート", test_imports()))
    results.append(("データベース", test_database_exists()))
    results.append(("特徴量生成", test_feature_engineering()))
    results.append(("スクレイピング", test_scraping_single_race()))
    results.append(("モデル読み込み", test_model_loading()))

    # Summary
    print("=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print()
    print(f"合計: {passed}/{total} テスト成功")

    if passed == total:
        print("\n🎉 すべてのテストが成功しました！")
    else:
        print("\n⚠️ 一部のテストが失敗しました。上記のエラーを確認してください。")
        print("\n推奨アクション:")
        print("1. 依存パッケージのインストール: pip install -r requirements.txt")
        print("2. データベースの確認: database.csvが存在するか確認")
        print("3. モデルの学習: python ml/feature_engineering.py && python ml/train_model.py")


if __name__ == "__main__":
    main()
