#!/usr/bin/env python3
"""
Basic CSVのカラムズレ問題を分析・修正
"""

import pandas as pd

# 問題の分析
print("🔍 カラムズレ問題の分析\n")
print("="*80)

# JRA Basic
jra_basic = "/Users/itoudaiki/Program/dai-keiba/data/raw/database_basic.csv"
df_jra = pd.read_csv(jra_basic, nrows=5)

print(f"\n📊 JRA Basic CSV")
print(f"ヘッダーカラム数: {len(df_jra.columns)}")
print(f"カラム名:\n{list(df_jra.columns)}\n")

print("サンプルデータ(最初の行):")
for col in df_jra.columns:
    val = df_jra[col].iloc[0] if len(df_jra) > 0 else "N/A"
    print(f"  {col}: {val}")

# NAR Basic
nar_basic = "/Users/itoudaiki/Program/dai-keiba/data/raw/database_nar_basic.csv"
df_nar = pd.read_csv(nar_basic, nrows=5)

print(f"\n📊 NAR Basic CSV")
print(f"ヘッダーカラム数: {len(df_nar.columns)}")
print(f"カラム名:\n{list(df_nar.columns)}\n")

print("サンプルデータ(最初の行):")
for col in df_nar.columns:
    val = df_nar[col].iloc[0] if len(df_nar) > 0 else "N/A"
    print(f"  {col}: {val}")

print("\n" + "="*80)
print("\n⚠️  問題:")
print("  - ヘッダーは26カラム")
print("  - データ行は20カラム程度")
print("  - 会場、レース名などが欠落")
print("\n💡 原因:")
print("  - Basicノートブックのscrape_race_basic()関数が")
print("    メタデータを正しく抽出できていない")
print("\n🔧 解決策:")
print("  - Basicノートブックのスクレイピングロジックを修正")
print("  - 会場、レース名、日付などを正しく抽出")
