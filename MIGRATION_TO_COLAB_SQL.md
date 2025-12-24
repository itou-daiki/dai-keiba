# 🔄 Colab + SQL アーキテクチャへの移行ガイド

## 📋 概要

従来の「管理ページでスクレイピング + 学習」から、「Colabでスクレイピング + 前処理、管理ページで学習のみ」に移行します。

### 変更前のアーキテクチャ
```
管理ページ
├─ スクレイピング → CSV保存
├─ 特徴量生成 → processed_data.csv
└─ モデル学習 → models/*.pkl

公開ページ
├─ CSV読み込み
└─ 予測表示
```

### 変更後のアーキテクチャ
```
Google Colab（データ処理層）
├─ スクレイピング
├─ 特徴量生成
└─ SQLite保存 → keiba_data.db

管理ページ（学習専用）
├─ SQLite読み込み
└─ モデル学習 → models/*.pkl

公開ページ（予測専用）
├─ SQLite読み込み
└─ 予測表示
```

---

## 🚀 移行手順

### ステップ1: Google Colabでデータ準備

1. **Google Colabを開く**
   ```
   https://colab.research.google.com/
   ```

2. **ノートブックをアップロード**
   - `colab_data_pipeline.ipynb` をアップロード
   - または、GitHubから直接開く

3. **必要なファイルをアップロード**
   - `scraper/` ディレクトリ
   - `ml/feature_engineering.py`
   - `ml/venue_characteristics.py`
   - `ml/run_style_analyzer.py`

4. **Google Driveをマウント**
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```

5. **すべてのセルを実行**
   - Runtime → Run all
   - スクレイピング〜SQL保存まで自動実行（数時間かかる場合あり）

6. **データベースをダウンロード**
   ```python
   from google.colab import files
   files.download('keiba_data.db')
   ```

### ステップ2: ローカル環境の準備

1. **データベースを配置**
   ```bash
   # プロジェクトルートに配置
   mv ~/Downloads/keiba_data.db /path/to/dai-keiba/
   ```

2. **データベースの確認**
   ```bash
   cd /path/to/dai-keiba
   python ml/db_helper.py keiba_data.db
   ```

   出力例:
   ```
   ============================================================
   データベース統計情報
   ============================================================

   📊 JRA:
      総レコード数: 63,780
      ユニークレース数: 4,500
      ユニーク馬数: 8,900
      データ期間: 2023-01-01 ～ 2025-12-24
      勝率: 7.23%
      鮮度: 最新（今日）

   📊 NAR:
      総レコード数: 29,504
      ユニークレース数: 2,100
      ユニーク馬数: 5,200
      データ期間: 2023-01-01 ～ 2025-12-24
      勝率: 9.63%
      鮮度: 最新（今日）
   ```

### ステップ3: 管理ページで学習

1. **管理ページ（簡素版）を起動**
   ```bash
   streamlit run scraper/admin_app_simple.py --server.port 8501
   ```

2. **データベースパスを確認**
   - サイドバーで `keiba_data.db` が選択されているか確認

3. **モードを選択**
   - JRA または NAR

4. **学習を実行**
   - 「学習開始」ボタンをクリック
   - ハイパーパラメータ最適化は任意（初回は不要）

5. **モデルが保存されたことを確認**
   ```bash
   ls -lh ml/models/
   # lgbm_model.pkl または lgbm_model_nar.pkl が生成される
   ```

### ステップ4: 公開ページで予測

1. **公開ページを起動**
   ```bash
   streamlit run public_app.py --server.port 8502
   ```

2. **データベースから予測**
   - 現在の `public_app.py` は自動的にSQLiteを使用するように更新されます

---

## 📝 public_app.py の主要な変更点

### 変更前（CSV版）
```python
# CSVからデータ読み込み
df = pd.read_csv('database.csv')
```

### 変更後（SQL版）
```python
# SQLiteからデータ読み込み
from ml.db_helper import KeibaDatabase

db = KeibaDatabase('keiba_data.db')
df = db.get_processed_data(mode='JRA')
```

### 具体的な修正箇所

1. **インポート追加**
   ```python
   # public_app.py の冒頭に追加
   from ml.db_helper import KeibaDatabase
   ```

2. **データ読み込みの変更**
   ```python
   # 従来のコード
   # if f'data_{race_id}' in st.session_state:
   #     df_display = st.session_state[f'data_{race_id}'].copy()

   # 新しいコード
   db = KeibaDatabase('keiba_data.db')
   df_display = db.get_race_data(race_id, mode=mode_val)
   ```

3. **データ新鮮度の取得**
   ```python
   # 従来のコード
   # freshness = get_data_freshness(mode=mode_val)

   # 新しいコード
   freshness = db.get_data_freshness(mode_val)
   ```

---

## 🔧 トラブルシューティング

### Q1: データベースファイルが見つかりません

**A:** Google Colabで生成した `keiba_data.db` をプロジェクトルートに配置してください。

```bash
# 確認
ls -lh keiba_data.db

# 存在しない場合、Colabで再実行
```

### Q2: テーブルが存在しません

**A:** Google Colabのノートブックが正しく実行されていません。

```bash
# テーブルの確認
sqlite3 keiba_data.db "SELECT name FROM sqlite_master WHERE type='table';"

# 期待される出力
# processed_data_jra
# processed_data_nar
```

### Q3: 特徴量の数が一致しません

**A:** Colabで `use_venue_features=True` を指定したか確認してください。

```python
# colab_data_pipeline.ipynb 内
USE_VENUE_FEATURES = True  # これが True になっているか確認
```

### Q4: データが古い

**A:** Google Colabで最新データを取得し、データベースを更新してください。

```bash
# 現在のデータ鮮度を確認
python ml/db_helper.py keiba_data.db

# Google Colabで最新データを取得して更新
```

---

## 📊 メリット

1. **✅ 処理の分離**: データ処理とモデル学習が分離され、管理が容易
2. **✅ スケーラビリティ**: Colabの無料GPUを活用可能
3. **✅ データ一元管理**: SQLiteで一元管理、複数アプリから参照可能
4. **✅ 再現性**: Colabノートブックで処理が再現可能
5. **✅ 高速化**: SQL インデックスにより高速なデータアクセス

---

## 🎯 次のステップ

1. **定期的なデータ更新**
   - 週1回、Google Colabで最新データを取得
   - `keiba_data.db` を更新

2. **モデルの再学習**
   - 新しいデータが1000件以上溜まったら再学習
   - 管理ページで「学習開始」

3. **自動化（オプション）**
   - Google Colab + Google Drive + Streamlit Cloud
   - GitHub Actions で自動更新

---

## 📚 参考資料

- Google Colab: https://colab.research.google.com/
- SQLite: https://www.sqlite.org/
- Streamlit: https://streamlit.io/

---

**最終更新**: 2025-12-24
