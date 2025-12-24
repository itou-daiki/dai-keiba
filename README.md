# 🏇 AI競馬予想 EVシステム (AI Horse Racing EV System)

## 📌 概要
本アプリケーションは、**LightGBM**を用いた機械学習モデルにより、中央競馬（JRA）および地方競馬（NAR）のレース結果を予測し、期待値（Expected Value: EV）の高い馬を自動抽出する**AI予想システム**です。

**新アーキテクチャ（2025-12-24）:**
- 🔄 **Google Colab**: スクレイピング + 前処理 + 特徴量生成 → SQLite
- 🧠 **管理ページ**: モデル学習専用（スクレイピング機能は Colab に移行）
- 🌐 **公開ページ**: SQLiteから読み込み + 予測 + 表示

**主な特徴:**
- ✅ **TimeSeriesSplit**: Look-ahead bias完全排除
- ✅ **Optunaハイパーパラメータ最適化**: 自動で最適パラメータを探索
- ✅ **JRA/NAR別モデル**: 中央・地方それぞれに最適化
- ✅ **信頼度スコア**: 各予測の信頼性を0-100%で数値化
- ✅ **確率較正**: 予測確率と実際の確率を一致させる
- ✅ **SQLiteデータベース**: 高速アクセス、一元管理
- ✅ **Google Colab対応**: 無料GPUでスケーラブルな処理

## 🚀 クイックスタート

```bash
# 1. Google Colabでデータ準備
# colab_data_pipeline.ipynb をGoogle Colabで実行
# → keiba_data.db をダウンロード

# 2. データベースを配置
mv ~/Downloads/keiba_data.db ./

# 3. 管理ページでモデル学習
streamlit run app/admin_app.py --server.port 8501

# 4. 公開ページで予測
streamlit run app/public_app.py --server.port 8502
```

詳細は [MIGRATION_TO_COLAB_SQL.md](MIGRATION_TO_COLAB_SQL.md) を参照してください。

---

## 🏗️ システム構成 & アーキテクチャ

システムは大きく分けて以下の2つのアプリケーションと、バックエンドのMLパイプラインで構成されています。

### 1. 🛠️ 管理アプリケーション (`app/admin_app.py`)

**役割**: データ収集、モデル学習、運用管理

#### スクレイピング機能
- **データソース**: `netkeiba.com` からレース結果を自動収集
- **高速化**: 馬の過去データをメモリキャッシュ（N+1問題解消）
- **対応範囲**:
  - JRA（中央競馬）: `database.csv`
  - NAR（地方競馬）: `database_nar.csv`
- **収集データ**:
  - レース基本情報（日付、会場、距離、馬場状態、天気）
  - 出走馬情報（馬名、枠番、馬番、年齢、斤量、騎手）
  - 過去走履歴（最大全履歴、着順、タイム、上がり3F、通過順、馬体重、オッズ）
  - 結果情報（着順、走破タイム）

#### MLOps機能
- **モデル学習**: 最新データで自動学習（JRA/NAR別々）
- **ハイパーパラメータ最適化**: Optunaによる自動チューニング（50-100試行）
- **実験管理**: MLflowで学習履歴を記録・可視化
- **性能評価**: TimeSeriesSplit 5-foldクロスバリデーション

---

## 🎯 管理ページでの学習処理の実態

### 学習ボタンを押したときの処理フロー

