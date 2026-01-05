"""
競馬予測システム用の定数定義

このファイルはマジックナンバーを集約し、コードの可読性と保守性を向上させます。
"""

# ==========================================
# デフォルト値（欠損値補完用）
# ==========================================

# 着順関連
DEFAULT_RANK = 18  # 最下位想定（18頭立てレース）
DEFAULT_POPULARITY = 18  # 最下位人気

# 馬体重関連
DEFAULT_HORSE_WEIGHT = 470.0  # 成馬の平均馬体重(kg)
DEFAULT_WEIGHT_CHANGE = 0.0  # 馬体重変化の中央値

# タイム関連
DEFAULT_TIME_SECONDS = 120.0  # 2000m走の平均タイム（秒）
DEFAULT_LAST_3F = 36.0  # 上がり3Fの平均（秒）

# オッズ関連
DEFAULT_ODDS = 10.0  # 中位人気のオッズ想定
MIN_ODDS = 1.0  # 最小オッズ
MAX_ODDS = 999.9  # 最大オッズ

# 距離関連
DEFAULT_DISTANCE = 1800  # 平均レース距離（メートル）
MIN_DISTANCE = 800
MAX_DISTANCE = 4000

# ==========================================
# 時間減衰加重（過去走重視度）
# ==========================================

# 過去5走の重み（前走が最重要）
TIME_DECAY_WEIGHTS = [0.50, 0.25, 0.13, 0.08, 0.04]
assert abs(sum(TIME_DECAY_WEIGHTS) - 1.0) < 0.001, "重みの合計は1.0である必要があります"

# ==========================================
# 適性スコアの閾値
# ==========================================

# 騎手・コース・距離適性のランク（1位〜18位を想定）
COMPATIBILITY_EXCELLENT = 3.5  # 優秀（1-3位）
COMPATIBILITY_GOOD = 7.0       # 良好（4-7位）
COMPATIBILITY_AVERAGE = 11.0   # 平均（8-11位）
COMPATIBILITY_POOR = 14.0      # 不良（12-14位）
# 14位超: 致命的

# ==========================================
# 信頼度スコアの調整値
# ==========================================

# データ量によるペナルティ
DATA_SIZE_THRESHOLD_CRITICAL = 1000  # この未満で-20
DATA_SIZE_THRESHOLD_LOW = 3000       # この未満で-8
DATA_SIZE_THRESHOLD_MEDIUM = 5000    # この未満で-3

DATA_PENALTY_CRITICAL = -20
DATA_PENALTY_LOW = -8
DATA_PENALTY_MEDIUM = -3

# 適性による信頼度ボーナス
COMPAT_BONUS_EXCELLENT = 15   # 全て高適性
COMPAT_BONUS_GOOD = 8         # 良適性
COMPAT_BONUS_AVERAGE = 0      # 平均的
COMPAT_BONUS_POOR = -12       # 不適性
COMPAT_BONUS_CRITICAL = -25   # 致命的

COMPAT_PENALTY_WEAK_POINT = -15  # 致命的な弱点を抱えている
COMPAT_PENALTY_MINOR = -5        # 小さな弱点

# その他のペナルティ
PENALTY_REST_COMEBACK = -10      # 長期休養明け
PENALTY_NO_HISTORY = -40         # データなし

# 信頼度スコアの範囲
CONFIDENCE_MIN = 20
CONFIDENCE_MAX = 95

# ==========================================
# EV計算パラメータ
# ==========================================

# JRA（中央競馬）の設定
JRA_MARK_WEIGHTS = {
    "◎": 1.15,  # 本命
    "◯": 1.10,  # 対抗
    "▲": 1.05,  # 単穴
    "△": 1.02,  # 連下
    "✕": 0.0,   # 消し
    "": 1.0     # 印なし
}
JRA_SAFETY_THRESHOLD = 0.04  # 1着確率4%未満は除外

