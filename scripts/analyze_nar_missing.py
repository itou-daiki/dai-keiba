#!/usr/bin/env python3
"""
NAR(地方競馬)データの欠損分析
"""

import pandas as pd
import numpy as np

# NARデータ読み込み
nar_path = "/Users/itoudaiki/Program/dai-keiba/data/raw/database_nar_basic.csv"

try:
    df = pd.read_csv(nar_path, dtype=str)
    
    print("🔍 NAR Basic データ分析")
    print(f"{'='*80}\n")
    
    print(f"📊 基本情報:")
    print(f"  総行数: {len(df)}")
    print(f"  総カラム数: {len(df.columns)}")
    print(f"  カラム: {list(df.columns)}\n")
    
    # 欠損率分析
    print(f"📊 カラム別欠損率:")
    for col in df.columns:
        missing = df[col].isna().sum() + (df[col] == '').sum()
        rate = missing / len(df) * 100
        status = "✅" if rate < 10 else "⚠️" if rate < 50 else "❌"
        print(f"  {status} {col}: {rate:.1f}% ({missing}/{len(df)})")
    
    # 重要カラムの欠損
    print(f"\n📊 重要カラムの欠損:")
    important_cols = ['日付', '会場', 'レース番号', 'レース名', 'コースタイプ', '距離', 'race_id', 'horse_id']
    for col in important_cols:
        if col in df.columns:
            missing = df[col].isna().sum() + (df[col] == '').sum()
            rate = missing / len(df) * 100
            status = "✅" if rate < 10 else "⚠️" if rate < 50 else "❌"
            print(f"  {status} {col}: {rate:.1f}%")
    
    # サンプルデータ
    print(f"\n📊 サンプルデータ(最初の3行):")
    print(df[['日付', '会場', 'レース名', '馬名', 'race_id']].head(3).to_string(index=False))
    
except FileNotFoundError:
    print(f"❌ ファイルが見つかりません: {nar_path}")
except Exception as e:
    print(f"❌ エラー: {e}")