```
[学習開始] ボタン押下
    ↓
1. データ読み込み
    ├─ database.csv (JRA) または database_nar.csv (NAR)
    ├─ データ量チェック（最低100件、推奨5000件以上）
    └─ 勝率チェック（正常範囲: 5-10%）
    ↓
2. データ品質検証（P1-4実装）
    ├─ 重複チェック（race_id + 馬番）
    ├─ 欠損値チェック
    ├─ 外れ値検出（IQR法）
    └─ ログ出力 → ml/training.log
    ↓
3. 特徴量エンジニアリング
    ├─ ml/feature_engineering.py 実行
    ├─ 時間減衰加重平均（過去5走）
    │   └─ Weight = exp(-0.5 * (i-1))  # 直近ほど重視
    ├─ 騎手相性、距離適性、コース適性の計算
    ├─ 芝/ダート適性の分離
    └─ processed_data.csv / processed_data_nar.csv 生成
    ↓
4. Optunaハイパーパラメータ最適化（オプション）
    ├─ n_trials回（デフォルト50回）の試行
    ├─ TimeSeriesSplit 3-foldで各試行を評価
    ├─ 最適化するパラメータ（12個）:
    │   ├─ num_leaves: 20-150
    │   ├─ max_depth: 3-12
    │   ├─ learning_rate: 0.005-0.2（対数スケール）
    │   ├─ feature_fraction: 0.5-1.0
    │   ├─ bagging_fraction: 0.5-1.0
    │   ├─ bagging_freq: 1-10
    │   ├─ min_child_samples: 5-100
    │   ├─ min_gain_to_split: 0.0-1.0
    │   ├─ lambda_l1: 1e-8～10.0（L1正則化）
    │   ├─ lambda_l2: 1e-8～10.0（L2正則化）
    │   └─ scale_pos_weight: 動的計算（クラス不均衡対応）
    ├─ TPESampler（効率的探索）
    ├─ MedianPruner（無駄な試行の早期終了）
    └─ 最良パラメータを選択
    ↓
5. TimeSeriesSplit 5-fold クロスバリデーション（P0-1実装）
    ├─ データを日付順にソート
    ├─ 5分割で評価:
    │   Fold 1: [Train: 0-20%] → [Test: 20-40%]
    │   Fold 2: [Train: 0-40%] → [Test: 40-60%]
    │   Fold 3: [Train: 0-60%] → [Test: 60-80%]
    │   Fold 4: [Train: 0-80%] → [Test: 80-90%]
    │   Fold 5: [Train: 0-90%] → [Test: 90-100%]
    ├─ 各foldで評価指標を計算:
    │   ├─ AUC (Area Under Curve)
    │   ├─ Accuracy
    │   ├─ Precision, Recall, F1 Score
    │   ├─ Brier Score（確率精度）
    │   └─ Log Loss
    └─ 平均±標準偏差を算出
    ↓
6. 最終モデルの訓練（P0-3改善）
    ├─ CVで評価済み → 全データで学習
    ├─ 学習データ: 100%（旧: 80%）
    ├─ LightGBMパラメータ:
    │   ├─ objective: 'binary'
    │   ├─ metric: 'auc'
    │   ├─ boosting_type: 'gbdt'
    │   ├─ num_boost_round: 300
    │   ├─ early_stopping_rounds: 30
    │   └─ 最適化されたパラメータ（Optuna使用時）
    └─ Best iteration で学習完了
    ↓
7. 最適閾値の探索（P0-2実装）
    ├─ 0.05～0.95の範囲を0.05刻みでスキャン
    ├─ F1スコアを最大化する閾値を発見
    ├─ デフォルト0.5から最適値へ変更
    │   例: 勝率10%のデータ → 最適閾値0.15
    └─ メタデータに記録
    ↓
8. 確率較正（オプション、P1-3実装）
    ├─ Isotonic Regression使用
    ├─ 予測確率と実際の確率のズレを修正
    ├─ Brier Score改善（10-30%）
    └─ 較正済みモデルを生成
    ↓
9. モデル保存
    ├─ ml/models/lgbm_model.pkl（JRA）
    ├─ ml/models/lgbm_model_nar.pkl（NAR）
    ├─ メタデータJSON（_meta.json）:
    │   ├─ 訓練日時
    │   ├─ 性能指標（AUC, F1, Brier Score等）
    │   ├─ CV結果（mean ± std）
    │   ├─ ハイパーパラメータ
    │   ├─ 最適閾値
    │   ├─ データ統計（レコード数、勝率）
    │   ├─ 特徴量リスト
    │   └─ 警告メッセージ
    └─ MLflowに記録
    ↓
10. 完了
    └─ ログに性能指標を出力
```

### 目的変数（ターゲット）

**現在**: `target_win`（1着のみ）

