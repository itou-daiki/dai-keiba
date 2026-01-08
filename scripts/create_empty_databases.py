#!/usr/bin/env python3
"""
テスト用の空のdatabase.csvとdatabase_nar.csvを作成
全94カラムのヘッダーのみを含む
"""

import pandas as pd
import os

def create_empty_database_csv(output_path: str):
    """
    全94カラムのヘッダーのみを含む空のCSVを作成
    """
    # 全94カラムを定義
    columns = [
        # 基本情報 (26カラム)
        "日付", "会場", "レース番号", "レース名", "重賞", "コースタイプ", "距離", "回り", "天候", "馬場状態",
        "着順", "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "タイム", "着差", "人気", "単勝オッズ",
        "後3F", "厩舎", "馬体重(増減)", "race_id", "horse_id",
    ]
    
    # 過去5走カラム (65カラム)
    for i in range(1, 6):
        p = f"past_{i}"
        columns.extend([
            f"{p}_date", f"{p}_rank", f"{p}_time", f"{p}_run_style", f"{p}_race_name",
            f"{p}_last_3f", f"{p}_horse_weight", f"{p}_jockey", f"{p}_condition",
            f"{p}_odds", f"{p}_weather", f"{p}_distance", f"{p}_course_type"
        ])
    
    # 血統カラム (3カラム)
    columns.extend(["father", "mother", "bms"])
    
    # 空のDataFrameを作成
    df = pd.DataFrame(columns=columns)
    
    # CSVとして保存
    df.to_csv(output_path, index=False)
    
    print(f"✅ 空のCSVを作成しました: {output_path}")
    print(f"   カラム数: {len(columns)}")
    print(f"   データ行数: 0")

if __name__ == "__main__":
    # JRA用
    jra_path = "/Users/itoudaiki/Program/dai-keiba/data/raw/database.csv"
    create_empty_database_csv(jra_path)
    
    # NAR用
    nar_path = "/Users/itoudaiki/Program/dai-keiba/data/raw/database_nar.csv"
    create_empty_database_csv(nar_path)
    
    print(f"\n{'='*80}")
    print("✅ テスト用の空のCSVファイルを作成しました")
    print(f"{'='*80}")
    print(f"\nJRA: {jra_path}")
    print(f"NAR: {nar_path}")
    print(f"\nこれらのファイルはヘッダー行のみを含み、データ行は0件です。")
    print(f"スクレイピングノートブックを実行すると、このファイルにデータが追記されます。")
