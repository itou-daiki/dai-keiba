#!/usr/bin/env python3
"""
NAR 基本情報CSVと詳細情報CSVをマージするスクリプト
"""

import pandas as pd
import os
from pathlib import Path

def merge_nar_data(save_dir: str = "/Users/itoudaiki/Program/dai-keiba/data/raw"):
    """
    database_nar_basic.csv + database_nar_details.csv → database_nar.csv
    """
    print(f"\n{'='*80}")
    print("🔗 NARデータマージ")
    print(f"{'='*80}\n")
    
    basic_path = os.path.join(save_dir, "database_nar_basic.csv")
    details_path = os.path.join(save_dir, "database_nar_details.csv")
    output_path = os.path.join(save_dir, "database_nar.csv")
    
    # ファイル存在確認
    if not os.path.exists(basic_path):
        print(f"❌ 基本情報CSVが見つかりません: {basic_path}")
        return
    
    if not os.path.exists(details_path):
        print(f"❌ 詳細情報CSVが見つかりません: {details_path}")
        return
    
    # 読み込み
    print("📖 基本情報を読み込み中...")
    basic_df = pd.read_csv(basic_path, dtype=str)
    print(f"   {len(basic_df)} 行読み込み")
    
    print("📖 詳細情報を読み込み中...")
    details_df = pd.read_csv(details_path, dtype=str)
    print(f"   {len(details_df)} 行読み込み")
    
    # マージ
    print("\n🔗 データをマージ中...")
    merged_df = basic_df.merge(
        details_df,
        on=['race_id', 'horse_id'],
        how='left'
    )
    
    print(f"   マージ後: {len(merged_df)} 行")
    
    # カラム順序を整列
    expected_columns = [
        # 基本情報 (26カラム)
        "日付", "会場", "レース番号", "レース名", "重賞", "コースタイプ", "距離", "回り", "天候", "馬場状態",
        "着順", "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "タイム", "着差", "人気", "単勝オッズ",
        "後3F", "厩舎", "馬体重(増減)", "race_id", "horse_id",
    ]
    
    # 過去5走カラム (65カラム)
    for i in range(1, 6):
        p = f"past_{i}"
        expected_columns.extend([
            f"{p}_date", f"{p}_rank", f"{p}_time", f"{p}_run_style", f"{p}_race_name",
            f"{p}_last_3f", f"{p}_horse_weight", f"{p}_jockey", f"{p}_condition",
            f"{p}_odds", f"{p}_weather", f"{p}_distance", f"{p}_course_type"
        ])
    
    # 血統カラム (3カラム)
    expected_columns.extend(["father", "mother", "bms"])
    
    # 整列
    merged_df = merged_df.reindex(columns=expected_columns, fill_value='')
    
    # 保存
    print(f"\n💾 保存中: {output_path}")
    merged_df.to_csv(output_path, index=False)
    
    print(f"\n✅ マージ完了!")
    print(f"   出力: {output_path}")
    print(f"   行数: {len(merged_df)}")
    print(f"   カラム数: {len(merged_df.columns)}")
    
    # 統計
    print(f"\n📊 データ統計:")
    print(f"   基本情報のみ: {len(basic_df)} 行")
    print(f"   詳細情報: {len(details_df)} ユニーク馬")
    print(f"   最終データ: {len(merged_df)} 行")

if __name__ == "__main__":
    import sys
    
    save_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/itoudaiki/Program/dai-keiba/data/raw"
    merge_nar_data(save_dir)