```python
# P0-3: target_winへの統一（EVと整合）
target_col = 'target_win'  # rank == 1 のとき1、それ以外0
```

**理由**: EV計算は単勝オッズを使用するため、1着確率と整合させる必要がある。

### 学習時間の目安

| データ量 | Optuna無し | Optuna 50試行 | Optuna 100試行 |
|---------|-----------|--------------|---------------|
| 500件 | 10秒 | 2分 | 4分 |
| 1000件 | 20秒 | 4分 | 8分 |
| 5000件 | 2分 | 15分 | 30分 |
| 10000件 | 5分 | 40分 | 80分 |

---

## 📊 公開ページでの計算処理の実態

### レース分析ボタンを押したときの処理フロー

```
[レース分析] ボタン押下
    ↓
1. レースデータ取得
    ├─ todays_data.json / todays_data_nar.json 読み込み
    ├─ 選択されたrace_idのデータを抽出
    └─ 出走馬リスト取得（馬名、枠番、馬番、年齢、騎手等）
    ↓
2. 特徴量エンジニアリング（予測用）
    ├─ ml/feature_engineering.py の関数を呼び出し
    ├─ 各馬の過去走データから特徴量を計算:
    │   ├─ 時間減衰加重平均（過去5走）
    │   │   ├─ weighted_avg_rank（加重平均着順）
    │   │   ├─ weighted_avg_speed（加重平均スピード）
    │   │   ├─ weighted_avg_agari3f（加重平均上がり3F）
    │   │   └─ weighted_avg_weight（加重平均馬体重）
    │   ├─ 騎手相性スコア（0-10）
    │   ├─ 距離適性スコア（0-10）
    │   ├─ 芝適性スコア（0-10）
    │   ├─ ダート適性スコア（0-10）
    │   └─ 会場ごとの適性（外枠有利度など）
    └─ X_df（特徴量データフレーム）生成
    ↓
3. JRA/NAR自動判定
    ├─ ユーザー選択モード（mode_val）を優先
    ├─ 会場名から自動判定（オーバーライド）:
    │   ├─ JRA会場: 札幌、函館、福島、新潟、東京、
    │   │             中山、中京、京都、阪神、小倉
    │   └─ NAR会場: それ以外（大井、川崎、船橋等）
    └─ 対応するモデルを選択
    ↓
4. モデル読み込み
    ├─ JRA: ml/models/lgbm_model.pkl
    ├─ NAR: ml/models/lgbm_model_nar.pkl
    ├─ メタデータ読み込み（_meta.json）:
    │   ├─ AUC, 訓練日時
    │   ├─ データ量、勝率
    │   └─ 最適閾値
    └─ データ新鮮度チェック（database.csv最終更新日）
    ↓
5. AI予測確率の計算
    ├─ メタカラムを除外:
    │   └─ ['馬名', 'horse_id', '枠', '馬番', 'race_id',
    │       'date', 'rank', '着順', 'target_win']
    ├─ 数値特徴量のみ選択
    ├─ 欠損値を0で埋める
    ├─ model.predict(X_pred)
    │   └─ 出力: 各馬の1着確率（0.0～1.0）
    └─ AI_Prob列に格納
    ↓
6. 信頼度スコアの計算（改善版）
    各馬ごとに:
    ├─ ベース信頼度 = モデルAUC × 100
    ├─ データ量ペナルティ:
    │   ├─ <1000件: -20
    │   ├─ <3000件: -8
    │   ├─ <5000件: -3
    │   └─ ≥5000件: 0
    ├─ 予測確率ボーナス:
    │   ├─ 0.5からの距離を計算
    │   ├─ 距離 × 2 - 0.25) × 40
    │   └─ 極端な予測（<0.05 or >0.95）: +12
    ├─ 適性スコアボーナス（新規追加）:
    │   ├─ 平均適性スコア:
    │   │   ├─ ≥9: +15（全て高適性）
    │   │   ├─ ≥7: +8
    │   │   ├─ ≥5: 0
    │   │   ├─ ≥3: -12
    │   │   └─ <3: -25（データ品質低い）
    │   └─ 最低スコアペナルティ:
    │       ├─ <3: -15（致命的不適性）
    │       └─ <5: -8
    └─ 信頼度 = max(20, min(95, 合計))
    ↓
7. EV（期待値）の計算
    各馬ごとに:
    ├─ JRA/NAR別パラメータ設定:
    │   ├─ JRA:
    │   │   ├─ 印の補正: ◎=1.3倍, ◯=1.15倍
    │   │   ├─ 安全フィルタ: AI確率8%未満は除外
    │   │   └─ 確率調整: なし（AI予測そのまま）
    │   └─ NAR:
    │       ├─ 印の補正: ◎=1.8倍, ◯=1.4倍（積極的）
    │       ├─ 安全フィルタ: AI確率5%未満は除外
    │       └─ 確率調整: p × 0.9 + 0.05（保守的）
    ├─ 安全フィルタチェック:
    │   └─ AI確率 < threshold → EV = -1.0（推奨外）
    ├─ 確率調整（NAR時のみ）:
    │   └─ adjusted_p = p × 0.9 + 0.05
    ├─ 印による補正:
    │   └─ adjusted_p × mark_weight
    ├─ 脚質相性補正（会場情報がある場合）:
    │   └─ adjusted_p × run_style_compatibility
    ├─ 枠番有利度補正（会場情報がある場合）:
    │   └─ 外枠/内枠の有利度を反映
    └─ EV計算:
        └─ EV = (adjusted_p × odds) - 1.0
    ↓
8. Kelly基準の計算（推奨投資比率）
    ├─ Kelly = (adjusted_p × odds - 1) / (odds - 1)
    ├─ 0以下の場合: 0%（投資非推奨）
    └─ 上限: 10%（過度な投資を防ぐ）
    ↓
9. 結果の表示
    ├─ データエディタで表示:
    │   ├─ 馬名、枠番、馬番、年齢
    │   ├─ AIスコア（%）
    │   ├─ 信頼度（%）← 新規追加
    │   ├─ 現在オッズ（編集可能）
    │   ├─ 予想印（編集可能）
    │   ├─ 騎手相性、コース適性、距離適性
    │   ├─ 期待値（EV）
    │   └─ 推奨度（Kelly%）
    ├─ EV > 0の馬を緑色ハイライト
    └─ データ新鮮度・モデル情報を表示
```

