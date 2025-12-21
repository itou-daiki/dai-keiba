# スクレイピング機能 検証ガイド

## 📋 検証の目的

このガイドでは、実装されたスクレイピング機能と新しい特徴量が正しく動作するか確認します。

---

## 🚀 クイックスタート

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 自動テストの実行

```bash
python tests/test_scraping.py
```

---

## 📝 手動検証手順

### ステップ1: データベースの確認

```bash
# データベースファイルの存在確認
ls -lh database.csv

# データ内容の確認（最初の5行）
head -5 database.csv
```

**期待される結果:**
- ファイルサイズ: 約300KB以上
- 列数: 約90列（日付、会場、レース名、馬名、horse_id、過去走データなど）
- 行数: 656行（ヘッダー含む）

---

### ステップ2: 特徴量生成のテスト

```bash
# 特徴量を再生成
python ml/feature_engineering.py
```

**期待される結果:**
```
Loading database.csv...
Saved processed data to ml/processed_data.csv (655 rows)
```

**確認ポイント:**
```bash
# 生成された特徴量ファイルを確認
ls -lh ml/processed_data.csv

# 特徴量の列名を確認（新しい12個の特徴量が含まれているはず）
python -c "
import pandas as pd
df = pd.read_csv('ml/processed_data.csv')
print('総特徴量数:', len(df.columns))

# 新規特徴量をチェック
new_features = [
    'turf_compatibility',
    'dirt_compatibility',
    'good_condition_avg',
    'heavy_condition_avg',
    'distance_compatibility',
    'is_rest_comeback',
    'interval_category',
    'is_consecutive',
    'jockey_compatibility',
    'race_class',
    'is_graded',
    'age_limit'
]

existing = [f for f in new_features if f in df.columns]
print(f'新規特徴量: {len(existing)}/{len(new_features)} 存在')
print('存在する新規特徴量:', existing)
"
```

---

### ステップ3: スクレイピング機能のテスト

#### 3-1. 単一レースのスクレイピング

```python
# Python対話モードで実行
python

>>> from scraper.auto_scraper import scrape_race_data
>>>
>>> # テスト用のレースID（最新のレースIDに変更してください）
>>> race_id = "202506050101"
>>>
>>> # スクレイピング実行
>>> result = scrape_race_data(race_id)
>>>
>>> # 結果確認
>>> if result:
>>>     print("✅ スクレイピング成功")
>>>     print(f"取得データ型: {type(result)}")
>>> else:
>>>     print("⚠️ データ取得失敗（レースが存在しないか、ネットワークエラー）")
```

#### 3-2. 今日のレーススケジュール取得

```python
>>> from scraper.auto_scraper import scrape_todays_schedule
>>>
>>> # 今後8日分のレース取得
>>> todays_data = scrape_todays_schedule()
>>>
>>> # 結果確認
>>> import json
>>> print(json.dumps(todays_data, ensure_ascii=False, indent=2)[:500])
```

---

### ステップ4: オッズ取得機能のテスト

```python
>>> from scraper.odds_scraper import OddsScraper
>>>
>>> scraper = OddsScraper()
>>>
>>> # テスト用のレースID
>>> race_id = "202506050101"
>>>
>>> # オッズ取得（リトライ処理付き）
>>> odds = scraper.get_odds_multi_source(race_id)
>>>
>>> # 結果確認
>>> if odds:
>>>     print("✅ オッズ取得成功")
>>>     for umaban, odd in list(odds.items())[:5]:
>>>         print(f"  馬番 {umaban}: {odd}倍")
>>> else:
>>>     print("⚠️ オッズ取得失敗")
```

---

### ステップ5: モデル学習とクロスバリデーション

#### 5-1. 通常学習

```bash
python ml/train_model.py
```

#### 5-2. クロスバリデーション

```python
python

>>> from ml.train_model import train_with_cross_validation
>>>
>>> # 5分割クロスバリデーション実行
>>> result = train_with_cross_validation('ml/processed_data.csv', n_splits=5)
>>>
>>> # 結果表示
>>> print(f"平均AUC: {result['mean_auc']:.4f} ± {result['std_auc']:.4f}")
>>> print(f"平均精度: {result['mean_accuracy']:.4f} ± {result['std_accuracy']:.4f}")
```

**期待される結果:**
- 平均AUC: 0.70以上
- 標準偏差: 0.05以下（安定したモデル）

---

### ステップ6: バックテストの実行

