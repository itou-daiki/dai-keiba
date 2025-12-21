# 🏇 AI期待度算出方法の分析と改善提案

## 📊 現状の分析

### 現在のEV（期待値）計算式

```python
EV = (AI確率 × 印の重み × オッズ) - 1.0

# 印の重み
◎ = 1.5
◯ = 1.2
▲ = 1.1
△ = 1.05
✕ = 0.0

# 安全フィルタ
if AI確率 < 8%:
    EV = -1.0
```

---

## ⚠️ 問題点

### 1. **中央競馬と地方競馬を区別していない**

現在のモデルは、JRA（中央競馬）とNAR（地方競馬）を区別せずに学習・予測しています。

**中央競馬と地方競馬の主な違い:**

| 項目 | 中央競馬（JRA） | 地方競馬（NAR） |
|------|----------------|----------------|
| **レベル** | 高い（全国トップ） | 多様（地域差大） |
| **主要コース** | 芝・ダート混在 | ダート中心 |
| **開催形態** | 昼間のみ | ナイター開催多数 |
| **オッズ傾向** | 人気馬堅い | 人気薄波乱多い |
| **賞金額** | 高額 | 比較的低額 |
| **馬のレベル** | トップクラス | 中央落ち馬も多い |
| **騎手** | 一流騎手集中 | 地域の騎手 |

### 2. **一律の印補正係数**

中央と地方では予想の信頼度が異なるはずだが、同じ係数を使用

### 3. **安全フィルタの閾値が一律**

8%という閾値が中央・地方両方に適切とは限らない

---

## ✅ 改善提案

### 提案1: 会場による中央/地方の自動判定

#### 実装内容

```python
# ml/race_classifier.py (新規作成)

# JRA中央競馬の会場リスト
JRA_VENUES = [
    '札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉'
]

# 地方競馬の主要会場
NAR_VENUES = [
    '門別', '盛岡', '水沢', '浦和', '船橋', '大井', '川崎', '金沢',
    '笠松', '名古屋', '園田', '姫路', '高知', '佐賀'
]

def classify_race_type(venue):
    """
    会場から中央/地方を判定

    Returns:
        str: 'JRA' or 'NAR'
    """
    if venue in JRA_VENUES:
        return 'JRA'
    elif venue in NAR_VENUES:
        return 'NAR'
    else:
        # 不明な場合は会場名から推測
        # JRAは漢字2文字が多い
        if len(venue) == 2:
            return 'JRA'
        return 'NAR'
```

---

### 提案2: 中央/地方別の特徴量追加

#### 実装内容

```python
# ml/feature_engineering.py に追加

def add_race_type_features(df):
    """
    中央/地方の特徴量を追加
    """
    from race_classifier import classify_race_type

    # 1. レースタイプを判定
    df['race_type'] = df['会場'].apply(classify_race_type)

    # 2. レースタイプコード（数値化）
    df['race_type_code'] = df['race_type'].map({'JRA': 1, 'NAR': 0})

    # 3. 中央/地方別の過去成績
    df['jra_win_rate'] = 0.0
    df['nar_win_rate'] = 0.0

    for i in range(1, 6):
        # 過去走のレース名から中央/地方を推測
        race_name_col = f'past_{i}_race_name'
        rank_col = f'past_{i}_rank'

        if race_name_col in df.columns and rank_col in df.columns:
            # JRAレースの判定（G1/G2/G3、重賞など）
            is_jra = df[race_name_col].astype(str).str.contains('G1|G2|G3|重賞|オープン', na=False)

            # JRA成績集計
            df.loc[is_jra & (df[rank_col] <= 3), 'jra_win_rate'] += 1

            # NAR成績集計
            df.loc[~is_jra & (df[rank_col] <= 3), 'nar_win_rate'] += 1

    # 平均化
    df['jra_win_rate'] = df['jra_win_rate'] / 5
    df['nar_win_rate'] = df['nar_win_rate'] / 5

    return df
```

---

### 提案3: 中央/地方別のEV計算式

#### 実装内容

```python
# public_app.py の EV計算部分を改善

def calculate_ev_advanced(ai_prob, odds, mark, race_type='JRA'):
    """
    中央/地方を考慮したEV計算

    Args:
        ai_prob: AI予測確率（0-1）
        odds: オッズ
        mark: 予想印
        race_type: 'JRA' or 'NAR'

    Returns:
        float: 期待値
    """
    # 1. 印の重みを中央/地方で変える
    if race_type == 'JRA':
        # 中央は信頼性高いので印の影響を抑える
        mark_weights = {
            "◎": 1.3,   # 1.5 → 1.3
            "◯": 1.15,  # 1.2 → 1.15
            "▲": 1.08,  # 1.1 → 1.08
            "△": 1.03,  # 1.05 → 1.03
            "✕": 0.0,
            "": 1.0
        }
        safety_threshold = 0.08  # 8%

    else:  # NAR
        # 地方は波乱が多いので印の重みを大きく
        mark_weights = {
            "◎": 1.8,   # 1.5 → 1.8
            "◯": 1.4,   # 1.2 → 1.4
            "▲": 1.2,   # 1.1 → 1.2
            "△": 1.1,   # 1.05 → 1.1
            "✕": 0.0,
            "": 1.0
        }
        safety_threshold = 0.05  # 5%（地方は低確率でも狙う価値あり）

    # 2. 安全フィルタ
    if ai_prob < safety_threshold:
        return -1.0

    # 3. EV計算
    weight = mark_weights.get(mark, 1.0)

    # 4. 中央/地方でAI確率の信頼度を調整
    if race_type == 'JRA':
        # 中央はAI予測をそのまま使用
        adjusted_prob = ai_prob
    else:
        # 地方は予測の不確実性を考慮して調整
        # 高い確率は少し下げ、低い確率は少し上げる
        adjusted_prob = ai_prob * 0.9 + 0.05

    ev = (adjusted_prob * weight * odds) - 1.0

    return ev
```