### EV算出ロジック詳細

**基本式:**
```
EV = (調整後AI確率 × 現在オッズ) - 1.0
```

**調整後AI確率の計算:**
```python
# 1. ベースAI確率
base_prob = model.predict(features)  # 0.0 ~ 1.0

# 2. JRA/NAR別の確率調整
if race_type == 'NAR':
    # 地方は不確実性が高いため保守的に
    adjusted_prob = base_prob * 0.9 + 0.05
else:  # JRA
    # 中央はAI予測の信頼性が高い
    adjusted_prob = base_prob

# 3. 印による補正
mark_weights = {
    '◎': 1.8 if NAR else 1.3,  # 本命
    '◯': 1.4 if NAR else 1.15,  # 対抗
    '▲': 1.2 if NAR else 1.1,   # 単穴
    '△': 1.1 if NAR else 1.05,  # 連下
    '': 1.0                      # 印なし
}
adjusted_prob *= mark_weights[mark]

# 4. 脚質相性補正（会場データがある場合）
if run_style_compatibility:
    adjusted_prob *= run_style_compatibility

# 5. 枠番有利度補正（会場データがある場合）
if frame_advantage:
    if 外枠 and 外枠有利会場:
        adjusted_prob *= outer_advantage
    elif 内枠 and 外枠有利会場:
        adjusted_prob *= (2.0 - outer_advantage)

# 6. 安全フィルタ
safety_threshold = 0.05 if NAR else 0.08
if base_prob < safety_threshold:
    # どんなにオッズが高くても推奨外
    return -1.0

# 7. EV計算
EV = (adjusted_prob * odds) - 1.0
```

**解釈:**
- **EV > 0**: 長期的に期待値プラス（買い推奨）
- **EV = 0**: トントン（見送り）
- **EV < 0**: 期待値マイナス（買わない）
- **EV = -1.0**: 安全フィルタで除外済み

