#!/usr/bin/env python3
"""
騎手適性がAI勝率予測に与える影響を分析するスクリプト（NARモデル）
"""
import pickle
import pandas as pd
import json

# NARモデルとメタデータを読み込む
with open('ml/models/lgbm_model_nar.pkl', 'rb') as f:
    model = pickle.load(f)

with open('ml/models/lgbm_model_nar_meta.json', 'r') as f:
    meta = json.load(f)

# 特徴量名を取得
features = meta['features']

# 特徴量重要度を取得（Gain方式）
importance_gain = model.feature_importance(importance_type='gain')
importance_split = model.feature_importance(importance_type='split')

# DataFrameを作成
df_importance = pd.DataFrame({
    'feature': features,
    'gain': importance_gain,
    'split': importance_split
})

# 重要度でソート
df_importance = df_importance.sort_values('gain', ascending=False)

# 騎手関連特徴量を抽出
jockey_features = [
    'jockey_compatibility',
    'jockey_win_rate',
    'jockey_top3_rate',
    'jockey_races_log',
    'is_jockey_change',
    'jockey_id',
    'stable_win_rate',
    'stable_top3_rate',
    'trainer_id'
]

print("=" * 80)
print("【NAR全特徴量の重要度TOP20】")
print("=" * 80)
print(df_importance.head(20).to_string(index=False))

print("\n" + "=" * 80)
print("【NAR騎手関連特徴量の重要度】")
print("=" * 80)

jockey_df = df_importance[df_importance['feature'].isin(jockey_features)]

# 全体における騎手関連特徴量の順位と重要度
total_gain = df_importance['gain'].sum()
jockey_total_gain = jockey_df['gain'].sum()
jockey_contribution = (jockey_total_gain / total_gain) * 100

for idx, row in jockey_df.iterrows():
    rank = df_importance.index.get_loc(idx) + 1
    feature_name = row['feature']
    gain_value = row['gain']
    gain_pct = (gain_value / total_gain) * 100

    # 日本語名を追加
    jp_names = {
        'jockey_compatibility': '騎手適性度',
        'jockey_win_rate': '騎手勝率',
        'jockey_top3_rate': '騎手連対率',
        'jockey_races_log': '騎手経験値',
        'is_jockey_change': '騎手変更',
        'jockey_id': '騎手ID',
        'stable_win_rate': '調教師勝率',
        'stable_top3_rate': '調教師連対率',
        'trainer_id': '調教師ID'
    }
    jp_name = jp_names.get(feature_name, feature_name)

    print(f"{rank:2d}位: {feature_name:30s} ({jp_name:12s}) - Gain: {gain_value:8.0f} ({gain_pct:5.2f}%)")

print("\n" + "=" * 80)
print("【NAR統計サマリー】")
print("=" * 80)
print(f"騎手関連特徴量の合計貢献度: {jockey_contribution:.2f}%")
print(f"全特徴量数: {len(features)}個")
print(f"騎手関連特徴量数: {len(jockey_df)}個")
print(f"\nモデル性能 (NARモデル):")
print(f"  - AUC: {meta['performance']['auc']:.4f}")
print(f"  - 精度: {meta['performance']['accuracy']*100:.2f}%")
print(f"  - 適合率: {meta['performance']['precision']*100:.2f}%")
print(f"  - 再現率: {meta['performance']['recall']*100:.2f}%")

print("\n" + "=" * 80)
print("【NAR結論】")
print("=" * 80)

top5_features = df_importance.head(5)['feature'].tolist()
jockey_in_top5 = [f for f in top5_features if f in jockey_features]

if jockey_in_top5:
    print(f"✅ 騎手関連特徴量がTOP5に{len(jockey_in_top5)}個含まれています: {jockey_in_top5}")
else:
    top_jockey_rank = jockey_df.index[0]
    top_jockey_position = df_importance.index.get_loc(top_jockey_rank) + 1
    print(f"騎手関連特徴量の最高順位: {top_jockey_position}位 ({jockey_df.iloc[0]['feature']})")

print(f"\n騎手関連特徴量は全体の{jockey_contribution:.2f}%の予測貢献度を持っています。")
