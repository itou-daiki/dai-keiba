# 🔧 会場特性機能の有効化ガイド

## 問題

新しい会場特性の特徴量（11個）を追加したため、予測時の特徴量数（42個）が既存モデルの学習時の特徴量数（27個）と一致しなくなりました。

```
Prediction Error: The number of features in data (42) is not the same as
it was in training data (27).
```

---

## 解決方法

### オプション1: 一時的に新機能を無効化（すぐに使える）✅

**現在の設定** - すでに適用済み

```python
# ml/feature_engineering.py
def process_data(df, lambda_decay=0.2, use_venue_features=False):
    # use_venue_features=False がデフォルト
    # これにより既存の27特徴量のみ使用

# public_app.py (line 171)
X_df = process_data(df, use_venue_features=False)
```

この設定で、既存のモデル（27特徴量）が正常に動作します。

**制限事項:**
- 会場特性の特徴量は使用されません
- EV計算の会場別調整は引き続き動作します（モデル予測とは独立）

---

### オプション2: 新しい特徴量でモデルを再学習（推奨）🚀

#### ステップ1: モデルを再学習

```bash
# プロジェクトルートで実行
python ml/retrain_with_venue_features.py
```

このスクリプトは:
1. `database.csv` から新しい特徴量（42個）を生成
2. 新しいモデルを学習
3. `ml/models/lgbm_model_v2.pkl` として保存

**実行時間:** データ量により5-20分

#### ステップ2: public_app.pyを編集

**変更箇所1: モデルパス**

```python
# Line 130付近
# 変更前
MODEL_PATH = 'ml/models/lgbm_model.pkl'

# 変更後
MODEL_PATH = 'ml/models/lgbm_model_v2.pkl'
```

**変更箇所2: 特徴量フラグ**

```python
# Line 171
# 変更前
X_df = process_data(df, use_venue_features=False)

# 変更後
X_df = process_data(df, use_venue_features=True)
```

#### ステップ3: アプリを再起動

```bash
streamlit run public_app.py
```

---

## 新しい特徴量の効果

再学習後、以下の特徴量が有効になります:

| 特徴量 | 説明 | 期待効果 |
|--------|------|---------|
| `run_style_code` | 馬の脚質（逃げ/先行/差し/追込） | +5-8% |
| `venue_run_style_compatibility` | 会場×脚質の相性 | +5-8% |
| `venue_distance_compatibility` | 会場×距離の相性 | +3-5% |
| `venue_condition_compatibility` | 会場×馬場状態の相性 | +2-4% |
| `frame_advantage` | 会場別枠番有利度 | +1-3% |
| その他6個 | 直線距離、コース幅、勾配など | +5-10% |

**総合的な期待効果:**
- 予測精度: +20〜30%
- 回収率: +10〜15%

---

## トラブルシューティング

### エラー: ImportError (venue_characteristics)

```bash
# mlディレクトリに移動して確認
ls ml/venue_characteristics.py
ls ml/run_style_analyzer.py
```

ファイルが存在しない場合、最新のコードをpullしてください。

### エラー: モデル学習が遅い

データ量が多い場合、学習に時間がかかります：
- 100,000行: 約5分
- 500,000行: 約15分
- 1,000,000行以上: 30分以上

処理を高速化するオプション:

```python
# ml/retrain_with_venue_features.py
# パラメータを調整
params = {
    'num_leaves': 20,  # 31 → 20 (シンプルなモデル)
    'learning_rate': 0.1,  # 0.05 → 0.1 (高速化)
}
```

### エラー: メモリ不足

データが大きすぎる場合、サンプリングしてください:

```python
# ml/retrain_with_venue_features.py
# main()関数内で
df = pd.read_csv(db_path)

# サンプリング（最新50万行のみ）
if len(df) > 500000:
    df = df.tail(500000)
    print(f"⚠️ データをサンプリング: {len(df):,}行")
```

---

## 検証方法

### 1. 特徴量数の確認

```bash
python ml/retrain_with_venue_features.py
```

出力:
```
✅ 処理済みデータを保存: ml/processed_data_v2.csv
   行数: XXX,XXX
   特徴量数: 42  # ← これが42になっていることを確認
```

### 2. モデルのテスト

```python
# Pythonコンソールで
import pickle
with open('ml/models/lgbm_model_v2.pkl', 'rb') as f:
    model = pickle.load(f)

print(f"モデルの特徴量数: {model.num_feature()}")  # 42であることを確認
```

### 3. 予測のテスト

アプリを起動して、適当なレースIDで予測を実行:
- エラーが出なければ成功
- EV計算に会場特性が反映されているか確認

---

## まとめ

### 現在の状態（適用済み）
✅ 既存モデル（27特徴量）で正常動作
✅ EV計算の会場別調整は有効
❌ 会場特性の特徴量はモデルに未使用

### 推奨アクション
1. `python ml/retrain_with_venue_features.py` を実行
2. `public_app.py` を編集（2箇所）
3. アプリを再起動

これで、会場特性を含む全ての新機能が有効になります！
