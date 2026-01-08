#!/usr/bin/env python3
"""
カラム完全性検証スクリプト
全94カラムのデータが正しく取得できるかテスト
"""

import pandas as pd
from pathlib import Path

# 期待されるカラムリスト(94カラム)
EXPECTED_COLUMNS = [
    # 基本情報 (26カラム)
    "日付", "会場", "レース番号", "レース名", "重賞", "コースタイプ", "距離", "回り", "天候", "馬場状態",
    "着順", "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "タイム", "着差", "人気", "単勝オッズ",
    "後3F", "厩舎", "馬体重(増減)", "race_id", "horse_id",
]

# 過去5走カラム (65カラム)
for i in range(1, 6):
    p = f"past_{i}"
    EXPECTED_COLUMNS.extend([
        f"{p}_date", f"{p}_rank", f"{p}_time", f"{p}_run_style", f"{p}_race_name",
        f"{p}_last_3f", f"{p}_horse_weight", f"{p}_jockey", f"{p}_condition",
        f"{p}_odds", f"{p}_weather", f"{p}_distance", f"{p}_course_type"
    ])

# 血統カラム (3カラム)
EXPECTED_COLUMNS.extend(["father", "mother", "bms"])


def verify_columns(csv_path: str) -> dict:
    """
    CSVファイルのカラムを検証
    
    Returns:
        検証結果の辞書
    """
    print(f"\n{'='*80}")
    print(f"📋 カラム完全性検証: {Path(csv_path).name}")
    print(f"{'='*80}\n")
    
    if not Path(csv_path).exists():
        return {
            "status": "error",
            "message": f"ファイルが存在しません: {csv_path}"
        }
    
    try:
        # ヘッダーのみ読み込み
        df = pd.read_csv(csv_path, nrows=0)
        actual_columns = df.columns.tolist()
        
        print(f"✅ ファイル読み込み成功")
        print(f"   期待カラム数: {len(EXPECTED_COLUMNS)}")
        print(f"   実際カラム数: {len(actual_columns)}")
        
        # カラム比較
        expected_set = set(EXPECTED_COLUMNS)
        actual_set = set(actual_columns)
        
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        
        # 順序チェック
        order_match = (actual_columns == EXPECTED_COLUMNS)
        
        result = {
            "status": "success" if not missing and not extra and order_match else "warning",
            "total_expected": len(EXPECTED_COLUMNS),
            "total_actual": len(actual_columns),
            "missing_columns": list(missing),
            "extra_columns": list(extra),
            "order_match": order_match
        }
        
        # 結果表示
        print(f"\n{'─'*80}")
        print("📊 検証結果")
        print(f"{'─'*80}\n")
        
        if not missing and not extra and order_match:
            print("✅ 完全一致! すべてのカラムが正しく存在します")
        else:
            if missing:
                print(f"❌ 不足カラム ({len(missing)}個):")
                for col in sorted(missing):
                    print(f"   - {col}")
            
            if extra:
                print(f"\n➕ 余分なカラム ({len(extra)}個):")
                for col in sorted(extra):
                    print(f"   - {col}")
            
            if not order_match:
                print(f"\n⚠️  カラムの順序が異なります")
        
        # データ内容の検証(サンプル)
        print(f"\n{'─'*80}")
        print("📊 データ内容サンプル検証")
        print(f"{'─'*80}\n")
        
        df_sample = pd.read_csv(csv_path, nrows=10, dtype=str)
        
        if len(df_sample) > 0:
            print(f"✅ サンプル行数: {len(df_sample)}")
            
            # 各カテゴリの欠損率をチェック
            categories = {
                "基本情報": EXPECTED_COLUMNS[:26],
                "過去1走": [c for c in EXPECTED_COLUMNS if c.startswith("past_1_")],
                "過去2走": [c for c in EXPECTED_COLUMNS if c.startswith("past_2_")],
                "過去3走": [c for c in EXPECTED_COLUMNS if c.startswith("past_3_")],
                "過去4走": [c for c in EXPECTED_COLUMNS if c.startswith("past_4_")],
                "過去5走": [c for c in EXPECTED_COLUMNS if c.startswith("past_5_")],
                "血統": ["father", "mother", "bms"]
            }
            
            print("\n欠損率:")
            for cat_name, cols in categories.items():
                available_cols = [c for c in cols if c in df_sample.columns]
                if available_cols:
                    missing_rate = df_sample[available_cols].isna().mean().mean() * 100
                    empty_rate = (df_sample[available_cols] == "").mean().mean() * 100
                    total_empty = missing_rate + empty_rate
                    
                    status = "✅" if total_empty < 10 else ("⚠️" if total_empty < 50 else "❌")
                    print(f"  {status} {cat_name:12}: {total_empty:5.1f}% 空")
        else:
            print("⚠️  データが空です")
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"エラー: {e}"
        }