---

## 📁 ディレクトリ構造

```
dai-keiba/
├── app/
│   ├── public_app.py                    # 公開アプリ（ユーザー向け予想画面）
│   └── admin_app.py                     # 管理アプリ（データ収集・学習）
├── data/
│   ├── raw/
│   │   ├── database.csv                 # JRA生データ
│   │   └── database_nar.csv             # NAR生データ
│   └── temp/
│       ├── todays_data.json             # 本日のJRAレース一覧
│       └── todays_data_nar.json         # 本日のNARレース一覧
├── scraper/
│   ├── auto_scraper.py                  # スクレイピング統括（キャッシュ機能）
│   ├── jra_scraper.py                   # JRA専用スクレイパー
│   ├── nar_scraper.py                   # NAR専用スクレイパー
│   └── race_classifier.py               # JRA/NAR自動判定
├── ml/
│   ├── feature_engineering.py           # 特徴量生成・前処理
│   ├── train_model.py                   # 学習・推論ロジック（最適化版）
│   ├── calibration_plot.py              # キャリブレーション曲線可視化
│   ├── performance_tracker.py           # パフォーマンス追跡
│   ├── explainability.py                # SHAP値による説明性
│   ├── scrape_historical_data.py        # 過去3年分データ収集スクリプト
│   └── models/
│       ├── lgbm_model.pkl               # JRAモデル
│       ├── lgbm_model_meta.json         # JRAメタデータ
│       ├── lgbm_model_nar.pkl           # NARモデル
│       └── lgbm_model_nar_meta.json     # NARメタデータ
├── notebooks/                           # Colabノートブック等
├── scripts/                             # ユーティリティスクリプト
└── keiba_data.db                        # SQLiteデータベース
```

---

## 🚀 使い方

### 1. 環境構築

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# MLflowサーバー起動（オプション）
mlflow ui --port 5000
```

### 2. アプリケーション起動

```bash
# 管理画面（ポート 8501）
streamlit run app/admin_app.py --server.port 8501

# 公開画面（ポート 8502）
streamlit run app/public_app.py --server.port 8502
```

### 3. 基本的な運用フロー

#### 初回セットアップ
1. **[管理画面]** スクレイピングタブ
   - 「過去3年分の履歴データ収集」を実行
   ```bash
   python ml/scrape_historical_data.py --start 2023-01-01
   ```
2. **[管理画面]** 特徴量生成タブ
   - 「特徴量を生成」ボタンをクリック
3. **[管理画面]** モデル学習タブ
   - 「完全最適化で学習」ボタンをクリック（初回は時間がかかる）

#### 日常運用
1. **[管理画面]** スクレイピングタブ
   - 「今日のレース一覧を更新」
   - 「過去1週間のデータ収集」（週1回）
2. **[管理画面]** モデル学習タブ
   - 「通常学習」（新データが1000件以上溜まったら）
   - または「完全最適化で学習」（月1回推奨）
3. **[公開画面]** メイン画面
   - 「最新モデルを再読み込み」
   - 「レース一覧を更新」
   - 対象レースを選択して「分析する」

---

## 📊 パフォーマンス指標

### モデル性能（JRA、5000件学習時の目安）

| 指標 | 通常学習 | Optuna最適化 | 改善率 |
|------|---------|-------------|--------|
| **AUC** | 0.72 | 0.78 | +8.3% |
| **F1 Score** | 0.15 | 0.22 | +46.7% |
| **Brier Score** | 0.085 | 0.068 | -20.0% |
| **Recall** | 0.42 | 0.51 | +21.4% |
| **Precision** | 0.09 | 0.14 | +55.6% |

### 信頼度スコアの分布例

| AI確率 | 適性平均 | 信頼度 | 解釈 |
|--------|----------|--------|------|
| 5% | 10 | 42% | 低確率だが高適性→中信頼 |
| 10% | 10 | 58% | 標準 |
| 30% | 10 | 82% | 高確率＋高適性→高信頼 |
| 15% | 3 | 35% | 適性データ不足→低信頼 |
| 50% | 10 | 60% | 迷い予測→中信頼 |

---

## 🔧 高度な設定

### Optunaハイパーパラメータ最適化

```python
from ml.train_model import train_and_save_model

