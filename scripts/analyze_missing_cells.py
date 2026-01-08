#!/usr/bin/env python3
"""
CSVファイルの欠損セルを分析
"""

import pandas as pd
import numpy as np

def analyze_missing_data(csv_path):
    """
    CSVファイルの欠損データを分析
    """
    print(f"\n{'='*80}")
    print(f"📊 欠損データ分析: {csv_path.split('/')[-1]}")
    print(f"{'='*80}\n")
    
    # CSVを読み込み
    df = pd.read_csv(csv_path, dtype=str, nrows=100)
    
    print(f"総行数(サンプル): {len(df)}")
    print(f"総カラム数: {len(df.columns)}\n")
    
    # 欠損率を計算
    missing_stats = []
    for col in df.columns:
        total = len(df)
        missing = df[col].isna().sum()
        empty = (df[col] == '').sum()
        missing_or_empty = missing + empty
        rate = (missing_or_empty / total * 100) if total > 0 else 0
        
        if rate > 0:
            missing_stats.append({
                'カラム': col,
                '欠損数': missing,
                '空文字数': empty,
                '合計': missing_or_empty,
                '欠損率': rate
            })
    
    # 欠損率でソート
    missing_stats.sort(key=lambda x: x['欠損率'], reverse=True)
    
    # 結果表示
    if missing_stats:
        print("📋 欠損データがあるカラム:\n")
        print(f"{'カラム名':<20} {'欠損':<8} {'空文字':<8} {'合計':<8} {'欠損率':<10}")
        print(f"{'-'*70}")
        
        for stat in missing_stats[:20]:  # 上位20件
            print(f"{stat['カラム']:<20} {stat['欠損数']:<8} {stat['空文字数']:<8} "
                  f"{stat['合計']:<8} {stat['欠損率']:<10.1f}%")
    else:
        print("✅ 欠損データなし")
    
    # カテゴリ別分析
    print(f"\n{'='*80}")
    print("📊 カテゴリ別欠損率")
    print(f"{'='*80}\n")
    
    categories = {
        '基本情報': ['日付', '会場', 'レース番号', 'レース名', 'コースタイプ', '距離', '天候', '馬場状態'],
        'レース結果': ['着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム', '着差', '人気', '単勝オッズ'],
        '過去1走': [col for col in df.columns if col.startswith('past_1_')],
        '過去2走': [col for col in df.columns if col.startswith('past_2_')],
        '血統': ['father', 'mother', 'bms'],
    }
    
    for cat_name, cols in categories.items():
        existing_cols = [c for c in cols if c in df.columns]
        if not existing_cols:
            continue
        
        total_cells = len(df) * len(existing_cols)
        missing_cells = 0
        
        for col in existing_cols:
            missing_cells += df[col].isna().sum() + (df[col] == '').sum()
        
        rate = (missing_cells / total_cells * 100) if total_cells > 0 else 0
        status = "✅" if rate < 5 else "⚠️" if rate < 20 else "❌"
        
        print(f"{status} {cat_name:<15}: {rate:>6.1f}% 欠損")
    
    # サンプルデータ表示
    print(f"\n{'='*80}")
    print("📝 サンプルデータ(最初の3行)")
    print(f"{'='*80}\n")
    
    sample_cols = ['日付', '会場', 'レース名', '馬名', '着順', 'タイム', 'race_id', 'horse_id']
    existing_sample_cols = [c for c in sample_cols if c in df.columns]
    
    if existing_sample_cols:
        print(df[existing_sample_cols].head(3).to_string())

if __name__ == "__main__":
    files = [
        "/Users/itoudaiki/Program/dai-keiba/data/raw/database (3).csv",
        "/Users/itoudaiki/Program/dai-keiba/data/raw/database_basic.csv",
    ]
    
    for f in files:
        try:
            analyze_missing_data(f)
        except Exception as e:
            print(f"❌ エラー: {f} - {e}")
