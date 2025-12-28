# 🏇 AI競馬予測システム (dai-keiba)

**最終更新:** 2025-12-28
**バージョン:** 2.0.0
**目的:** 競馬の**1着（勝馬）予測**による投資回収率最大化

---

## 📋 目次

1. [システム概要](#システム概要)
2. [主要機能](#主要機能)
3. [技術仕様](#技術仕様)
4. [特徴量詳細（60-70個）](#特徴量詳細)
5. [インストール・セットアップ](#インストールセットアップ)
6. [使用方法](#使用方法)
7. [モデル性能](#モデル性能)
8. [アーキテクチャ](#アーキテクチャ)
9. [データフロー](#データフロー)
10. [トラブルシューティング](#トラブルシューティング)

---

## 🎯 システム概要

### コンセプト

**「AIの予測確率」×「あなたの相馬眼（予想印）」×「オッズ」= 期待値(EV)**

本システムは、機械学習（LightGBM）を用いて**1着確率**を算出し、期待値（Expected Value）がプラスの馬券を見つけ出します。

### 主な特長

- ✅ **データリーク完全防止:** shift(1)による厳密な時系列処理
- ✅ **JRA/NAR別最適化:** 中央競馬・地方競馬で異なるモデル・パラメータ
- ✅ **60-70個の高品質特徴量:** 競馬専門知識を深く反映
- ✅ **確率較正対応:** Isotonic Regressionで予測精度向上
- ✅ **透明性:** モデル性能・信頼度を常時表示

### 対象ユーザー

- 💰 **投資家:** 期待値プラスの馬券で長期的な利益を追求
- 🎓 **データサイエンティスト:** 競馬予測の技術的チャレンジを楽しむ
- 🏇 **競馬ファン:** AIと自分の予想を組み合わせて的中率UP

---

## ⚡ 主要機能

### 1. AI予測機能

- **1着確率の算出:** 過去14万件以上のレースデータから学習
- **信頼度スコア:** 各予測の信頼性を0-100%で数値化
- **適性評価:** 騎手・コース・距離適性を個別表示

### 2. 期待値(EV)計算

- **純粋EV:** `(AI確率 × 印補正 × オッズ) - 1.0`
- **調整後EV:** JRA/NARで異なる補正係数
- **Kelly基準:** 最適賭け率を自動計算（資金の何%を賭けるべきか）

### 3. データ管理

- **自動スクレイピング:** netkeiba.comから最新データ取得
- **過去走データ:** 各馬の過去5走を自動収集
- **オッズ更新:** リアルタイム単勝・複勝オッズ取得

### 4. 管理画面

- **モデル再学習:** GUIから簡単にモデル更新
- **データベース管理:** スクレイピング・クリーニング・統計表示
- **パフォーマンス監視:** AUC・Brier Scoreなど性能指標の可視化

---

## 🔧 技術仕様

### システム要件

- **Python:** 3.8以上
- **必須ライブラリ:**
  - pandas, numpy（データ処理）
  - lightgbm（機械学習）
  - streamlit（UI）
  - selenium（スクレイピング）
  - optuna（ハイパーパラメータ最適化）
  - scikit-learn（前処理・評価）

### 機械学習モデル

| 項目 | 仕様 |
|------|------|
| アルゴリズム | LightGBM Gradient Boosting |
| タスク | Binary Classification (1着 = 1, その他 = 0) |
| 目的関数 | Binary Cross-Entropy |
| 評価指標 | AUC (ROC曲線下面積) |
| 交差検証 | TimeSeriesSplit (5分割) |
| ハイパーパラメータ最適化 | Optuna (50試行) |
| 確率較正 | Isotonic Regression（オプション） |

### ターゲット変数

```python
target_win = 1  # 1着の場合
target_win = 0  # 2着以下の場合

# 注: target_top3（3着以内）も保持しているが、
#     単勝EV計算との整合性から target_win を使用
```

**重要:** EV計算では単勝オッズを使用するため、**1着予測（target_win）が正しい選択**です。

---

## 📊 特徴量詳細

### 全特徴量一覧（60-70個）

#### 1. 過去成績ベース（9個）- 時間減衰加重平均

**重み係数:** `[0.50, 0.25, 0.13, 0.08, 0.04]` （前走→5走前）

| 特徴量 | 説明 | 計算式 |
|-------|------|--------|
| `weighted_avg_rank` | 加重平均着順 | Σ(past_i_rank × weight[i]) |
| `weighted_avg_run_style` | 加重平均位置取り | Σ(past_i_run_style × weight[i]) |
| `weighted_avg_last_3f` | 加重平均上り3F | Σ(past_i_last_3f × weight[i]) |
| `weighted_avg_horse_weight` | 加重平均馬体重 | Σ(past_i_weight × weight[i]) |
| `weighted_avg_odds` | 加重平均オッズ | Σ(past_i_odds × weight[i]) |
| `weighted_avg_weather` | 加重平均天候コード | Σ(past_i_weather × weight[i]) |
| `weighted_avg_weight_change` | 加重平均馬体重変化 | Σ(past_i_weight_change × weight[i]) |
| `weighted_avg_interval` | 加重平均レース間隔 | Σ(past_i_interval × weight[i]) |
| `weighted_avg_speed` | 加重平均速度（m/s） | Σ(past_i_speed × weight[i]) |

**重み設計の根拠:**
- 競馬業界標準（プロ予想家採用値）
- 前走50%は競馬予測の鉄則（直近情報が最重要）
- 指数減衰（lambda=0.2）では前走が30%程度で不十分

#### 2. トレンド（2個）- 線形回帰による成績推移

| 特徴量 | 説明 | 計算方法 |
|-------|------|----------|
| `trend_rank` | 着順トレンド | np.polyfit([1,2,3,4,5], [ranks], 1)[0] |
| `trend_last_3f` | 上り3Fトレンド | np.polyfit([1,2,3,4,5], [last_3fs], 1)[0] |

**解釈:**
- 正の傾き: 改善傾向（最近の走が良い）
- 負の傾き: 悪化傾向（最近の走が悪い）

#### 3. 適性スコア（7個） - 全期間（Global History）

**重要:** 以前の「過去5走」ロジックを廃止し、**過去3年間の全データを参照**する「Global Expanding Mean」方式に変更しました。「データなし（0点）」の問題が解消されています。

| 特徴量 | 説明 | デフォルト | 算出ロジック |
|-------|------|-----------|------------|
| `turf_compatibility` | 芝コース平均着順 | 10.0 | **全期間**の芝レース平均着順 |
| `dirt_compatibility` | ダートコース平均着順 | 10.0 | **全期間**のダートレース平均着順 |
| `good_condition_avg` | 良馬場平均着順 | 10.0 | 全期間の良馬場平均着順 |
| `heavy_condition_avg` | 重/不良馬場平均着順 | 10.0 | 全期間の重・不良での平均着順 |
| `distance_compatibility` | 距離適性スコア | 10.0 | 当該距離区分（短・マイル・中・長）での全期間平均着順 |
| `course_distance_record` | 会場×距離別平均着順 | 10.0 | 当該コース・距離での全期間平均着順 |
| `best_similar_course_rank` | 類似コース最良着順 | 18.0 | (変更なし) |

**リーク防止:**
全データは日付順にソートされ、`shift(1).expanding().mean()` を使用しているため、**必ず「そのレースより前」のデータのみ**を使って計算されます。

#### 4. レース間隔（4個）

| 特徴量 | 説明 | 値の範囲 | ロジック改善 |
|-------|------|----------|------------|
| `is_rest_comeback` | 休養明けフラグ | 0 or 1 | **過去全履歴**から正確な日数を計算（90日以上） |
| `interval_category` | 間隔カテゴリ | 1-4 | 1:連闘, 2:月内, 3:2ヶ月内, 4:休養 |
| `is_consecutive` | 連闘フラグ | 0 or 1 | 14日以内 |
| `last_race_reliability` | 前走信頼度 | 0.4-1.0 | レース間隔に基づく減衰係数 |

#### 5. 騎手・厩舎（9個）

**改善点:** 直近だけでなく**3年間の全相性**を算出。初騎乗時は「厩舎ライン（調教師×騎手）」の相性で補完します。

| 特徴量 | 説明 | 補完ロジック |
|-------|------|------------|
| `jockey_compatibility` | **騎手×馬**の全期間平均着順 | データなし時は **厩舎×騎手** の成績を使用 |
| `jockey_win_rate` | 騎手勝率（Rolling） | ✅ shift(1) |
| `jockey_top3_rate` | 騎手複勝率（Rolling） | ✅ shift(1) |
| `jockey_races_log` | 騎手経験値（log変換） | ✅ |
| `jockey_id` | 騎手IDハッシュ | - |
| `is_jockey_change` | 乗り替わりフラグ | - |
| `stable_win_rate` | 厩舎勝率（Rolling） | ✅ shift(1) |
| `stable_top3_rate` | 厩舎複勝率（Rolling） | ✅ shift(1) |
| `trainer_id` | 調教師IDハッシュ | - |

#### 6. レースクラス・タイプ（7個）

| 特徴量 | 説明 | 値の範囲 |
|-------|------|----------|
| `race_class` | レースクラス | 0（未知）～9（G1） |
| `race_type_code` | JRA/NAR | 1（JRA）, 0（NAR） |
| `is_graded` | 重賞フラグ | 0 or 1 |
| `age_limit` | 年齢制限 | 0/2/3/4 |
| `jra_compatibility` | JRA成績（平均着順） | - |
| `nar_compatibility` | NAR成績（平均着順） | - |
| `is_jra_transfer` | JRA→NAR転入フラグ | 0 or 1 |

**レースクラス階層:**
```
9: G1（最高峰）
8: G2
7: G3
6: オープン
5: 3勝クラス
4: 2勝クラス
3: 1勝クラス
2: 未勝利
1: 新馬
0: 不明
```

#### 7. 馬特性（4個）

| 特徴量 | 説明 | 値の範囲 |
|-------|------|----------|
| `age` | 馬齢 | 2-10歳程度 |
| `growth_factor` | 成長係数 | 0.85-1.3 |
| `last_race_performance` | 前走評価 | 0.6-1.2 |
| `rank_trend` | 連続着順変化 | -5～+5 |

**成長係数:**
- 2歳: 1.3（急成長期）
- 3歳: 1.15（成長期）
- 4-5歳: 1.0（ピーク）
- 6歳以上: 0.85（ベテラン）

#### 8. 現在レース条件（5個）

| 特徴量 | 説明 | 値 |
|-------|------|---|
| `course_type_code` | コース種別 | 1（芝）, 2（ダート）, 3（障害） |
| `distance_val` | 距離（m） | 1000-3600 |
| `rotation_code` | 回り | 1（右）, 2（左）, 3（直線） |
| `weather_code` | 天候 | 1-5 |
| `condition_code` | 馬場状態 | 1（良）-4（不良） |

#### 9. 血統（3個）

| 特徴量 | 説明 |
|-------|------|
| `father_id` | 父馬IDハッシュ |
| `mother_id` | 母馬IDハッシュ |
| `bms_id` | 母父馬IDハッシュ |

#### 10. 会場特性（11個）- オプション

`use_venue_features=True` で有効化

| 特徴量 | 説明 |
|-------|------|
| `run_style_code` | 脚質（1=逃げ, 2=先行, 3=差し, 4=追込） |
| `run_style_consistency` | 脚質安定度（0-1） |
| `venue_run_style_compatibility` | 会場×脚質相性 |
| `venue_distance_compatibility` | 会場×距離相性 |
| `straight_length` | 直線長（m） |
| `track_width_code` | コース幅 |
| `slope_code` | 勾配 |
| `venue_condition_compatibility` | 会場×馬場相性 |
| `frame_advantage` | 枠番有利度 |
| `dd_frame_bias` | **データ駆動型枠バイアス** ⭐ |
| `dd_run_style_bias` | **データ駆動型脚質バイアス** ⭐ |

詳細は [FEATURE_VALIDATION_REPORT.md](docs/FEATURE_VALIDATION_REPORT.md) を参照してください。

---

## 🚀 インストール・セットアップ

### 1. リポジトリクローン

```bash
git clone https://github.com/yourusername/dai-keiba.git
cd dai-keiba
```

### 2. 依存関係インストール

```bash
pip install -r requirements.txt
```

主要ライブラリ:
```
pandas>=1.3.0
numpy>=1.21.0
lightgbm>=3.3.0
streamlit>=1.20.0
selenium>=4.0.0
optuna>=3.0.0
scikit-learn>=1.0.0
mlflow>=2.0.0
```

### 3. Chromeドライバー設定（スクレイピング用）

```bash
# Chromeドライバーのダウンロード・配置
# https://chromedriver.chromium.org/

# パス設定（auto_scraper.py内）
CHROMEDRIVER_PATH = "/path/to/chromedriver"
```

### 4. ディレクトリ構造確認

```
dai-keiba/
├── app/
│   ├── public_app.py          # ユーザー向け予想UI
│   └── admin_app.py           # 管理画面
├── ml/
│   ├── feature_engineering.py # 特徴量生成
│   ├── train_model.py         # モデル学習
│   ├── backtest.py            # バックテスト
│   ├── constants.py           # 定数定義
│   ├── error_handler.py       # エラー処理
│   └── models/                # 学習済みモデル保存先
│       ├── lgbm_model.pkl
│       ├── lgbm_model_meta.json
│       ├── lgbm_model_nar.pkl
│       └── feature_stats.pkl
├── data/
│   ├── raw/                   # 生データ
│   │   ├── database.csv       # JRA全レースデータ
│   │   └── database_nar.csv   # NAR全レースデータ
│   ├── processed/             # 処理済みデータ
│   │   ├── processed_data.csv
│   │   └── processed_data_nar.csv
│   └── temp/                  # 一時ファイル
│       ├── todays_data.json
│       └── todays_data_nar.json
├── scraper/
│   └── auto_scraper.py        # スクレイピング
├── docs/                      # ドキュメント
│   ├── FEATURE_VALIDATION_REPORT.md
│   ├── SYSTEM_HEALTH_CHECK_REPORT.md
│   ├── METRICS_VALIDATION_REPORT.md
│   └── CALIBRATION_GUIDE.md
└── README.md                  # このファイル
```

---

## 💻 使用方法

### 基本ワークフロー

#### 1. データ収集（初回のみ）

```bash
# 管理画面を起動
streamlit run app/admin_app.py

# ブラウザで http://localhost:8501 を開く
# 「データベース管理」→「全データ更新」
```

#### 2. モデル学習

```bash
cd ml

# 基本学習
python train_model.py

# 確率較正あり（推奨）
python train_model.py --calibrate

# ハイパーパラメータ最適化
python train_model.py --optimize --n_trials 50 --calibrate
```

#### 3. 予想アプリ起動

```bash
streamlit run app/public_app.py
```

#### 4. 予想手順

1. **開催モード選択:** JRA / NAR
2. **レース一覧更新:** 「📅 レース一覧を更新」ボタン
3. **レース選択:** ドロップダウンから予想したいレースを選択
4. **出馬表取得:** 「🐴 出馬表を取得」ボタン
5. **AI予測実行:** 自動で予測・信頼度・適性スコアを表示
6. **予想印入力:** あなたの予想（◎◯▲△☆）を入力
7. **オッズ入力:** 現在オッズを手動入力 or 「🔄 最新オッズを取得」
8. **期待値確認:** EV（期待値）がプラスの馬を確認
9. **購入判断:** Kelly基準の推奨賭け率を参考に購入

---

## 📈 モデル性能

### JRAモデル（lgbm_model.pkl）

**学習データ:** 142,350件（2020-2025年）

| 指標 | 値 | 評価 |
|------|---|------|
| AUC | 0.8909 | ⭐⭐⭐⭐⭐ 優秀 |
| Precision | 0.7266 | モデルが「買い」判定した馬の73%が好走 |
| Recall | 0.1854 | 全勝ち馬の19%を検出（高精度・低カバー戦略） |
| Brier Score | 0.0567 | 確率予測の誤差（較正で改善可能） |
| 勝率（データ） | 7.27% | 理論値（1/18頭）に近い |

**解釈:**
- **AUC 0.89:** ランダムより89%正確に勝ち馬を上位に配置
- **Precision 0.73:** 的中精度が高い（予想した馬の7割が好走）
- **Recall 0.19:** カバー率は低め（全勝ち馬の2割のみ予想）
- → **「確実に来そうな馬だけを厳選」戦略**

### NARモデル（lgbm_model_nar.pkl）

| 指標 | 値 | 評価 |
|------|---|------|
| AUC | 0.8500 | ⭐⭐⭐⭐ 良好 |
| Brier Score | 0.0612 | JRAよりやや高い（データ量の差） |

---

## 🔬 理論・数式

### 1. 時間減衰加重平均

```
weighted_avg = Σ (value[i] × weight[i])

weight = [0.50, 0.25, 0.13, 0.08, 0.04]
  ↑        ↑     ↑     ↑     ↑     ↑
前走   前々走  3走前  4走前  5走前

例: 着順 [3, 5, 8, 10, 12]
weighted_avg = 3×0.50 + 5×0.25 + 8×0.13 + 10×0.08 + 12×0.04
             = 5.07着
```

### 2. 期待値(EV)

```
EV = (確率 × オッズ) - 1.0

調整後EV = (AI確率 × 印補正 × オッズ) - 1.0

印補正（JRA）:
  ◎ = 1.3
  ◯ = 1.15
  ▲ = 1.05
  △ = 1.02
  ☆ = 1.0

印補正（NAR）:
  ◎ = 1.8
  ◯ = 1.4
  ▲ = 1.2
  △ = 1.1
  ☆ = 1.0
```

### 3. Kelly基準

```
Kelly% = (p × b - 1) / (b - 1)

p: 勝率（AI確率 × 印補正）
b: オッズ

例:
  p = 0.15（15%）
  b = 10.0（10倍）

  Kelly = (0.15 × 10 - 1) / (10 - 1)
        = (1.5 - 1) / 9
        = 0.0556
        ≈ 5.56%

→ 資金の5.56%を賭けるべき

制限: max(0, min(10%, Kelly))  # 最大10%に制限
```

---

## ⚠️ トラブルシューティング

### Q1. モデルが読み込めない

**エラー:** `FileNotFoundError: lgbm_model.pkl not found`

**解決策:**
```bash
# モデルを再学習
cd ml
python train_model.py
```

### Q2. スクレイピングがタイムアウト

**エラー:** `TimeoutException: Element not found`

**解決策:**
- ネットワーク接続確認
- `auto_scraper.py` の `WAIT_TIME` を増やす
- Chromeドライバーのバージョン確認

### Q3. 予測精度が低い

**問題:** 的中率が期待より低い

**確認事項:**
1. モデルのAUCを確認（0.85以上が目安）
2. データ量を確認（10万件以上推奨）
3. 確率較正を実行したか
4. target_winで学習しているか（target_top3ではない）

**解決策:**
```bash
# 確率較正ありで再学習
cd ml
python train_model.py --calibrate
```

---

## 📚 参考資料

### ドキュメント

- [特徴量検証レポート](docs/FEATURE_VALIDATION_REPORT.md) - 全特徴量の詳細検証
- [システム動作確認レポート](docs/SYSTEM_HEALTH_CHECK_REPORT.md) - 構文チェック・整合性確認
- [指標検証レポート](docs/METRICS_VALIDATION_REPORT.md) - 数式・係数の検証
- [確率較正ガイド](docs/CALIBRATION_GUIDE.md) - 確率較正の詳細説明

### 外部リンク

- [LightGBM公式ドキュメント](https://lightgbm.readthedocs.io/)
- [Optuna公式ドキュメント](https://optuna.readthedocs.io/)
- [Streamlit公式ドキュメント](https://docs.streamlit.io/)

---

## 🤝 貢献

プルリクエスト歓迎！

### 貢献方法

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成