def analyze_data_sources():
    """
    各カラムのデータソースを分析
    """
    print(f"\n{'='*80}")
    print("📊 データソース分析")
    print(f"{'='*80}\n")
    
    sources = {
        "レース結果ページ": {
            "URL": "https://race.netkeiba.com/race/result.html?race_id=XXXX",
            "取得方法": "BeautifulSoup + テーブルパース",
            "カラム数": 26,
            "カラム": [
                "日付", "会場", "レース番号", "レース名", "重賞", "コースタイプ", "距離", "回り",
                "天候", "馬場状態", "着順", "枠", "馬番", "馬名", "性齢", "斤量", "騎手",
                "タイム", "着差", "人気", "単勝オッズ", "後3F", "厩舎", "馬体重(増減)",
                "race_id", "horse_id"
            ],
            "リスク": "低 - テーブル構造が安定"
        },
        "馬履歴ページ": {
            "URL": "https://db.netkeiba.com/horse/result/HORSE_ID/",
            "取得方法": "BeautifulSoup + pd.read_html",
            "カラム数": 65,
            "カラム": "past_1_* ~ past_5_* (各13項目)",
            "リスク": "中 - 新馬の場合は空、レース日付フィルタリング必須"
        },
        "血統ページ": {
            "URL": "https://db.netkeiba.com/horse/ped/HORSE_ID/",
            "取得方法": "BeautifulSoup + CSSセレクタ",
            "カラム数": 3,
            "カラム": ["father", "mother", "bms"],
            "リスク": "低 - テーブル構造が安定"
        }
    }
    
    for source_name, info in sources.items():
        print(f"📌 {source_name}")
        print(f"   URL: {info['URL']}")
        print(f"   取得方法: {info['取得方法']}")
        print(f"   カラム数: {info['カラム数']}")
        print(f"   リスク: {info['リスク']}")
        print()


def recommend_splitting_strategy():
    """
    ノートブック分割戦略を提案
    """
    print(f"\n{'='*80}")
    print("🚀 ノートブック分割戦略の提案")
    print(f"{'='*80}\n")
    
    strategies = [
        {
            "name": "戦略1: 2段階分割(基本 + 詳細)",
            "notebooks": [
                "Colab_JRA_Basic.ipynb - レース基本情報のみ(26カラム)",
                "Colab_JRA_Details.ipynb - 履歴+血統追加(68カラム)"
            ],
            "pros": [
                "基本情報は高速取得(1レース=1リクエスト)",
                "詳細情報は並列実行可能",
                "失敗時の再実行が容易"
            ],
            "cons": [
                "2回実行が必要",
                "データ結合の手間"
            ],
            "time_reduction": "30-40%",
            "complexity": "中"
        },
        {
            "name": "戦略2: 3段階分割(レース + 履歴 + 血統)",
            "notebooks": [
                "Colab_JRA_Race.ipynb - レース情報(26カラム)",
                "Colab_JRA_History.ipynb - 馬履歴(65カラム)",
                "Colab_JRA_Pedigree.ipynb - 血統(3カラム)"
            ],
            "pros": [
                "各段階が独立して実行可能",
                "履歴と血統を並列実行可能",
                "最大の柔軟性"
            ],
            "cons": [
                "3回実行が必要",
                "データ結合が複雑"
            ],
            "time_reduction": "40-50%",
            "complexity": "高"
        },
        {
            "name": "戦略3: 現状維持 + 最適化",
            "notebooks": [
                "Colab_JRA_Scraping.ipynb - 全データ一括(94カラム)"
            ],
            "pros": [
                "1回の実行で完了",
                "データ整合性が保証される",
                "シンプル"
            ],
            "cons": [
                "実行時間が長い",
                "失敗時の再実行コストが高い"
            ],
            "time_reduction": "0% (ベースライン)",
            "complexity": "低"
        }
    ]
    
    for i, strategy in enumerate(strategies, 1):
        print(f"{'─'*80}")
        print(f"戦略{i}: {strategy['name']}")
        print(f"{'─'*80}")
        print(f"\n📓 ノートブック構成:")
        for nb in strategy['notebooks']:
            print(f"   - {nb}")
        
        print(f"\n✅ メリット:")
        for pro in strategy['pros']:
            print(f"   + {pro}")
        
        print(f"\n⚠️  デメリット:")
        for con in strategy['cons']:
            print(f"   - {con}")
        
        print(f"\n⏱️  時間短縮: {strategy['time_reduction']}")
        print(f"🔧 複雑度: {strategy['complexity']}")
        print()
    
    print(f"{'='*80}")
    print("💡 推奨: 戦略1 (2段階分割)")
    print(f"{'='*80}")
    print("\n理由:")
    print("  1. 基本情報は高速取得可能(Colabタイムアウト回避)")
    print("  2. 詳細情報は別セッションで実行可能")
    print("  3. 実装が比較的シンプル")
    print("  4. 30-40%の時間短縮が見込める")
    print()


if __name__ == "__main__":
    # データソース分析
    analyze_data_sources()
    
    # 分割戦略の提案
    recommend_splitting_strategy()
    
    # CSVファイルの検証(存在する場合)
    csv_paths = [
        "/Users/itoudaiki/Program/dai-keiba/data/raw/database.csv",
        "/Users/itoudaiki/Program/dai-keiba/data/raw/database_nar.csv"
    ]
    
    for csv_path in csv_paths:
        if Path(csv_path).exists():
            verify_columns(csv_path)
    
    print(f"\n{'='*80}")
    print("✅ 検証完了")
    print(f"{'='*80}\n")
