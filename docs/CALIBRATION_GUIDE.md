# 🎯 確率較正（Probability Calibration）ガイド

## 概要

確率較正は、機械学習モデルの予測確率を**実際の発生確率に近づける**技術です。

### なぜ必要か？

LightGBMなどのブースティングモデルは、**識別性能（AUC）は高いが、確率が歪んでいる**ことがあります。

**例：**
- モデルが「1着確率10%」と予測
- 実際には100レース中15回勝つ（実確率15%）
- → 5%のズレ = **期待値計算が狂う**

---

## 現在のモデルの状態

### JRAモデル

```json
{
  "calibrated": false,
  "brier_score": 0.0567,  // 低いほど良い（較正で改善可能）
  "auc": 0.8909           // 識別性能は優秀
}
```

**問題点:**
- 未較正のため、確率にバイアスがある可能性
- EV計算の精度に影響

---

## 較正の効果（期待値）

### Brier Scoreの改善

```
較正前: 0.0567
較正後: 0.0400-0.0500（10-30%改善）
```

### EV計算の精度向上

```python
# 較正前
ai_prob = 0.10（予測）
real_prob = 0.15（実際）
odds = 10.0
EV = 0.10 × 10.0 - 1.0 = 0.0  # 買わない判断
# → 本当はEV = 0.15 × 10.0 - 1.0 = 0.5（買うべき）

# 較正後
ai_prob = 0.15（較正済み）
EV = 0.15 × 10.0 - 1.0 = 0.5  # 正しい判断
```

---

## 較正の有効化手順

### 方法1: 管理画面から（推奨）

1. `streamlit run app/admin_app.py` で管理画面を起動
2. 「機械学習」タブを選択
3. **「確率較正を実行」にチェック**
4. 「学習開始」ボタンをクリック

```
処理時間: 通常の学習 + 5-10分
```

### 方法2: コマンドラインから

```bash
cd ml
python train_model.py --calibrate
```

### 方法3: Pythonスクリプトから

```python
from ml.train_model import train_and_save_model

train_and_save_model(
    data_path="data/processed/processed_data.csv",
    model_path="ml/models/lgbm_model.pkl",
    calibrate=True,  # ← 較正を有効化
    use_timeseries_split=True,
    n_folds=5
)
```

---

## 較正の仕組み

### 使用アルゴリズム: Isotonic Regression

```python
from sklearn.isotonic import IsotonicRegression

# 1. モデルで予測確率を計算
raw_probs = model.predict(X_test)

# 2. Isotonic Regressionで較正
calibrator = IsotonicRegression(out_of_bounds='clip')
calibrated_probs = calibrator.fit_transform(raw_probs, y_test)
```

**特徴:**
- 単調性を保証（確率が逆転しない）
- ノンパラメトリック（柔軟な較正曲線）
- 過学習しにくい

### 較正曲線の例

```
実際の1着率
│  /
│ /
│/     ← 理想（完璧な較正）
│
│      •••••
│   •••
│•••
└──────────── 予測確率
```

- 点線が理想のy=x
- ●が実際のモデル
- 較正により●を点線に近づける

---

## 較正後の検証

### 1. メタデータの確認

```bash
cat ml/models/lgbm_model_meta.json | grep calibrated
```

```json
{
  "training_config": {
    "calibrated": true  // ← trueになっていればOK
  }
}
```

### 2. Brier Scoreの改善確認

```python
import json

with open('ml/models/lgbm_model_meta.json') as f:
    meta = json.load(f)

print(f"Brier Score: {meta['performance']['brier_score']:.4f}")
# 較正前: 0.0567
# 較正後: 0.0400-0.0500 （目安）
```

### 3. 較正曲線の可視化

```bash
python ml/calibration_plot.py \
  --model ml/models/lgbm_model.pkl \
  --data data/processed/processed_data.csv
```

出力: `ml/visualizations/calibration_plot.png`

---

## 注意事項

### 較正が不要なケース

1. **データ量が少ない（<1000件）**
   - 較正が過学習を起こす可能性
   - まずデータ収集を優先

2. **Brier Scoreが既に優秀（<0.05）**
   - 較正の余地が小さい
   - 計算コストのみ増加

### JRA vs NAR

- **JRA:** データ量が多い（142,350件）→ 較正推奨
- **NAR:** データ量次第
  - 10,000件以上: 較正推奨
  - 3,000-10,000件: 任意
  - 3,000件未満: 非推奨

---

## トラブルシューティング

### Q1. 較正後、AUCが下がった

**A:** 正常です。較正は識別性能（AUC）ではなく、確率精度（Brier Score）を改善します。

```
AUC: 0.89 → 0.88（微減は許容範囲）
Brier: 0.057 → 0.045（改善）
```

### Q2. 較正に時間がかかりすぎる

**A:** データ量が多い場合、サンプリングを検討

```python
# 100,000件から20,000件にサンプリング
sample_size = min(20000, len(X_test))
X_sample = X_test.sample(n=sample_size, random_state=42)
y_sample = y_test.loc[X_sample.index]

calibrator.fit(raw_probs[X_sample.index], y_sample)
```

### Q3. NAR未較正時の補正が適用されている

**A:** `public_app.py:1129-1138` の一律補正は削除を検討

較正済みモデルでは不要なため、以下のように修正：

```python
# 削除（較正済みなら不要）
# if race_type == 'NAR' and not is_calibrated:
#     new_p = p * 0.9 + 0.05
```

---

## 推奨ワークフロー

### 初回学習時

1. まず**較正なし**で学習
2. Brier Scoreを確認
3. Brier > 0.05 なら較正版を再学習
4. 較正前後を比較し、良い方を採用

### 定期更新時

1. 月1回、較正ありで再学習
2. バックテストで実性能を検証
3. Brier Scoreをモニタリング

---

## まとめ

✅ **較正のメリット**
- EV計算の精度向上（最重要）
- Brier Score 10-30%改善
- 確率の信頼性向上

⚠️ **注意点**
- データ量が少ないと逆効果
- 計算時間が5-10分増加
- AUCは改善しない（識別性能は別）

🎯 **推奨アクション**
1. 現在のJRAモデルを較正版で再学習
2. Brier Scoreを比較
3. バックテストで実際のEV精度を検証

---

**作成日:** 2025-12-28
**対象:** dai-keiba プロジェクト
**参考:** `ml/train_model.py`, `ml/calibration_plot.py`