# NAR（地方競馬）の設定
NAR_MARK_WEIGHTS = {
    "◎": 1.30,  # 本命（堅い決着のため高め）
    "◯": 1.15,  # 対抗
    "▲": 1.10,  # 単穴
    "△": 1.05,  # 連下
    "✕": 0.0,   # 消し
    "": 1.0     # 印なし
}
NAR_SAFETY_THRESHOLD = 0.03  # 1着確率3%未満は除外

# NAR未較正時の確率調整
NAR_PROB_CORRECTION_FACTOR = 0.9
NAR_PROB_CORRECTION_OFFSET = 0.05

# ==========================================
# Kelly基準
# ==========================================

KELLY_MAX_BET_RATIO = 0.10  # 最大賭け率（資金の10%まで）
KELLY_MIN_BET_RATIO = 0.0   # 最小賭け率

# ==========================================
# モデル学習パラメータ
# ==========================================

# TimeSeriesSplit
TIMESERIES_SPLIT_FOLDS = 5

# Early Stopping
EARLY_STOPPING_ROUNDS = 30

# Boosting Rounds
NUM_BOOST_ROUND = 300

# 最適閾値探索の範囲
THRESHOLD_SEARCH_MIN = 0.05
THRESHOLD_SEARCH_MAX = 0.95
THRESHOLD_SEARCH_STEP = 0.05

# ==========================================
# 会場特性の補正係数
# ==========================================

# 直線距離による補正
STRAIGHT_LONG_THRESHOLD = 500   # 長い直線（メートル）
STRAIGHT_SHORT_THRESHOLD = 300  # 短い直線（メートル）

# 長直線の補正（人気馬不利）
LONG_STRAIGHT_FAVORITE_PENALTY = 0.95
LONG_STRAIGHT_OUTSIDER_BONUS = 1.05

# 短直線の補正（人気馬有利）
SHORT_STRAIGHT_FAVORITE_BONUS = 1.05
SHORT_STRAIGHT_OUTSIDER_PENALTY = 0.95

# 小回りコースの補正
NARROW_TRACK_FAVORITE_BONUS = 1.03

# 急坂コースの補正
STEEP_SLOPE_FAVORITE_BONUS = 1.02

# ==========================================
# 枠番関連
# ==========================================

OUTER_FRAME_THRESHOLD = 6  # 外枠判定（6枠以上）
INNER_FRAME_THRESHOLD = 3  # 内枠判定（3枠以下）

# ==========================================
# 脚質コード
# ==========================================

RUN_STYLE_ESCAPE = 1    # 逃げ
RUN_STYLE_LEADING = 2   # 先行
RUN_STYLE_STALKING = 3  # 差し
RUN_STYLE_CLOSING = 4   # 追込

# ==========================================
# データベース関連
# ==========================================

DB_PATH = "keiba_data.db"
CACHE_EXPIRY_SECONDS = 900  # 15分

# ==========================================
# スクレイピング関連
# ==========================================

REQUEST_TIMEOUT = 10  # タイムアウト（秒）
REQUEST_DELAY = 1.0   # リクエスト間隔（秒）
MAX_RETRIES = 3       # 最大リトライ回数

# ==========================================
# UI表示関連
# ==========================================

TOP_N_DISPLAY = 5  # TOP N表示のデフォルト
PROGRESS_BAR_MAX = 100

# ==========================================
# 検証用
# ==========================================

if __name__ == "__main__":
    print("=== 競馬予測システム 定数一覧 ===")
    print(f"時間減衰重み合計: {sum(TIME_DECAY_WEIGHTS):.3f}")
    print(f"デフォルト馬体重: {DEFAULT_HORSE_WEIGHT}kg")
    print(f"JRA安全閾値: {JRA_SAFETY_THRESHOLD:.1%}")
    print(f"NAR安全閾値: {NAR_SAFETY_THRESHOLD:.1%}")
    print(f"Kelly最大賭け率: {KELLY_MAX_BET_RATIO:.1%}")
    print("✅ 定数ファイル正常")
