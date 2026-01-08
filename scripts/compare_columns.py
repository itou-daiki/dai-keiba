#!/usr/bin/env python3
"""
ユーザー提示のカラムリストとノートブックの実装を比較
"""

# ユーザーが提示したカラムリスト
user_columns = """日付	会場	レース番号	レース名	重賞	コースタイプ	距離	回り	天候	馬場状態	着順	枠	馬番	馬名	性齢	斤量	騎手	タイム	着差	人気	単勝オッズ	後3F	厩舎	馬体重(増減)	race_id	horse_id	past_1_date	past_1_rank	past_1_time	past_1_run_style	past_1_race_name	past_1_last_3f	past_1_horse_weight	past_1_jockey	past_1_condition	past_1_odds	past_1_weather	past_1_distance	past_1_course_type	past_2_date	past_2_rank	past_2_time	past_2_run_style	past_2_race_name	past_2_last_3f	past_2_horse_weight	past_2_jockey	past_2_condition	past_2_odds	past_2_weather	past_2_distance	past_2_course_type	past_3_date	past_3_rank	past_3_time	past_3_run_style	past_3_race_name	past_3_last_3f	past_3_horse_weight	past_3_jockey	past_3_condition	past_3_odds	past_3_weather	past_3_distance	past_3_course_type	past_4_date	past_4_rank	past_4_time	past_4_run_style	past_4_race_name	past_4_last_3f	past_4_horse_weight	past_4_jockey	past_4_condition	past_4_odds	past_4_weather	past_4_distance	past_4_course_type	past_5_date	past_5_rank	past_5_time	past_5_run_style	past_5_race_name	past_5_last_3f	past_5_horse_weight	past_5_jockey	past_5_condition	past_5_odds	past_5_weather	past_5_distance	past_5_course_type	father	mother	bms""".split('\t')

# ノートブックの実装カラム
notebook_columns = [
    "日付", "会場", "レース番号", "レース名", "重賞", "コースタイプ", "距離", "回り", "天候", "馬場状態",
    "着順", "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "タイム", "着差", "人気", "単勝オッズ",
    "後3F", "厩舎", "馬体重(増減)", "race_id", "horse_id"
]

# 過去5走カラムを追加
for i in range(1, 6):
    p = f"past_{i}"
    notebook_columns.extend([
        f"{p}_date", f"{p}_rank", f"{p}_time", f"{p}_run_style", f"{p}_race_name",
        f"{p}_last_3f", f"{p}_horse_weight", f"{p}_jockey", f"{p}_condition",
        f"{p}_odds", f"{p}_weather", f"{p}_distance", f"{p}_course_type"
    ])

# 血統カラムを追加
notebook_columns.extend(["father", "mother", "bms"])

print("=" * 80)
print("📊 カラム比較: ユーザー提示 vs ノートブック実装")
print("=" * 80)

print(f"\nユーザー提示カラム数: {len(user_columns)}")
print(f"ノートブック実装カラム数: {len(notebook_columns)}")

# 完全一致チェック
if user_columns == notebook_columns:
    print("\n✅ 完全一致!")
else:
    print("\n⚠️  差異があります")
    
    # 差異を確認
    user_set = set(user_columns)
    notebook_set = set(notebook_columns)
    
    missing_in_notebook = user_set - notebook_set
    extra_in_notebook = notebook_set - user_set
    
    if missing_in_notebook:
        print(f"\n❌ ノートブックに不足しているカラム ({len(missing_in_notebook)}個):")
        for col in sorted(missing_in_notebook):
            print(f"   - {col}")
    
    if extra_in_notebook:
        print(f"\n➕ ノートブックに余分なカラム ({len(extra_in_notebook)}個):")
        for col in sorted(extra_in_notebook):
            print(f"   - {col}")
    
    # 順序の確認
    print("\n📋 順序の比較:")
    print("-" * 80)
    
    max_len = max(len(user_columns), len(notebook_columns))
    differences = []
    
    for i in range(max_len):
        user_col = user_columns[i] if i < len(user_columns) else "(なし)"
        notebook_col = notebook_columns[i] if i < len(notebook_columns) else "(なし)"
        
        if user_col != notebook_col:
            differences.append((i+1, user_col, notebook_col))
    
    if differences:
        print(f"\n⚠️  順序が異なる箇所 ({len(differences)}個):")
        for idx, user_col, nb_col in differences[:10]:  # 最初の10個だけ表示
            print(f"   位置{idx}: ユーザー='{user_col}' vs ノートブック='{nb_col}'")
        
        if len(differences) > 10:
            print(f"   ... 他 {len(differences) - 10} 箇所")
    else:
        print("\n✅ 順序も完全一致!")

# 詳細比較
print("\n" + "=" * 80)
print("📝 詳細比較")
print("=" * 80)

print("\n基本カラム (26個):")
for i in range(26):
    u = user_columns[i] if i < len(user_columns) else "(なし)"
    n = notebook_columns[i] if i < len(notebook_columns) else "(なし)"
    match = "✅" if u == n else "❌"
    print(f"  {i+1:2}. {match} {u:20} | {n}")

print("\n過去5走カラム (65個):")
print("  (各走13項目 × 5走)")
for run in range(1, 6):
    print(f"\n  past_{run}_:")
    start_idx = 26 + (run - 1) * 13
    for j in range(13):
        idx = start_idx + j
        u = user_columns[idx] if idx < len(user_columns) else "(なし)"
        n = notebook_columns[idx] if idx < len(notebook_columns) else "(なし)"
        match = "✅" if u == n else "❌"
        print(f"    {idx+1:2}. {match} {u:30} | {n}")

print("\n血統カラム (3個):")
for i in range(91, 94):
    u = user_columns[i] if i < len(user_columns) else "(なし)"
    n = notebook_columns[i] if i < len(notebook_columns) else "(なし)"
    match = "✅" if u == n else "❌"
    print(f"  {i+1:2}. {match} {u:20} | {n}")

print("\n" + "=" * 80)
print("🎯 結論")
print("=" * 80)

if user_columns == notebook_columns:
    print("\n✅ ノートブックの実装は、ユーザーが提示したカラムリストと完全に一致しています。")
    print("   カラムのずれは発生しません。")
else:
    print("\n⚠️  ノートブックの実装に調整が必要です。")