# 完全最適化（100試行）
train_and_save_model(
    "ml/processed_data.csv",
    "ml/models/lgbm_model.pkl",
    optimize_hyperparams=True,   # Optuna有効化
    n_trials=100,                 # 試行回数
    find_threshold=True,          # 最適閾値探索
    calibrate=True                # 確率較正
)
```

### 確率較正の効果確認

```python
from ml.calibration_plot import plot_calibration_curve
import pandas as pd
import pickle

# モデル読み込み
with open("ml/models/lgbm_model.pkl", "rb") as f:
    model = pickle.load(f)

# テストデータで確率較正曲線を描画
df = pd.read_csv("ml/processed_data.csv")
# ... データ準備 ...
y_pred = model.predict(X_test)
plot_calibration_curve(y_test, y_pred, model_name="LightGBM")
```

---

## 🐛 トラブルシューティング

### Q1: AIスコアが全て同じ値になる
**A:** モデルファイルが古い可能性があります。
1. 「最新モデルを再読み込み」をクリック
2. 管理画面で再学習を実行

### Q2: 信頼度が全て同じ値になる
**A:** 修正済み（2025-12-23）。最新版にアップデートしてください。

### Q3: NARモードなのに「中央競馬（JRA）」と表示される
**A:** 修正済み（2025-12-23）。会場名から自動判定されます。

### Q4: 学習が遅すぎる
**A:** 以下を試してください:
- Optunaの試行回数を減らす（100→50→30）
- CVのfold数を減らす（5→3）
- データ量を減らす（最新1年分のみなど）

### Q5: Look-ahead biasが心配
**A:** TimeSeriesSplitで完全に対応済みです。日付順にソートして時系列分割しています。

### Q6: 予測時に「特徴量の数が一致しない」エラー
**A:** 学習時と予測時で`use_venue_features`パラメータが一致していません（2025-12-24修正）。

**現在の仕様:**
- 学習時: `use_venue_features=False`（デフォルト、27個の特徴量）
- 予測時: `use_venue_features=False`（同期済み）

**会場特性特徴量を使いたい場合（将来の拡張）:**
1. `ml/feature_engineering.py`の`calculate_features`関数に`use_venue_features=True`を指定
2. 管理画面で特徴量を再生成
3. モデルを再学習（JRA/NAR両方）
4. `public_app.py`でも`use_venue_features=True`に変更

会場特性特徴量（11個）:
- 脚質コード、脚質一貫性、序盤位置、位置変化
- 会場×脚質相性、会場×距離相性
- 直線距離、コース幅、勾配
- 会場×馬場状態相性、枠番有利度

---

## 📚 参考資料

### 機械学習アルゴリズム
- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [Optuna Documentation](https://optuna.readthedocs.io/)

### 評価指標
- **AUC**: 予測確率のランク付け性能（0.5=ランダム、1.0=完璧）
- **Brier Score**: 確率予測の精度（0.0=完璧、0.25=ランダム）
- **F1 Score**: Precision（精度）とRecall（再現率）の調和平均

### TimeSeriesSplit
- 時系列データで未来→過去の情報漏洩を防ぐCV手法
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)

---

## 📝 ライセンス

本プロジェクトは個人利用・学習目的での使用を想定しています。
商用利用する場合は、データ提供元（netkeiba.com）の利用規約を確認してください。

---

## 👨‍💻 開発者向け情報

### コードスタイル
- Python 3.8+
- PEP 8準拠
- Type hints推奨

### テスト
```bash
# 単体テスト（実装予定）
pytest tests/

# 統合テスト
python -m ml.train_model  # 学習パイプライン全体
```

### デバッグ
- ログファイル: `ml/training.log`
- MLflow UI: `http://localhost:5000`
- Streamlitデバッグモード: `streamlit run app.py --logger.level=debug`

---

**最終更新**: 2025-12-23
**バージョン**: 2.0.0（Optuna統合版）