```python
>>> from ml.backtest import run_backtest, compare_strategies
>>>
>>> # 単一戦略のバックテスト
>>> result = run_backtest(
...     'ml/models/lgbm_model.pkl',
...     'ml/processed_data.csv',
...     betting_strategy='ev_positive'
... )
>>>
>>> # 結果表示
>>> print(f"的中率: {result['hit_rate']:.1f}%")
>>> print(f"回収率: {result['recovery_rate']:.1f}%")
>>> print(f"ROI: {result['roi']:.1f}%")
>>>
>>> # 複数戦略の比較
>>> comparison = compare_strategies(
...     'ml/models/lgbm_model.pkl',
...     'ml/processed_data.csv'
... )
```

---

## ✅ 検証チェックリスト

### 基本動作

- [ ] `pip install -r requirements.txt` でパッケージがインストールできる
- [ ] `database.csv` が存在し、データが入っている
- [ ] `ml/feature_engineering.py` が正常に実行できる
- [ ] `ml/processed_data.csv` に29個の特徴量が生成される

### スクレイピング機能

- [ ] `scrape_race_data()` でレース結果が取得できる
- [ ] `scrape_todays_schedule()` で今後のレーススケジュールが取得できる
- [ ] 馬の過去走データ（5走分）が取得できる
- [ ] オッズ取得がリトライ処理で安定して動作する

### 新規特徴量

- [ ] `turf_compatibility` - 芝適性が計算される
- [ ] `dirt_compatibility` - ダート適性が計算される
- [ ] `jockey_compatibility` - 騎手相性が計算される
- [ ] `is_rest_comeback` - 休養明けフラグが設定される
- [ ] `race_class` - レースクラスが数値化される

### モデル学習

- [ ] クロスバリデーションが実行できる
- [ ] 時系列分割による学習が実行できる
- [ ] モデルが `ml/models/lgbm_model.pkl` に保存される
- [ ] MLflowに実験結果が記録される

### バックテスト

- [ ] バックテストが実行できる
- [ ] 的中率、回収率、ROIが計算される
- [ ] 複数戦略の比較ができる

---

## 🐛 トラブルシューティング

### エラー: `ModuleNotFoundError: No module named 'pandas'`

**原因:** 依存パッケージがインストールされていない

**解決策:**
```bash
pip install -r requirements.txt
```

---

### エラー: `FileNotFoundError: database.csv not found`

**原因:** データベースファイルが存在しない

**解決策:**
```bash
# 管理画面からスクレイピングを実行
streamlit run scraper/admin_app.py
```

---

### エラー: オッズ取得が常に失敗する

**原因:** ネットワークエラー、またはnetkeiba.comへのアクセス制限

**解決策:**
1. インターネット接続を確認
2. しばらく時間を置いてから再試行
3. VPNを使用している場合は一時的にオフにする

---

### 警告: 特徴量の値がすべて10.0（デフォルト値）

**原因:** 過去走データが不足している

**解決策:**
- より多くのレースデータをスクレイピング
- `database.csv` に過去走データが含まれているか確認

---

## 📊 期待される性能指標

実装された改善により、以下の性能向上が期待されます：

| 指標 | 改善前 | 改善後（期待値） |
|------|--------|-----------------|
| 特徴量数 | 17個 | 29個 (+70%) |
| 予測精度（AUC） | 0.65-0.70 | 0.70-0.80 (+5-10%) |
| オッズ取得成功率 | 60% | 95%+ |
| クエリ速度（SQLite使用時） | - | 10倍以上高速化 |

---

## 🔄 次のステップ

検証が完了したら、以下を実行してください：

1. **データ量を増やす**: 過去2〜3年分のスクレイピングを実行
   ```bash
   # 管理画面から実行
   streamlit run scraper/admin_app.py
   ```

2. **モデルを再学習**: 新しい特徴量で学習
   ```bash
   python ml/feature_engineering.py
   python ml/train_model.py
   ```

3. **バックテストで検証**: 実際の収支をシミュレーション
   ```python
   from ml.backtest import compare_strategies
   compare_strategies('ml/models/lgbm_model.pkl', 'ml/processed_data.csv')
   ```

4. **本番環境で運用**: 公開画面で予想を開始
   ```bash
   streamlit run public_app.py
   ```

---

## 📞 サポート

問題が解決しない場合は、以下のファイルを確認してください：

- `IMPROVEMENTS.md` - 実装内容の詳細
- `tests/test_scraping.py` - 自動テストスクリプト
- 各モジュールのdocstring

エラーログと一緒に、実行環境の情報も記録してください：
```bash
python --version
pip list | grep -E "(pandas|lightgbm|scikit-learn)"
```