---

### 提案4: 中央/地方別モデルの構築（高度版）

#### 実装内容

```python
# ml/train_dual_model.py (新規作成)

def train_separate_models(data_path):
    """
    中央と地方で別々のモデルを学習
    """
    df = pd.read_csv(data_path)

    # 中央/地方に分割
    jra_data = df[df['race_type'] == 'JRA']
    nar_data = df[df['race_type'] == 'NAR']

    print(f"JRAデータ: {len(jra_data)}行")
    print(f"NARデータ: {len(nar_data)}行")

    # 中央モデル学習
    jra_model = train_model(jra_data, model_name='lgbm_jra_model.pkl')

    # 地方モデル学習
    nar_model = train_model(nar_data, model_name='lgbm_nar_model.pkl')

    return jra_model, nar_model


def predict_with_dual_model(race_data, venue):
    """
    中央/地方に応じて適切なモデルで予測
    """
    race_type = classify_race_type(venue)

    if race_type == 'JRA':
        model = load_model('ml/models/lgbm_jra_model.pkl')
    else:
        model = load_model('ml/models/lgbm_nar_model.pkl')

    predictions = model.predict(race_data)

    return predictions, race_type
```

---

### 提案5: 地方競馬特有の特徴量追加

#### 実装内容

```python
# 地方競馬で重要な特徴量

def add_nar_specific_features(df):
    """
    地方競馬特有の特徴量を追加
    """
    # 1. ナイター開催フラグ
    # レース時刻が18時以降の場合
    df['is_night_race'] = 0  # 実際にはレース時刻データが必要

    # 2. 中央からの転入馬フラグ
    # 過去にJRAレースに出走していた馬
    df['is_jra_transfer'] = 0
    for i in range(1, 6):
        race_name_col = f'past_{i}_race_name'
        if race_name_col in df.columns:
            is_jra_past = df[race_name_col].astype(str).str.contains('G1|G2|G3|重賞', na=False)
            df.loc[is_jra_past, 'is_jra_transfer'] = 1

    # 3. 地方競馬での連勝数
    df['nar_winning_streak'] = 0
    consecutive_wins = 0
    for i in range(1, 6):
        rank_col = f'past_{i}_rank'
        race_name_col = f'past_{i}_race_name'

        if rank_col in df.columns and race_name_col in df.columns:
            is_nar = ~df[race_name_col].astype(str).str.contains('G1|G2|G3|重賞', na=False)
            is_win = df[rank_col] == 1

            # NAR1着なら連勝カウント
            if is_nar.any() and is_win.any():
                consecutive_wins += 1
            else:
                break

    df['nar_winning_streak'] = consecutive_wins

    return df
```

---

## 📊 期待される効果

| 改善項目 | 期待される効果 |
|---------|--------------|
| **中央/地方の区別** | 予測精度 +5〜8% |
| **別モデル構築** | 各モデルの精度 +10〜15% |
| **EV計算の最適化** | 回収率 +3〜5% |
| **地方特有特徴量** | 地方レースの的中率 +7〜10% |

---

## 🚀 実装優先度

### 最優先（今すぐ実装）
1. ✅ **会場による中央/地方判定**
2. ✅ **中央/地方別EV計算式**
3. ✅ **race_type特徴量の追加**

### 高優先（次のステップ）
4. ⏳ **中央/地方別の過去成績特徴量**
5. ⏳ **地方競馬特有の特徴量**

### 中優先（余力があれば）
6. ⏳ **中央/地方別モデルの構築**

---

## ✅ 検証方法

### 実装後の検証手順

1. **中央競馬での精度確認**
   ```python
   # JRAレースのみでバックテスト
   jra_races = df[df['race_type'] == 'JRA']
   result = run_backtest(model, jra_races, betting_strategy='ev_positive')
   print(f"JRA 回収率: {result['recovery_rate']}%")
   ```

2. **地方競馬での精度確認**
   ```python
   # NARレースのみでバックテスト
   nar_races = df[df['race_type'] == 'NAR']
   result = run_backtest(model, nar_races, betting_strategy='ev_positive')
   print(f"NAR 回収率: {result['recovery_rate']}%")
   ```

3. **中央/地方の予測精度比較**
   ```python
   from ml.train_model import train_with_cross_validation

   # 中央のみ
   jra_cv = train_with_cross_validation(jra_processed_data)
   print(f"JRA AUC: {jra_cv['mean_auc']:.4f}")

   # 地方のみ
   nar_cv = train_with_cross_validation(nar_processed_data)
   print(f"NAR AUC: {nar_cv['mean_auc']:.4f}")
   ```

---

## 📝 まとめ

### 現状の問題

- ❌ 中央と地方を区別せずに予測
- ❌ EV計算が一律
- ❌ 地方競馬特有の要素を考慮していない

### 改善後

- ✅ 中央と地方を自動判定
- ✅ それぞれに最適化されたEV計算
- ✅ 中央/地方別の特徴量
- ✅ （オプション）中央/地方別モデル

これにより、**より精度の高い予想**と**回収率の向上**が期待できます！
