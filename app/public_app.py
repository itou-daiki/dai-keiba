import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import pickle
import json
import plotly.express as px
import plotly.graph_objects as go
import time
import logging
from datetime import datetime
import re
import importlib
import joblib

# Setup logger
logger = logging.getLogger(__name__)

# Add paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT, 'scraper'))
sys.path.append(os.path.join(PROJECT_ROOT, 'ml'))
sys.path.append(PROJECT_ROOT) # Add root for 'ml.feature_engineering' access

try:
    # -------------------------------------------------------------
    # Custom Modules
    # -------------------------------------------------------------
    #from scraper.auto_scraper import scrape_shutuba_data
    from scraper import auto_scraper
    from feature_engineering import process_data_v2 as process_data
    # Try importing from ml package first (correct structure)
    try:
        from ml.db_helper import KeibaDatabase
    except ImportError:
        # Fallback to root (local dev)
        from db_helper import KeibaDatabase
except ImportError as e:
    # This is critical if we rely on DB, but for public app we might use parquet
    print(f"Warning: KeibaDatabase import failed: {e}")
    KeibaDatabase = None

st.set_page_config(page_title="AI Keiba Predictor", layout="wide")

# --- Utils ---
@st.cache_resource
def load_model(mode="JRA"):
    import joblib  # Ensure import inside function for safety
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"ml/models/lgbm_model_nar.pkl" if mode == "NAR" else "ml/models/lgbm_model.pkl")
    if os.path.exists(model_path):
        try:
            return joblib.load(model_path)
        except Exception as e:
            st.error(f"Failed to load model with joblib: {e}")
            return None
    return None

@st.cache_resource
def load_model_metadata(mode="JRA"):
    """モデルのメタデータ（訓練日時、性能指標など）を読み込む"""
    meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"ml/models/lgbm_model_nar_meta.json" if mode == "NAR" else "ml/models/lgbm_model_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@st.cache_resource
def load_history_csv(mode):
    """過去データをキャッシュとしてロード (高速化: Parquet優先 + メモリ最適化)"""
    base_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    filename_base = "database_nar" if mode == "NAR" else "database"
    
    # Check Parquet first
    parquet_path = os.path.join(base_dir, f"{filename_base}.parquet")
    csv_path = os.path.join(base_dir, f"{filename_base}.csv")
    
    # Optimization: Load only necessary columns
    usecols = [
        'horse_id', 'race_id', '日付', '着 順', 'タイム', 'レース名', 
        '後3F', '馬体重(増減)', '騎手', '馬場状態', '単勝 オッズ', 
        '天候', '距離', 'コースタイプ', 'father', 'mother', 'bms'
    ]

    # Memory Efficient Dtypes
    dtypes = {
        'horse_id': 'category',
        'race_id': 'category',
        '着 順': 'str', # Mixed types often, safe as str then coerce
        '騎手': 'category',
        '馬場状態': 'category',
        '天候': 'category',
        'コースタイプ': 'category',
        'father': 'category',
        'mother': 'category',
        'bms': 'category',
        '単勝 オッズ': 'float32'
    }

    df = None
    
    if os.path.exists(parquet_path):
        try:
            # Parquet is efficient, but we can cast types after load
            df = pd.read_parquet(parquet_path, columns=usecols)
        except:
             try:
                 df = pd.read_parquet(parquet_path) # Fallback
             except Exception as e:
                 st.warning(f"Parquet load failed: {e}")
            
    elif os.path.exists(csv_path):
        try:
            df = pd.read_csv(
                csv_path, 
                usecols=lambda c: c in usecols, 
                dtype=dtypes,
                low_memory=True
            )
        except Exception as e:
            st.warning(f"CSV load failed: {e}")
            
    if df is not None:
        # Key Mismatch Fix & Type enforcement
        if 'horse_id' in df.columns:
            df['horse_id'] = df['horse_id'].astype(str).str.replace(r'\.0$', '', regex=True).astype('category')
        if 'race_id' in df.columns:
            df['race_id'] = df['race_id'].astype(str).str.replace(r'\.0$', '', regex=True).astype('category')
            
        # Optimize numeric columns
        for col in ['単勝 オッズ', 'タイム', '後3F']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float32')
                
        return df
        
    return None

@st.cache_resource
def load_stats(mode="JRA"):
    """統計データ（騎手・コース成績など）をロード"""
    stats_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"ml/models/feature_stats_nar.pkl" if mode == "NAR" else "ml/models/feature_stats.pkl")
    if os.path.exists(stats_path):
        try:
            with open(stats_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            st.warning(f"Stats load error: {e}")
    return None

def get_data_freshness(mode="JRA"):
    """データベースの最終更新日時を取得（Parquet優先）"""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
    filename_base = "database_nar" if mode == "NAR" else "database"
    
    # Check Parquet first
    target_path = os.path.join(base_dir, f"{filename_base}.parquet")
    if not os.path.exists(target_path):
        target_path = os.path.join(base_dir, f"{filename_base}.csv")
    
    if os.path.exists(target_path):
        try:
            mtime = os.path.getmtime(target_path)
            dt = datetime.fromtimestamp(mtime)
            freshness = dt.strftime('%Y-%m-%d %H:%M')
            
            # 鮮度判定 (3日以内なら0=安全、それ以上は日数)
            days_diff = (datetime.now() - dt).days
            return freshness, days_diff
        except Exception as e:
            st.warning(f"データ鮮度の取得に失敗: {e}")
            return "不明", -1
    return "データなし", -1

def calculate_confidence_score(row, ai_prob, model_meta, jockey_compat=None, course_compat=None, distance_compat=None, is_rest_comeback=0, has_history=True):
    """
    予測の信頼度スコアを計算（0-100）

    Args:
        ai_prob: AI予測確率（0-1）
        model_meta: モデルメタデータ
        jockey_compat: 騎手相性スコア（0-10、Noneの場合は考慮しない）
        course_compat: コース適性スコア（0-10、Noneの場合は考慮しない）
        distance_compat: 距離適性スコア（0-10、Noneの場合は考慮しない）
        is_rest_comeback: 休養明けフラグ（1=True, 0=False）
        has_history: 過去走データがあるかどうか (True/False)

    Returns:
        int: 信頼度スコア（0-100）
    """
    if not model_meta:
        return 50  # デフォルト

    # ===== 1. ベース信頼度: 固定値（天井効果を解消するため大幅に下げる） =====
    # 完全にフラットな状態を30とし、加点で伸ばす方式に変更
    base_confidence = 30.0

    # ===== 2. データ量による調整 =====
    data_size = model_meta.get('data_stats', {}).get('total_records', 0)
    if data_size < 1000:
        data_penalty = -20  # データ量少ない
    elif data_size < 3000:
        data_penalty = -8
    elif data_size < 5000:
        data_penalty = -3
    else:
        data_penalty = 0

    # ===== 3. 予測確率による調整（連続的な調整） =====
    # 0.5から離れるほど信頼度が高い（モデルが確信を持っている）
    # 0.5に近いほど信頼度が低い（モデルが迷っている）
    distance_from_uncertain = abs(ai_prob - 0.5)

    # 距離に基づく信頼度ボーナス: 0.5離れていると最大+20、0.0だと-20
    # 式を調整して範囲を拡大
    prob_bonus = (distance_from_uncertain * 2 - 0.25) * 40

    # さらに極端な予測（<0.10 or >0.90）には追加ボーナス (Top 3用に調整)
    if ai_prob < 0.10 or ai_prob > 0.90:
        prob_bonus += 12

    # AI確率が極端に低い場合は信頼度を下げる（データ不足の可能性）
    if ai_prob < 0.15:
        prob_bonus -= 10

    # ===== 4. 適性スコアによる調整（新規追加） =====
    compat_bonus = 0

    # 利用可能な適性スコアを集計
    compat_scores = []
    if jockey_compat is not None and not pd.isna(jockey_compat):
        compat_scores.append(jockey_compat)
    if course_compat is not None and not pd.isna(course_compat):
        compat_scores.append(course_compat)
    if distance_compat is not None and not pd.isna(distance_compat):
        compat_scores.append(distance_compat)

    if compat_scores:
        avg_compat = sum(compat_scores) / len(compat_scores)
        min_compat = min(compat_scores)

        # 平均適性による調整 (Lower is Better, since these are Ranks 1-18)
        # 1.0 - 4.0: Excellent
        # 4.1 - 8.0: Good
        # 8.1 - 12.0: Average
        # 12.1+: Poor
        
        if avg_compat <= 3.5:
            compat_bonus = +50  # 全て高適性 (Rank 1-3) -> 極めて強力な補正
        elif avg_compat <= 7.0:
            compat_bonus = +25  # 良適性 (Rank 4-7)
        elif avg_compat <= 11.0:
            compat_bonus = 0    # 平均的
        elif avg_compat <= 14.0:
            compat_bonus = -30  # 不適性
        else:
            compat_bonus = -60  # 致命的 (Rank 15-18)

        # 最低スコアによる追加ペナルティ（いずれかの適性が極端に低い場合 = Rankが大きい）
        if max(compat_scores) > 13.0:
            compat_bonus -= 15  # 致命的な不適性を抱えている
        elif max(compat_scores) > 10.0:
            compat_bonus -= 5


    # ===== 5. 休養明け・間隔による調整 (新規追加) =====
    interval_penalty = 0
    if is_rest_comeback == 1:
        interval_penalty = -10 # 長期休養明けは不確定要素が多い
        
    # ===== 6. 初出走・履歴なしによるペナルティ (新規追加) =====
    history_penalty = 0
    if not has_history:
        history_penalty = -40 # データが全くない馬は信頼できない

    # ===== 7. 前走成績による補正 (新規追加) =====
    # ユーザー要望: 前走成績を強く反映
    past_rank_bonus = 0
    past_1_rank = row.get('past_1_rank')

    if pd.notna(past_1_rank):
        try:
            p1 = float(past_1_rank)
            if p1 <= 1.0:
                past_rank_bonus = +15 # 前走1着は勢いあり
            elif p1 <= 3.0:
                past_rank_bonus = +8  # 前走好走
            elif p1 >= 10.0:
                past_rank_bonus = -15 # 前走大敗は割り引き
        except:
            pass
            
    # ===== 最終計算 =====
    confidence = base_confidence + data_penalty + prob_bonus + compat_bonus + interval_penalty + history_penalty + past_rank_bonus

    # 範囲を拡大: 20-95（より差別化）
    return int(max(20, min(95, confidence)))

def predict_race_logic(df, model, model_meta, stats=None, mode="JRA"):
    """
    データフレームに対してAI予測と信頼度計算を行う
    stats: 統計情報の辞書（inference用）
    mode: "JRA" or "NAR" (Default: "JRA")
    """
    try:
        # 特徴量エンジニアリング（会場特性あり）
        # inference mode: pass stats (default to empty dict if None to force Inference Path)
        X_df = process_data(df, use_venue_features=True, input_stats=stats if stats is not None else {})

        # Align features with model
        if hasattr(model, 'feature_name'):
             model_features = model.feature_name()
             # Ensure all features exist and log missing ones
             missing_features = []
             for f in model_features:
                 if f not in X_df.columns:
                     missing_features.append(f)
                     X_df[f] = 0

             if missing_features:
                 logger.warning(f"⚠️  Missing features defaulted to 0 (first 10): {missing_features[:10]}")
                 if len(missing_features) > 10:
                     logger.warning(f"... and {len(missing_features)-10} more missing features")

             X_pred = X_df[model_features].copy()
             # Fill NA with 0 (consistent with Admin App)
             X_pred = X_pred.fillna(0)
             
             # Category Handling (Crucial for LightGBM)
             for col in X_pred.select_dtypes(include=['object']).columns:
                 X_pred[col] = X_pred[col].astype('category')

        else:
             # Fallback for older sklearn models or if feature_name not available
             meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
             features = [c for c in X_df.columns if c not in meta_cols and c != 'target_win']
             X_pred = X_df[features].select_dtypes(include=['number']).fillna(0)

        # Predict (Robust logic synced with Admin App)
        if hasattr(model, 'predict_proba'):
             probs = model.predict_proba(X_pred)[:, 1]
        else:
             probs = model.predict(X_pred)

        df['AI_Prob'] = probs
        df['AI_Score'] = (probs * 100).astype(float) # Ensure float for downstream calcs
        
        # Save X_df to session state for debugging
        st.session_state['last_features'] = X_df

        # Calculate Confidence
        confidences = []
        for idx, p in enumerate(probs):
            jockey_c = X_df['jockey_compatibility'].iloc[idx] if 'jockey_compatibility' in X_df.columns else None
            distance_c = X_df['distance_compatibility'].iloc[idx] if 'distance_compatibility' in X_df.columns else None
            
            # Course compatibility
            course_c = None
            if 'turf_compatibility' in X_df.columns and 'dirt_compatibility' in X_df.columns:
                if 'コースタイプ' in df.columns:
                    course_type = df['コースタイプ'].iloc[idx]
                    if '芝' in str(course_type):
                        course_c = X_df['turf_compatibility'].iloc[idx]
                    elif 'ダ' in str(course_type):
                        course_c = X_df['dirt_compatibility'].iloc[idx]
                else:
                    course_c = X_df['turf_compatibility'].iloc[idx] # Default

            is_rest = X_df['is_rest_comeback'].iloc[idx] if 'is_rest_comeback' in X_df.columns else 0
            
            # Check for history (using raw df columns if available, or heuristic on X_df)
            has_history = True
            if 'past_1_rank' in df.columns:
                 val = df['past_1_rank'].iloc[idx]
                 if pd.isna(val) or val == 0 or val == "":
                     has_history = False
            
            conf = calculate_confidence_score(df.iloc[idx], p, model_meta, jockey_c, course_c, distance_c, is_rest, has_history)
            confidences.append(conf)

        df['Confidence'] = confidences

        # D指数 calc moved after feature merge


        # Merge relevant features back to df
        cols_to_merge = [
            'turf_compatibility', 'dirt_compatibility',
            'jockey_compatibility', 'distance_compatibility',
            'weighted_avg_speed', 'weighted_avg_rank',
            'dd_frame_bias', 'dd_run_style_bias',
            'jockey_win_rate', 'course_distance_record',
            'good_condition_avg', 'heavy_condition_avg',
            'stable_win_rate', 'jockey_top3_rate',
            'trend_rank', 'growth_factor',
            # 過去成績データも追加
            'past_1_rank', 'past_2_rank', 'past_3_rank', 'past_4_rank', 'past_5_rank',
            'past_1_last_3f', 'past_2_last_3f', 'past_3_last_3f',
            # 血統統計
            'sire_win_rate', 'bms_win_rate'
        ]
        for c in cols_to_merge:
            if c in X_df.columns:
                df[c] = X_df[c]

        # course_compatibilityを動的に生成（コースタイプに応じて芝/ダートを選択）
        if 'turf_compatibility' in df.columns and 'dirt_compatibility' in df.columns:
            if 'コースタイプ' in df.columns:
                df['course_compatibility'] = df.apply(
                    lambda row: row['turf_compatibility'] if '芝' in str(row.get('コースタイプ', ''))
                               else row['dirt_compatibility'] if 'ダ' in str(row.get('コースタイプ', ''))
                               else row['turf_compatibility'],  # Default to turf
                    axis=1
                )
            else:
                # コースタイプ不明の場合は芝をデフォルトに
                df['course_compatibility'] = df['turf_compatibility']
        elif 'turf_compatibility' in df.columns:
            df['course_compatibility'] = df['turf_compatibility']
        elif 'dirt_compatibility' in df.columns:
            df['course_compatibility'] = df['dirt_compatibility']
        else:
            df['course_compatibility'] = 5.0  # デフォルト値
        # === D-Index Calculation (Refactored) ===
        import scoring
        importlib.reload(scoring) # Ensure latest logic
        
        # Load Weights (Mode Specific)
        d_index_conf_path = os.path.join(PROJECT_ROOT, "config", f"d_index_config_{mode.lower()}.json")
        default_weights = {'ai': 0.4, 'compat': 0.5, 'blood': 0.1}
        weights = default_weights
        if os.path.exists(d_index_conf_path):
            try:
                with open(d_index_conf_path, 'r') as f:
                    weights = json.load(f)
            except:
                pass
        # Fallback
        elif os.path.exists(os.path.join(PROJECT_ROOT, "config", "d_index_config.json")):
             try:
                with open(os.path.join(PROJECT_ROOT, "config", "d_index_config.json"), 'r') as f:
                    weights = json.load(f)
             except:
                pass
        
        df['Compat_Index'] = df.apply(lambda row: scoring.calculate_pure_compat(
            row, 
            weights.get('compat_sub_weights', {'jockey': 0.4, 'distance': 0.3, 'course': 0.3})
        ), axis=1)
        df['Bloodline_Index'] = df.apply(scoring.calculate_bloodline_index, axis=1)
        df['D_Index'] = df.apply(lambda row: scoring.calculate_d_index(row, weights), axis=1)
        return df
    except Exception as e:
        import traceback
        st.error(f"Prediction Error: {e}")
        st.code(traceback.format_exc())
        return None

def load_schedule_data(mode="JRA"):
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temp", "todays_data_nar.json" if mode == "NAR" else "todays_data.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# --- UI ---
st.title("🏇 AI競馬予想システム")

# Logic Explanation
with st.expander("ℹ️ このAI予想のロジックについて (クリックして開く)"):
    st.markdown("""
    ### 🧠 AI予想の仕組み
    このシステムは**LightGBM**という機械学習モデルを使用し、過去の膨大なレースデータから「1着（勝利）の確率」を算出しています。
    
    #### 使用しているデータ
    - **基本情報**: 枠番、馬番、馬齢、斤量、騎手
    - **過去5走の成績**: 着順、走破タイム、上り3F、通過順（脚質）、馬体重、馬場状態、**天気**、**最終オッズ**
    - **直近重視**: 過去のレースは直近のものほど重要視する「時間減衰」処理を行っています。
    
    #### 🎯 期待値 (EV) とは？
    「その馬券を買い続けたときに、最終的にいくら儲かるか」の指標です。
    
    $$
    \text{調整後期待値} = (\text{AIの勝率} \times \text{あなたの印} \times \text{オッズ}) - 1.0
    $$
    
    - **プラス (0以上)**: 買えば買うほど儲かるチャンスがある馬（推奨！）
    - **マイナス**: 勝つ確率に比べてオッズが低すぎる（割に合わない）馬
    - **あなたの印**: AIの予測に、あなたの直感（◎や◯）をミックスして計算します。AIだけでなく、あなたの相馬眼も反映されます。

    #### 🏇 中央競馬 vs 🌙 地方競馬
    このシステムは、会場から自動的に中央競馬（JRA）と地方競馬（NAR）を判定し、それぞれに最適化された期待値を計算します。

    **中央競馬（JRA）:**
    - 印の補正係数: ◎=1.3倍, ◯=1.15倍（控えめ）
    - 安全フィルタ: AI確率8%未満は除外
    - 特徴: レベルが高く、予想が堅め

    **地方競馬（NAR）:**
    - 印の補正係数: ◎=1.8倍, ◯=1.4倍（積極的）
    - 安全フィルタ: AI確率5%未満は除外
    - 特徴: 波乱が多く、人気薄が勝ちやすい

    #### 📊 信頼性向上の取り組み
    - **モデルメタデータ**: 訓練日時、性能指標（AUC）、データ量を常時表示
    - **予測信頼度スコア**: 各予測にモデルの信頼性を0-100%で数値化
    - **データ新鮮度**: データベースの最終更新日時を表示（3日以内が理想）
    - **注意喚起**: データ量不足や予測の限界を明示
    - **透明性**: モデルの性能・限界を隠さず開示
    """)


# -------------------------------------------------------------
# Triple Umatan (SPAT4 Loto) Logic
# -------------------------------------------------------------
def render_triple_umatan_section(target_races, mode_val):
    """
    トリプル馬単（キャリーオーバーなど）用の予想セクション
    3レース分の予想を一括で行い、買い目を生成する
    """
    st.markdown("### 🎯 SP: トリプル馬単 (Triple Exacta) 予想")
    st.info("💡 **機能説明**: 指定した3レース（通常は最終3レース）の馬単（1着・2着）をすべて的中させる「トリプル馬単」の買い目を生成します。")

    if not target_races or len(target_races) < 3:
        st.error("⚠️ レース情報が不足しています。少なくとも3レース必要です。")
        return

    # 1. Race Selection
    st.subheader("1. 対象レースの選択")
    
    # Sort by number first
    sorted_races = sorted(target_races, key=lambda x: int(x['number']) if str(x['number']).isdigit() else 0)
    
    # Try to find flagged races
    flagged_races = [r for r in sorted_races if r.get('is_triple', False)]
    
    if len(flagged_races) >= 3:
        # Used flagged races
        default_selections = flagged_races[:3] # Assumption: Triple is exactly 3
    else:
        # Fallback to Last 3
        default_selections = sorted_races[-3:] if len(sorted_races) >= 3 else sorted_races
    
    last_3 = default_selections # Rename for compatibility with existing variable usage
    
    race_options_list = [f"{r['number']}R: {r['name']}" for r in sorted_races]
    
    col_sel_1, col_sel_2, col_sel_3 = st.columns(3)
    
    # Defaults
    def get_idx(r): return filter_race_idx(sorted_races, r)
    
    # Dynamic Key Suffix (Date + Venue)
    if sorted_races:
        rk = f"{sorted_races[0].get('date','')} {sorted_races[0].get('venue','')}"
    else:
        rk = "unknown"

    with col_sel_1:
        idx1 = sorted_races.index(last_3[0]) if len(last_3) > 0 else 0
        r1_label = st.selectbox("1レース目", race_options_list, index=idx1, key=f"tu_r1_{rk}")
    with col_sel_2:
        idx2 = sorted_races.index(last_3[1]) if len(last_3) > 1 else 1
        r2_label = st.selectbox("2レース目", race_options_list, index=idx2, key=f"tu_r2_{rk}")
    with col_sel_3:
        idx3 = sorted_races.index(last_3[2]) if len(last_3) > 2 else 2
        r3_label = st.selectbox("3レース目", race_options_list, index=idx3, key=f"tu_r3_{rk}")

    selected_race_objs = []
    for label in [r1_label, r2_label, r3_label]:
        # Find object
        found = next((r for r in sorted_races if f"{r['number']}R: {r['name']}" == label), None)
        if found: selected_race_objs.append(found)

    # Session state key for Triple Umatan
    if 'tu_active' not in st.session_state:
        st.session_state['tu_active'] = False

    if st.button("🚀 トリプル馬単予想を開始", type="primary"):
        st.session_state['tu_active'] = True
        
    if st.session_state['tu_active']:
        if st.button("🔄 リセット / 閉じる"):
            st.session_state['tu_active'] = False
            st.rerun()

        model = load_model(mode_val)
        model_meta = load_model_metadata(mode_val)
        stats = load_stats(mode_val)
        
        if not model:
            st.error("モデルの読み込みに失敗しました。")
            return

        st.markdown("---")
        st.subheader("2. 各レースの分析・買い目構築")

        # Container for results
        results_container = st.container()
        
        total_combinations = 1
        prediction_summaries = []

        with st.spinner("3レース分のデータを分析中..."):
            history_df_cache = load_history_csv(mode_val) # Load once
            
            for i, race in enumerate(selected_race_objs):
                with results_container:
                    st.markdown(f"#### {i+1}レース目: {race['venue']}{race['number']}R {race['name']}")
                    
                    # Analyze
                    df_race = auto_scraper.scrape_shutuba_data(race['id'], mode=mode_val, history_df=history_df_cache)
                    if df_race is None or df_race.empty:
                        st.error(f"データの取得に失敗: {race['id']}")
                        return

                    processed_df = predict_race_logic(df_race, model, model_meta, stats=stats, mode=mode_val)
                     # Odds Bias (Simple apply for Triple Umatan)
                    if processed_df is not None:
                        # 1. Restore AI Score
                        processed_df['AIスコア(%)'] = processed_df['AI_Prob'] * 100

                        # 2. Prepare D-Index (D指数)
                        if 'D_Index' in processed_df.columns:
                            processed_df['D指数'] = processed_df['D_Index']
                        else:
                            processed_df['D指数'] = processed_df['AIスコア(%)']
                            
                        # 3. Add Info Columns (Compatibility & History)
                        # Map internal names to display names AND convert to 0-10 score (Higher is Better)
                        # Logic matches individual analysis: 10 - (avg_rank / 2)
                        def convert_compat_score(x):
                            if pd.isna(x): return 5.0
                            return max(0, min(10, 10 - (x / 2)))

                        if 'jockey_compatibility' in processed_df.columns:
                            processed_df['騎手適性度'] = processed_df['jockey_compatibility'].apply(convert_compat_score).round(1)
                        if 'distance_compatibility' in processed_df.columns:
                            processed_df['距離適性度'] = processed_df['distance_compatibility'].apply(convert_compat_score).round(1)
                        if 'course_compatibility' in processed_df.columns:
                            processed_df['コース適性度'] = processed_df['course_compatibility'].apply(convert_compat_score).round(1)
                            
                        # Add Weighted Avg Speed if available
                        if 'weighted_avg_speed' in processed_df.columns:
                             processed_df['平均スピード'] = processed_df['weighted_avg_speed'].round(1)

                        if 'past_1_rank' in processed_df.columns:
                            processed_df['前走着順'] = processed_df['past_1_rank'].fillna('-')
                            
                        # Use odds if available
                        if '単勝' in processed_df.columns:
                            processed_df['現在オッズ'] = pd.to_numeric(processed_df['単勝'], errors='coerce').fillna(0.0)
                        
                        # Add confidence
                        processed_df['信頼度'] = processed_df.apply(
                            lambda row: calculate_confidence_score(row, row['AI_Prob'], model_meta), axis=1
                        )

                        # Sort by D-Index
                        processed_df = processed_df.sort_values("D指数", ascending=False)
                        
                        # Add '予想印' column (Empty by default)
                        processed_df['予想印'] = ""
                        
                        # Add '調整後期待値' (Initial estimation)
                        # Formula: (AI_Prob * Odds * Mark_Bias) - 1.0 (Assume No Mark initially)
                        # Note: Simple estimation.
                        if '現在オッズ' in processed_df.columns:
                             processed_df['調整後期待値'] = (processed_df['AI_Prob'] * processed_df['現在オッズ']) - 1.0
                        else:
                             processed_df['調整後期待値'] = 0.0

                        # Calculate Gap
                        gap = 0.0
                        if len(processed_df) >= 2:
                            gap = processed_df.iloc[0]['D指数'] - processed_df.iloc[1]['D指数']
                        
                        # Top Candidates (Show ALL)
                        # top_horses = processed_df.head(6) # Removed limit
                        top_horses = processed_df
                        
                        # Display Top 4
                        st.write(f"**GAP値:** {gap:.1f}")
                        
                        # Define columns to show
                        # Create Pedigree Column
                        if 'father' in processed_df.columns and 'mother' in processed_df.columns:
                             processed_df['血統'] = processed_df.apply(
                                 lambda r: f"{r['father']} / {r['mother']}" + (f" ({r['bms']})" if pd.notna(r.get('bms')) else ""), 
                                 axis=1
                             )
                        else:
                             processed_df['血統'] = "-"
                             
                        cols_show = ['枠', '馬 番', '馬名', '予想印', 'D指数', 'AIスコア(%)', '信頼度', '現在オッズ', '調整後期待値']
                        # Add optional columns if they exist
                        for col in ['騎手適性度', 'コース適性度', '距離適性度', '平均スピード', '前走着順']:
                            if col in processed_df.columns:
                                cols_show.append(col)
                        cols_show.append('血統')
                                
                        # Interactive Editor
                        st.data_editor(
                            top_horses[cols_show],
                            height=300, # Taller for full list
                            hide_index=True,
                            column_config={
                                "AIスコア(%)": st.column_config.ProgressColumn(
                                    "AI勝率", format="%d%%", min_value=0, max_value=100
                                ),
                                "D指数": st.column_config.ProgressColumn(
                                    "D指数", format="%.1f", min_value=0, max_value=100
                                ),
                                "信頼度": st.column_config.NumberColumn(
                                    "信頼度", format="%d%%"
                                ),
                                "予想印": st.column_config.SelectboxColumn(
                                    "予想印",
                                    options=["", "◎", "◯", "▲", "△", "✕"],
                                    required=False,
                                    width="small"
                                ),
                                "調整後期待値": st.column_config.NumberColumn(
                                    "調整後期待値", format="%.2f"
                                ),
                                "平均スピード": st.column_config.NumberColumn(
                                    "平均スピード", format="%.1f m/s"
                                ),
                                "騎手適性度": st.column_config.ProgressColumn(
                                    "騎手適性", format="%.1f", min_value=0, max_value=10
                                ),
                                "コース適性度": st.column_config.ProgressColumn(
                                    "コース適性", format="%.1f", min_value=0, max_value=10
                                ),
                                "距離適性度": st.column_config.ProgressColumn(
                                    "距離適性", format="%.1f", min_value=0, max_value=10
                                ),
                            },
                             key=f"editor_{race['id']}_{i}" # Unique key for state persistence
                        )
                        
                        # === Data Missing Alerts (Triple Umatan) ===
                        edited_df = top_horses # Use top_horses as source for checks
                        
                        def to_circled(n):
                            try:
                                n_int = int(n)
                                if 1 <= n_int <= 20: return chr(9311 + n_int)
                                return str(n)
                            except: return str(n)

                        unknown_history = []
                        if '前走着順' in edited_df.columns:
                            unknown_history = [f"{to_circled(row['馬 番'])} {row['馬名']}" for _, row in edited_df[edited_df['前走着順'] == 0].iterrows()]
                            
                        unknown_jockey = []
                        hidden_gems = []
                        if '騎手適性度' in edited_df.columns:
                            # 5.0 is the fallback score for missing data
                            jockey_missing_mask = (edited_df['騎手適性度'] == 5.0)
                            unknown_jockey = [f"{to_circled(row['馬 番'])} {row['馬名']}" for _, row in edited_df[jockey_missing_mask].iterrows()]
                            
                            if 'コース適性度' in edited_df.columns and '距離適性度' in edited_df.columns:
                                 potential_mask = (edited_df['コース適性度'] >= 7.0) | (edited_df['距離適性度'] >= 7.0)
                                 hidden_gems = [f"{to_circled(row['馬 番'])} {row['馬名']}" for _, row in edited_df[jockey_missing_mask & potential_mask].iterrows()]
                
                        if unknown_history or unknown_jockey:
                             st.warning("⚠️ 一部の馬にデータ不足があります")
                             cols_alert = st.columns(2)
                             with cols_alert[0]:
                                 if unknown_history:
                                     st.info(f"**初出走・履歴なし**: {', '.join(unknown_history)}")
                             with cols_alert[1]:
                                 if unknown_jockey:
                                     st.info(f"**騎手データ不足**: {', '.join(unknown_jockey)}")
                                 if hidden_gems:
                                     st.success(f"✨ **騎手は未知数ですが、馬の適性は高い**: {', '.join(hidden_gems)}")
                        
                        # Suggestion
                        st.caption("👇 フォーメーション設定 (AI推奨: 1着候補=上位2頭, 2着候補=上位4頭)")
                        
                        # Logic similar to 'Renkei' in main app
                        if gap >= 15.0: # Solid Favorite
                             st.info(f"🦾 **鉄板** (Gap {gap:.1f}): 1着候補を絞れる可能性があります")
                        elif gap < 10.0: # Confusion
                             st.warning(f"🌪️ **混戦** (Gap {gap:.1f}): BOX買いなども検討してください")
                        else: # Standard
                             st.success(f"⚖️ **標準** (Gap {gap:.1f}): バランスの良いレースです")
                        
                        # Fixed Defaults based on user request (2x4)
                        default_1st = top_horses['馬 番'].iloc[:2].tolist() # Top 2
                        default_2nd = top_horses['馬 番'].iloc[:4].tolist() # Top 4
                        
                        all_nums = processed_df['馬 番'].tolist()
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            sel_1st = st.multiselect(f"{i+1}R: 1着候補", all_nums, default=default_1st, key=f"tu_1st_{i}")
                        with c2:
                            sel_2nd = st.multiselect(f"{i+1}R: 2着候補", all_nums, default=default_2nd, key=f"tu_2nd_{i}")
                        
                        # Calculate Race Combinations (Umatan Formation)
                        # Logic: sum(1 for h1 in sel_1st for h2 in sel_2nd if h1 != h2)
                        race_points = sum(1 for h1 in sel_1st for h2 in sel_2nd if h1 != h2)
                        
                        st.markdown(f"**点数:** {race_points}点")
                        total_combinations *= race_points
                        
                        # Store summary text
                        h_map = dict(zip(processed_df['馬 番'], processed_df['馬名']))
                        summary_txt = f"**{race['number']}R**: 1着[{','.join(sel_1st)}] → 2着[{','.join(sel_2nd)}]"
                        prediction_summaries.append(summary_txt)
                        
                        st.markdown("---")

        # 3. Final Summary
        st.subheader("3. 買い目まとめ")
        st.success(f"**合計点数: {total_combinations}点**")
        cost_50 = total_combinations * 50
        cost_100 = total_combinations * 100
        
        st.metric("推定購入金額 (50円/点)", f"{cost_50:,}円")
        st.metric("推定購入金額 (100円/点)", f"{cost_100:,}円")
        
        st.markdown("#### 構成")
        for s in prediction_summaries:
            st.write(s)

        st.warning("⚠️ トリプル馬単は50円から購入可能です（SPAT4）。オッズによるガミ（トリガミ）に注意してください。")


# -------------------------------------------------------------
# WIN5 (JRA) Logic
# -------------------------------------------------------------
def render_win5_section(target_races, mode_val):
    """
    WIN5用の予想セクション
    5レース分の予想を一括で行い、買い目を生成する
    """
    st.markdown("### 👑 WIN5 (5重勝単勝式) 予想")
    st.info("💡 **機能説明**: 指定した5レース（通常は各場のメインレース付近）の1着馬をすべて的中させる「WIN5」の買い目を生成します。")

    if not target_races or len(target_races) < 5:
        st.error("⚠️ レース情報が不足しています。少なくとも5レース必要です。")
        return

    # 1. Race Selection
    st.subheader("1. 対象レースの選択")
    
    # Defaults
    sorted_races = sorted(target_races, key=lambda x: int(x['number']) if str(x['number']).isdigit() else 0)
    
    # Try to find flagged races
    flagged_races = [r for r in sorted_races if r.get('is_win5', False)]
    
    if len(flagged_races) >= 5:
        default_selections = flagged_races[:5]
    else:
        # Fallback Heuristic
        priority_races = [r for r in sorted_races if str(r['number']) in ['10', '11']]
        priority_races.sort(key=lambda x: int(x['number']))
        
        if len(priority_races) >= 5:
             default_selections = priority_races[-5:]
        elif len(priority_races) > 0:
             remainder = [r for r in sorted_races if r not in priority_races]
             needed = 5 - len(priority_races)
             fill = remainder[-needed:] if len(remainder) >= needed else remainder
             default_selections = fill + priority_races
             default_selections.sort(key=lambda x: int(x['number']))
        else:
             default_selections = sorted_races[-5:] if len(sorted_races) >= 5 else sorted_races
    
    # Get all distinct venues from target_races
    all_venues = sorted(list(set([r['venue'] for r in target_races])))
    
    cols_sel = st.columns(5)
    selected_races_indices = []
    
    for i in range(5):
        with cols_sel[i]:
            st.markdown(f"**{i+1}レース目**")
            
            # 1. Determine Default for this slot
            def_race = default_selections[i] if i < len(default_selections) else sorted_races[0]
            
            # 2. Select Venue
            def_venue_idx = all_venues.index(def_race['venue']) if def_race['venue'] in all_venues else 0
            sel_venue = st.selectbox("会場", all_venues, index=def_venue_idx, key=f"win5_v{i}", label_visibility="collapsed")
            
            # 3. Filter Races by Venue
            venue_races = [r for r in sorted_races if r['venue'] == sel_venue]
            if not venue_races: venue_races = [def_race] # Fallback
            
            # 4. Select Race
            race_opts = [f"{r['number']}R: {r['name']}" for r in venue_races]
            
            # Try to match default race if venue wasn't changed
            if def_race['venue'] == sel_venue:
                 def_label = f"{def_race['number']}R: {def_race['name']}"
                 def_race_idx = race_opts.index(def_label) if def_label in race_opts else 0
            else:
                 def_race_idx = 0
            
            sel_label = st.selectbox("レース", race_opts, index=def_race_idx, key=f"win5_r{i}", label_visibility="collapsed")
            
            found = next((r for r in venue_races if f"{r['number']}R: {r['name']}" == sel_label), None)
            if found: selected_races_indices.append(found)

    # Session state key for WIN5
    if 'win5_active' not in st.session_state:
        st.session_state['win5_active'] = False

    if st.button("🚀 WIN5 予想を開始", type="primary"):
        st.session_state['win5_active'] = True
        
    if st.session_state['win5_active']:
        if st.button("🔄 リセット / 閉じる"):
            st.session_state['win5_active'] = False
            st.rerun()

        model = load_model(mode_val)
        model_meta = load_model_metadata(mode_val)
        stats = load_stats(mode_val)
        
        if not model:
            st.error("モデルの読み込みに失敗しました。")
            return

        st.markdown("---")
        st.subheader("2. 各レースの分析・買い目構築")

        results_container = st.container()
        
        total_combinations = 1
        prediction_summaries = []

        with st.spinner("5レース分のデータを分析中..."):
            history_df_cache = load_history_csv(mode_val) 
            
            for i, race in enumerate(selected_races_indices):
                with results_container:
                    st.markdown(f"#### {i+1}戦目: {race['venue']}{race['number']}R {race['name']}")
                    
                    df_race = auto_scraper.scrape_shutuba_data(race['id'], mode=mode_val, history_df=history_df_cache)
                    if df_race is None or df_race.empty:
                        st.error(f"データの取得に失敗: {race['id']}")
                        return

                    processed_df = predict_race_logic(df_race, model, model_meta, stats=stats, mode=mode_val)
                    
                    if processed_df is not None:
                        # 1. Restore AI Score
                        processed_df['AIスコア(%)'] = processed_df['AI_Prob'] * 100

                        # 2. Prepare D-Index
                        if 'D_Index' in processed_df.columns:
                            processed_df['D指数'] = processed_df['D_Index']
                        else:
                            processed_df['D指数'] = processed_df['AIスコア(%)']
                            
                         # 3. Add Info Columns (Compatibility & History)
                        # Map internal names to display names AND convert to 0-10 score (Higher is Better)
                        # Logic matches individual analysis: 10 - (avg_rank / 2)
                        def convert_compat_score(x):
                            if pd.isna(x): return 5.0
                            return max(0, min(10, 10 - (x / 2)))

                        if 'jockey_compatibility' in processed_df.columns:
                            processed_df['騎手適性度'] = processed_df['jockey_compatibility'].apply(convert_compat_score).round(1)
                        if 'distance_compatibility' in processed_df.columns:
                            processed_df['距離適性度'] = processed_df['distance_compatibility'].apply(convert_compat_score).round(1)
                        if 'course_compatibility' in processed_df.columns:
                            processed_df['コース適性度'] = processed_df['course_compatibility'].apply(convert_compat_score).round(1)
                            
                        if 'weighted_avg_speed' in processed_df.columns:
                             processed_df['平均スピード'] = processed_df['weighted_avg_speed'].round(1)

                        if 'past_1_rank' in processed_df.columns:
                            processed_df['前走着順'] = processed_df['past_1_rank'].fillna('-')
                            
                        # Odds
                        if '単勝' in processed_df.columns:
                            processed_df['現在オッズ'] = pd.to_numeric(processed_df['単勝'], errors='coerce').fillna(0.0)
                        
                        # Confidence
                        processed_df['信頼度'] = processed_df.apply(
                            lambda row: calculate_confidence_score(row, row['AI_Prob'], model_meta), axis=1
                        )
                        
                        # Sort
                        processed_df = processed_df.sort_values("D指数", ascending=False)
                        
                        # Mark & Adj EV
                        processed_df['予想印'] = ""
                        if '現在オッズ' in processed_df.columns:
                             processed_df['調整後期待値'] = (processed_df['AI_Prob'] * processed_df['現在オッズ']) - 1.0
                        else:
                             processed_df['調整後期待値'] = 0.0

                        # Gap
                        gap = 0.0
                        if len(processed_df) >= 2:
                            gap = processed_df.iloc[0]['D指数'] - processed_df.iloc[1]['D指数']
                        
                        # Display
                        st.write(f"**GAP値:** {gap:.1f}")
                        
                        # Create Pedigree Column
                        if 'father' in processed_df.columns and 'mother' in processed_df.columns:
                             processed_df['血統'] = processed_df.apply(
                                 lambda r: f"{r['father']} / {r['mother']}" + (f" ({r['bms']})" if pd.notna(r.get('bms')) else ""), 
                                 axis=1
                             )
                        else:
                             processed_df['血統'] = "-"
                        
                        cols_show = ['枠', '馬 番', '馬名', '予想印', 'D指数', 'AIスコア(%)', '信頼度', '現在オッズ', '調整後期待値']
                        for col in ['騎手適性度', 'コース適性度', '距離適性度', '平均スピード', '前走着順']:
                            if col in processed_df.columns:
                                cols_show.append(col)
                        cols_show.append('血統')
                                
                        st.data_editor(
                            processed_df[cols_show],
                            height=300,
                            hide_index=True,
                            column_config={
                                "AIスコア(%)": st.column_config.ProgressColumn("AI勝率", format="%d%%", min_value=0, max_value=100),
                                "D指数": st.column_config.ProgressColumn("D指数", format="%.1f", min_value=0, max_value=100),
                                "信頼度": st.column_config.NumberColumn("信頼度", format="%d%%"),
                                "予想印": st.column_config.SelectboxColumn("予想印", options=["", "◎", "◯", "▲", "△", "✕"], required=False, width="small"),
                                "調整後期待値": st.column_config.NumberColumn("調整後期待値", format="%.2f"),
                                "平均スピード": st.column_config.NumberColumn("平均スピード", format="%.1f m/s"),
                                "騎手適性度": st.column_config.ProgressColumn("騎手適性", format="%.1f", min_value=0, max_value=10),
                                "コース適性度": st.column_config.ProgressColumn("コース適性", format="%.1f", min_value=0, max_value=10),
                                "距離適性度": st.column_config.ProgressColumn("距離適性", format="%.1f", min_value=0, max_value=10),
                            },
                             key=f"win5_editor_{race['id']}_{i}"
                        )
                        
                        # === Data Missing Alerts (WIN5) ===
                        edited_df = processed_df # Use processed_df as source
                        
                        def to_circled(n):
                            try:
                                n_int = int(n)
                                if 1 <= n_int <= 20: return chr(9311 + n_int)
                                return str(n)
                            except: return str(n)

                        unknown_history = []
                        if '前走着順' in edited_df.columns:
                            unknown_history = [f"{to_circled(row['馬 番'])} {row['馬名']}" for _, row in edited_df[edited_df['前走着順'] == 0].iterrows()]
                            
                        unknown_jockey = []
                        hidden_gems = []
                        if '騎手適性度' in edited_df.columns:
                            # 5.0 is the fallback score for missing data
                            jockey_missing_mask = (edited_df['騎手適性度'] == 5.0)
                            unknown_jockey = [f"{to_circled(row['馬 番'])} {row['馬名']}" for _, row in edited_df[jockey_missing_mask].iterrows()]
                            
                            if 'コース適性度' in edited_df.columns and '距離適性度' in edited_df.columns:
                                 potential_mask = (edited_df['コース適性度'] >= 7.0) | (edited_df['距離適性度'] >= 7.0)
                                 hidden_gems = [f"{to_circled(row['馬 番'])} {row['馬名']}" for _, row in edited_df[jockey_missing_mask & potential_mask].iterrows()]
                
                        if unknown_history or unknown_jockey:
                             st.warning("⚠️ 一部の馬にデータ不足があります")
                             cols_alert = st.columns(2)
                             with cols_alert[0]:
                                 if unknown_history:
                                     st.info(f"**初出走・履歴なし**: {', '.join(unknown_history)}")
                             with cols_alert[1]:
                                 if unknown_jockey:
                                     st.info(f"**騎手データ不足**: {', '.join(unknown_jockey)}")
                                 if hidden_gems:
                                      st.success(f"✨ **騎手は未知数ですが、馬の適性は高い**: {', '.join(hidden_gems)}")
                        
                        # WIN5 Formation Logic (Win Only)
                        st.caption("👇 1着候補を選択 (WIN5)")
                        
                        if gap >= 15.0: 
                             st.info(f"🦾 **鉄板** (Gap {gap:.1f}): 1頭抜き推奨")
                        elif gap < 10.0:
                             st.warning(f"🌪️ **混戦** (Gap {gap:.1f}): 複数頭推奨")
                        else: 
                             st.success(f"⚖️ **標準** (Gap {gap:.1f}): 上位拮抗")
                        
                        # Defaults
                        if gap >= 15.0:
                            default_win = processed_df['馬 番'].iloc[:1].tolist()
                        elif gap < 10.0:
                             default_win = processed_df['馬 番'].iloc[:3].tolist()
                        else:
                             default_win = processed_df['馬 番'].iloc[:2].tolist()

                        all_nums = processed_df['馬 番'].tolist()
                        sel_win = st.multiselect(f"{i+1}戦目: 1着候補", all_nums, default=default_win, key=f"win5_sel_{i}")
                        
                        count = len(sel_win)
                        st.markdown(f"**点数:** {count}点")
                        total_combinations *= count
                        
                        summary_txt = f"**{i+1}戦目**: [{','.join(sel_win)}]"
                        prediction_summaries.append(summary_txt)
                        
                        st.markdown("---")

        # Final Calculation
        st.subheader("📊 WIN5 買い目集計")
        st.write(f"**総組み合わせ数**: {total_combinations} 通り")
        est_cost = total_combinations * 100
        st.write(f"**推定金額 (100円/点)**: {est_cost:,} 円")
        
        with st.expander("詳細を確認", expanded=True):
            for s in prediction_summaries:
                st.markdown(s)



# --- Admin Menu ---
st.markdown("### 設定")
mode = st.radio("開催モード (Mode)", ["JRA (中央競馬)", "NAR (地方競馬)"], horizontal=True)
mode_val = "JRA" if "JRA" in mode else "NAR"

with st.expander("🛠️ 管理ツール (スケジュール更新など)"):
    col_admin_1, col_admin_2 = st.columns([1, 1])
    with col_admin_1:
         if st.button("📅 レース一覧を更新 (今後1週間)"):
            with st.spinner(f"{mode_val}の最新レース情報を取得中..."):
                success, msg = auto_scraper.scrape_todays_schedule(mode=mode_val)
                if success:
                    st.success(msg)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"エラー: {msg}")
    
    with col_admin_2:
         if st.button("🧠 AIモデルを再読み込み"):
             st.cache_resource.clear()
             st.success("モデルキャッシュをクリアしました。次回予測時に再ロードされます。")

st.markdown("---")

# --- Analysis Mode Selection ---
st.markdown("### 分析モード")
    
    # ------------------------------------------------------------------
    # Analysis Mode Selector
    # ------------------------------------------------------------------
options = ["🔍 個別レース分析", "💎 堅いレースを探す (一括分析)"]
if mode_val == "NAR":
    options.append("🎯 SP: トリプル馬単 (NAR)")
if mode_val == "JRA":
     options.append("👑 WIN5 (JRA)")

options.append("📊 過去のレース分析 (データベース)")

analysis_mode = st.radio("機能を選択", options, horizontal=True)

st.markdown("---")

# --- Race Selection ---
st.subheader("📍 レース選択")

schedule_data = load_schedule_data(mode=mode_val)
race_id = None

if schedule_data and "races" in schedule_data:
    races = schedule_data['races']
    
    # 1. Filter by Date
    dates = sorted(list(set([r.get('date', 'Unknown') for r in races])))
    
    if analysis_mode == "🔍 個別レース分析":
        # Layout columns for selection
        col_date, col_venue, col_race = st.columns(3)
        
        with col_date:
             selected_date = st.selectbox("1. 日付を選択", dates)
        
        # Filter races by date
        todays_races = [r for r in races if r.get('date') == selected_date]
        
        if todays_races:
            # 2. Filter by Venue
            venues = sorted(list(set([r['venue'] for r in todays_races])))
            
            with col_venue:
                selected_venue = st.selectbox("2. 開催地を選択", venues)
                
            # Filter races by venue
            venue_races = [r for r in todays_races if r['venue'] == selected_venue]
            
            # 3. Select Race
            # Sort by race number
            venue_races.sort(key=lambda x: int(x['number']) if str(x['number']).isdigit() else 0)
            
            race_options = {f"{r['number']}R: {r['name']}": r['id'] for r in venue_races}
            
            with col_race:
                selected_label = st.selectbox("3. レースを選択", list(race_options.keys()))
                if selected_label:
                    race_id = race_options[selected_label]
        else:
            st.warning(f"{selected_date} のレースはありません。")

    elif analysis_mode == "🎯 SP: トリプル馬単 (NAR)":
        col_date, col_venue_tu = st.columns([1, 2])
        with col_date:
             selected_date = st.selectbox("1. 日付を選択", dates)
        
        todays_races = [r for r in races if r.get('date') == selected_date]
        
        if todays_races:
             # SPAT4 Loto対象場のみ抽出
             valid_tu_venues = ['門別', '浦和', '船橋', '大井', '川崎']
             venues = sorted(list(set([r.get('venue', 'Unknown') for r in todays_races if r.get('venue') in valid_tu_venues])))
             
             if not venues:
                 with col_venue_tu:
                     st.warning("対象開催なし (南関・門別のみ)")
             else:
                 with col_venue_tu:
                     selected_venue = st.selectbox("2. 開催地を選択 (対象場)", venues)
                 
                 venue_races = [r for r in todays_races if r['venue'] == selected_venue]
                 if venue_races:
                     render_triple_umatan_section(venue_races, mode_val)
                 else:
                     st.warning("レースがありません。")
        else:
             st.warning(f"{selected_date} のレースはありません。")

    elif analysis_mode == "👑 WIN5 (JRA)":
        st.info("💡 **WIN5**: JRAの指定5レースを予想します。")
        col_date, col_venue_multi = st.columns([1, 2])
        with col_date:
             selected_date = st.selectbox("1. 日付を選択", dates)
        
        # JRA Venues
        jra_venues = ['東京', '中山', '京都', '阪神', '新潟', '福島', '中京', '小倉', '札幌', '函館']
        
        todays_races = [r for r in races if r.get('date') == selected_date]
        
        # Filter for JRA main venues if possible, or just all races for that day
        # WIN5 usually involves 5 races, potentially across venues.
        jra_day_races = [r for r in todays_races if r['venue'] in jra_venues]
        
        if not jra_day_races:
             st.warning(f"{selected_date} のJRA開催レース（主要場）が見つかりません。")
        else:
             # Just pass all JRA races for that day to the renderer
             # User can select any 5 from them.
             
             # Show venues available
             avail_venues = list(set([r['venue'] for r in jra_day_races]))
             st.write(f"開催場: {', '.join(avail_venues)}")
             
             # Sort logic for default selection inside renderer is 'Last 5'.
             # Pass all races sorted by time/number?
             # Auto-scraper data might not have time sorted, but 'number' is there.
             
             render_win5_section(jra_day_races, mode_val)

    elif analysis_mode == "💎 堅いレースを探す (一括分析)":
        st.info("💡 **機能説明**: 指定した日の全レースをAIが分析し、信頼度が高い「堅いレース」のみを抽出します。")
        
        col_date, col_venue_multi = st.columns([1, 2])
        with col_date:
             selected_date = st.selectbox("1. 日付を選択", dates)
        
        todays_races = [r for r in races if r.get('date') == selected_date]
        if todays_races:
            venues = sorted(list(set([r.get('venue', 'Unknown') for r in todays_races])))
            
            with col_venue_multi:
                 selected_venues = st.multiselect("2. 開催地を選択 (空欄で全会場)", venues, default=venues)
            
            target_races = [r for r in todays_races if not selected_venues or r.get('venue') in selected_venues]
            st.write(f"対象レース数: {len(target_races)} レース")
            
            confidence_threshold = st.slider("信頼度フィルター (これ以上の信頼度のレースを表示)", 0, 100, 70)
            use_odds_bias_batch = st.checkbox("現在オッズを加味する (推奨)", value=True, help="人気馬のスコアを上げ、不人気馬を下げます")

            if st.button("🚀 一括分析を開始する", type="primary"):
                 if not target_races:
                     st.warning("対象レースがありません。")
                 else:
                     with st.spinner("モデルを読み込み中..."):
                         # from app.public_app import load_model, load_model_metadata
                         # from app.public_app import load_model, load_model_metadata
                         # from app.public_app import load_model, load_model_metadata
                         model = load_model(mode_val)
                         model_meta = load_model_metadata(mode_val)
                         stats = load_stats(mode_val)

                     
                     if not model:
                         st.error("モデルの読み込みに失敗しました。")
                     else:
                         results_container = st.container()
                         progress_bar = st.progress(0)
                         status_text = st.empty()
                         
                         solid_races_data = []
                         
                         for i, race in enumerate(target_races):
                             r_name = f"{race['venue']}{race['number']}R: {race['name']}"
                             status_text.text(f"分析中 ({i+1}/{len(target_races)}): {r_name}...")
                             
                             try:
                                 # 1. Scrape with cached history
                                 if i > 0: time.sleep(1) 
                                 history_df_cache = load_history_csv(mode_val)
                                 df_race = auto_scraper.scrape_shutuba_data(race['id'], mode=mode_val, history_df=history_df_cache)
                                 
                                 if df_race is not None and not df_race.empty:
                                     # 2. Predict

                                     processed_df = predict_race_logic(df_race, model, model_meta, stats=stats, mode=mode_val)
                                    
                                     # Odds Bias (Batch Mode)
                                     if use_odds_bias_batch and processed_df is not None and '単勝' in processed_df.columns:
                                         try:
                                             # Local helper or lambda
                                             calc_prob = lambda x: 0.8 / float(x) if (str(x).replace('.','',1).isdigit() and float(x) > 0) else 0
                                             
                                             processed_df['Implied_Prob'] = processed_df['単勝'].apply(calc_prob)
                                             # Blend: AI 70%, Market 30%
                                             alpha = 0.7
                                             processed_df['AI_Prob_Blended'] = (processed_df['AI_Prob'] * alpha) + (processed_df['Implied_Prob'] * (1 - alpha))
                                             processed_df['AI_Score'] = (processed_df['AI_Prob_Blended'] * 100).astype(int)
                                             
                                             # Recalculate D_Index using New AI Score
                                             # D_Index = AI(30%) + Compat(60%) + Blood(10%)
                                             # We need to ensure Compat_Index and Bloodline_Index exist
                                             if 'Compat_Index' in processed_df.columns and 'Bloodline_Index' in processed_df.columns:
                                                 processed_df['D_Index'] = (processed_df['AI_Score'] * 0.3) + (processed_df['Compat_Index'] * 0.6) + (processed_df['Bloodline_Index'] * 0.1)
                                                 processed_df['D_Index'] = processed_df['D_Index'].clip(1, 99)
                                             
                                         except Exception as e:
                                             # If error (e.g. odds not numeric), skip bias
                                             print(f"Odds bias error in batch: {e}")
                                     
                                     if processed_df is not None:
                                         # 3. Find Top Horses (Top 3) based on D-Index
                                         # User requested D-Index compliance
                                         processed_df = processed_df.sort_values('D_Index', ascending=False)
                                         
                                         # Save
                                         # Initialize basic metrics properly
                                         if processed_df.empty: continue
                                         
                                         top_horse = processed_df.iloc[0]
                                         conf = top_horse.get('D_Index', 0)
                                         
                                         # Calculate Gap (1st - 2nd)
                                         gap = 0.0
                                         gap_2_3 = 0.0
                                         gap_3_4 = 0.0
                                         
                                         if len(processed_df) >= 2:
                                             gap = conf - processed_df.iloc[1].get('D_Index', 0)
                                         
                                         if len(processed_df) >= 3:
                                             gap_2_3 = processed_df.iloc[1].get('D_Index', 0) - processed_df.iloc[2].get('D_Index', 0)
                                             
                                         if len(processed_df) >= 4:
                                             gap_3_4 = processed_df.iloc[2].get('D_Index', 0) - processed_df.iloc[3].get('D_Index', 0)
                                         
                                         # Calculate Top 5 Dispersion (Standard Deviation)
                                         top5_df = processed_df.head(5)
                                         top5_std = top5_df['D_Index'].std() if len(top5_df) > 1 else 0.0

                                         # Construct Multi-Horse String (Picks)
                                         picks_str = []
                                         marks = ["◎", "◯", "▲", "△", "☆", "注"]
                                         
                                         for rank in range(min(6, len(processed_df))):
                                             h = processed_df.iloc[rank]
                                             m = marks[rank]
                                             h_num = h.get('馬 番')
                                             if pd.isna(h_num): h_num = h.get('馬番', '')
                                             
                                             c_num = str(h_num) 
                                             # Try circles if simple int
                                             try:
                                                 val = int(float(h_num))
                                                 if 1 <= val <= 20: c_num = chr(9311 + val)
                                                 else: c_num = f"({val})"
                                             except: pass
                                             
                                             d_val = f"{h.get('D_Index',0):.1f}"
                                             picks_str.append(f"{m} {c_num} {h['馬名']} (D:{d_val})")
                                         
                                         picks_display = " / ".join(picks_str)

                                         # Odds Metrics
                                         odds_metrics = {}
                                         if '単勝' in processed_df.columns:
                                            try:
                                                valid_odds = pd.to_numeric(processed_df['単勝'], errors='coerce').dropna().sort_values().tolist()
                                                if len(valid_odds) >= 2: 
                                                    odds_metrics['Gap 1-2'] = valid_odds[1] - valid_odds[0]
                                                else: odds_metrics['Gap 1-2'] = 0.0
                                                
                                                if len(valid_odds) >= 3:
                                                    odds_metrics['Gap 2-3'] = valid_odds[2] - valid_odds[1]
                                                    odds_metrics['Std 1-2-3'] = np.std(valid_odds[:3], ddof=1)
                                                else:
                                                    odds_metrics['Gap 2-3'] = 0.0
                                                    odds_metrics['Std 1-2-3'] = 0.0
                                                    
                                                if len(valid_odds) >= 6:
                                                     odds_metrics['Std 1-6'] = np.std(valid_odds[:6], ddof=1)
                                                else:
                                                     odds_metrics['Std 1-6'] = 0.0
                                            except: pass

                                         if conf >= confidence_threshold:
                                             # Consolidate Data
                                             r_dict = {
                                                 "race_name": race['name'],
                                                 "venue": race['venue'],
                                                 "R": f"{race['number']}R",
                                                 "picks": picks_display,
                                                 "top_horse": top_horse['馬名'],
                                                 "confidence": conf,
                                                 "gap": gap,
                                                 "gap_2_3": gap_2_3,
                                                 "gap_3_4": gap_3_4,
                                                 "top_score": top_horse.get('AI_Score', 0),
                                                 "odds_1": top_horse.get('単勝', 0),
                                                 "_gap_val": gap
                                             }
                                             r_dict.update(odds_metrics)
                                             solid_races_data.append(r_dict)
                             
                             except Exception as e:
                                 print(f"Error analyzing {race['id']}: {e}")
                                 
                             progress_bar.progress((i + 1) / len(target_races))
                         
                         status_text.success(f"完了！ {len(target_races)}レース中、条件を満たすレースは {len(solid_races_data)} 件でした。")
                         
                         if solid_races_data:
                             st.markdown("### 💎 堅いレース候補 (2位との差が大きい順)")
                             res_df = pd.DataFrame(solid_races_data)
                             res_df = res_df.sort_values('_gap_val', ascending=False)
                             
                             # Rename and Reorder for Display/Export
                             rename_map = {
                                 "venue": "開催地", 
                                 "R": "R", 
                                 "race_name": "レース名", 
                                 "picks": "予想 (D指数)", 
                                 "top_horse": "本命馬", 
                                 "confidence": "TOP D指数", 
                                 "gap": "2位差 (D指数)", 
                                 "odds_1": "単勝", 
                                 "Gap 1-2": "オッズ差 1-2", 
                                 "Gap 2-3": "オッズ差 2-3",
                                 "Std 1-2-3": "オッズ偏差 (1-3)", 
                                 "Std 1-6": "オッズ偏差 (1-6)", 
                                 "top_score": "AIスコア"
                             }
                             
                             res_df = res_df.rename(columns=rename_map)
                             
                             # Define Order
                             display_cols = [
                                 "開催地", "R", "レース名", "予想 (D指数)", "本命馬", 
                                 "TOP D指数", "2位差 (D指数)", "単勝", 
                                 "オッズ差 1-2", "オッズ差 2-3", "オッズ偏差 (1-3)", "オッズ偏差 (1-6)", "AIスコア"
                             ]
                             # Filter to available columns
                             final_cols = [c for c in display_cols if c in res_df.columns]
                             res_df = res_df[final_cols]
                             
                             if not res_df.empty:
                                  st.dataframe(
                                      res_df,
                                      column_config={
                                          "TOP D指数": st.column_config.ProgressColumn("TOP D指数", format="%.1f", min_value=0, max_value=100),
                                          "2位差 (D指数)": st.column_config.NumberColumn("2位差 (D指数)", format="%.1f"),
                                          "オッズ差 1-2": st.column_config.NumberColumn("オッズ差 1-2", format="%.1f"),
                                          "オッズ差 2-3": st.column_config.NumberColumn("オッズ差 2-3", format="%.1f"),
                                          "オッズ偏差 (1-3)": st.column_config.NumberColumn("オッズ偏差 (1-3)", format="%.2f"),
                                          "オッズ偏差 (1-6)": st.column_config.NumberColumn("オッズ偏差 (1-6)", format="%.2f"),
                                          "AIスコア": st.column_config.NumberColumn("AIスコア", format="%d"),
                                          "単勝": st.column_config.NumberColumn("単勝", format="%.1f")
                                      },
                                      hide_index=True
                                  )

                                  # --- Betting Recommendations ---
                                  st.markdown("---")
                                  st.markdown("### 🎯 おすすめの賭け方 (Beta)")
                                  
                                  c_gap = '2位差 (D指数)'
                                  c_std3 = 'オッズ偏差 (1-3)'
                                  c_std6 = 'オッズ偏差 (1-6)'
                                  
                                  # Filter logic
                                  df_rec = res_df.copy()
                                  
                                  mask_priority = (df_rec[c_gap] > 5.0) & (df_rec[c_std3] < 1.5)
                                  df_priority = df_rec[mask_priority]

                                  mask_dividend = (df_rec[c_std6] < 4.0)
                                  df_dividend = df_rec[mask_dividend]

                                  mask_iron = (df_rec[c_gap] > 10.0)
                                  df_iron = df_rec[mask_iron]
                                  
                                  cols_show_rec = ['開催地', 'R', 'レース名', '本命馬', '予想 (D指数)']

                                  st.markdown("#### 🔥 【最優先】的中率・利益の柱")
                                  st.caption("推奨: ワイド4頭BOX ＋ 三連複4頭BOX")
                                  st.info("D指数上位4頭の決着を完全に捉えます。最も安定感があり、多重的中（トリプル的中）が発生しやすい最強の布陣です。")
                                  if not df_priority.empty:
                                      st.success(f"👉 **ワイド4頭BOX ＋ 三連複4頭BOX**")
                                      st.dataframe(df_priority.head(4)[cols_show_rec], hide_index=True)
                                  else:
                                      st.write("該当レースなし")

                                  st.markdown("#### 💰 【高配当】穴馬を含めた爆発力")
                                  st.caption("推奨: 三連複6頭BOX (20点)")
                                  st.info("ワイドよりも三連複に絞ることで、一撃10万馬券クラスを逃さず利益効率を最大化します。（条件: D指数5位・6位に人気薄が含まれる場合推奨）")
                                  if not df_dividend.empty:
                                      st.success(f"👉 **3連複 6頭BOX (20点)**")
                                      st.dataframe(df_dividend.head(6)[cols_show_rec], hide_index=True)
                                  else:
                                      st.write("該当レースなし")

                                  st.markdown("#### 🏰 【鉄板軸】軸馬の絶対的信頼")
                                  st.caption("推奨: ワイド流し ＋ 三連複軸1頭流し")
                                  st.info("軸馬（◎）から相手5頭へ。軸馬が3着以内に入る確率が極めて高いため、相手に人気薄が飛び込んだ際の「ヒモ荒れ」を三連複で高配当に変えます。")
                                  if not df_iron.empty:
                                      st.success(f"👉 **ワイド流し ＋ 三連複軸1頭流し (相手5頭)**")
                                      st.dataframe(df_iron.head(1)[cols_show_rec], hide_index=True)
                                  else:
                                      st.write("該当レースなし")

                                  # New Pattern 8: High Value Win (Gap > 10.0 & Odds >= 3.0)
                                  # New Pattern 8: High Value Win (Gap > 10.0 & Odds >= 3.0)
                                  if '単勝' in df_rec.columns:
                                      # Fix: Ensure odds is numeric for comparison
                                      df_rec['単勝'] = pd.to_numeric(df_rec['単勝'], errors='coerce')
                                      
                                      mask_value_win = (df_rec[c_gap] > 10.0) & (df_rec['単勝'] >= 3.0)
                                      df_value_win = df_rec[mask_value_win]

                                      st.markdown("#### 🌟 【穴勝負】低投資・高配当")
                                      st.caption("推奨: 単勝 ＋ 複勝 (比率1:2)")
                                      st.info("指数1位の穴馬が2・3着に食い込むケースが多いため、複勝を厚めに買うことで「的中したのに外れた」という事態を防ぎ、確実にプラスを拾います。")
                                      if not df_value_win.empty:
                                          st.success(f"👉 **単勝 ＋ 複勝 (比率1:2)**")
                                          st.dataframe(df_value_win[cols_show_rec], hide_index=True)
                                      else:
                                          st.write("該当レースなし")

                                  # New Pattern 1: High Confidence
                                  c_conf = 'TOP D指数'
                                  mask_confident = (df_rec[c_conf] >= 80.0)
                                  df_confident = df_rec[mask_confident]

                                  st.markdown("#### 💎 【確勝級】圧倒的指数差")
                                  st.caption("推奨: 単勝一点 ＋ 三連複軸1頭流し")
                                  st.info("D指数が2位以下を大きく引き離している場合（差が10以上推奨）、単勝で確実に資金を回収しつつ、三連複でボーナスを狙う戦略です。")
                                  if not df_confident.empty:
                                      st.success(f"👉 **単勝一点 ＋ 三連複軸1頭流し**")
                                      st.dataframe(df_confident[cols_show_rec], hide_index=True)
                                  else:
                                      st.write("該当レースなし")

                                  # New Pattern 2: Chaos
                                  mask_chaos = (df_rec[c_gap] < 3.0) & (df_rec[c_conf] < 70.0)
                                  df_chaos = df_rec[mask_chaos]

                                  st.markdown("#### 🌀 【波乱含み・BOX推奨】")
                                  st.caption("条件: 2位差 < 3.0 かつ TOP D指数 < 70.0 （混戦で軸が決まらない）")
                                  if not df_chaos.empty:
                                      st.warning(f"👉 **馬連・3連複のBOX（上位4〜5頭）で高配当狙い**")
                                      st.dataframe(df_chaos[cols_show_rec], hide_index=True)
                                  else:
                                      st.write("該当レースなし")

                                  # New Pattern 6: Duel (2 Strong Horses)
                                  c_gap_2_3 = 'gap_2_3'
                                  # Add columns if not exist
                                  if c_gap_2_3 not in df_rec.columns: df_rec[c_gap_2_3] = 0.0
                                  
                                  mask_duel = (df_rec[c_gap_2_3] > 10.0)
                                  df_duel = df_rec[mask_duel]

                                  st.markdown("#### ⚔️ 【一騎打ちムード】")
                                  st.caption("条件: 2位と3位のD指数差 > 10.0 （2強が突出している）")
                                  if not df_duel.empty:
                                      st.info(f"👉 **馬連・ワイド 1-2 一点勝負**")
                                      st.dataframe(df_duel[cols_show_rec], hide_index=True)
                                  else:
                                      st.write("該当レースなし")

                                  # New Pattern 7: Top 3 (3 Strong Horses)
                                  c_gap_3_4 = 'gap_3_4'
                                  if c_gap_3_4 not in df_rec.columns: df_rec[c_gap_3_4] = 0.0
                                  
                                  mask_top3 = (df_rec[c_gap_3_4] > 10.0)
                                  df_top3 = df_rec[mask_top3]

                                  st.markdown("#### 🔺 【3強対決】")
                                  st.caption("条件: 3位と4位のD指数差 > 10.0 （上位3頭が突出）")
                                  if not df_top3.empty:
                                      st.info(f"👉 **3連複 3頭BOX (1点買い)**")
                                      st.dataframe(df_top3[cols_show_rec], hide_index=True)
                                  else:
                                      st.write("該当レースなし")
                                  
                                  st.markdown("---")
                             else:
                                  st.warning("条件を満たす堅いレースは見つかりませんでした。")
                         else:
                             st.warning("条件を満たす堅いレースは見つかりませんでした。")
        else:
            st.warning(f"{selected_date} のレースはありません。")

    elif analysis_mode == "📊 過去のレース分析 (データベース)":
        st.markdown("### 📊 過去のレース分析: 堅いレースの抽出")
        st.info("過去の全レースデータから、オッズのばらつきや人気差を計算し、特に「堅い」（予測しやすい）レースを抽出します。")

        # Helper: Load Data Cached
        @st.cache_data(ttl=3600)
        def load_analysis_data(path):
            return pd.read_parquet(path)

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if mode_val == "NAR":
             db_path = os.path.join(project_root, "data", "raw", "database_nar.parquet")
        else:
             db_path = os.path.join(project_root, "data", "raw", "database.parquet")

        if not os.path.exists(db_path):
             st.error(f"データベースが見つかりません: {db_path}")
        else:
             # Filters UI
             try:
                 # Load just to get metadata for filters (Cached)
                 df_raw = load_analysis_data(db_path)
                 
                 # Prepare Filter Options
                 if '日付' in df_raw.columns:
                     df_raw['日付'] = pd.to_datetime(df_raw['日付'], errors='coerce')
                     valid_dates = df_raw['日付'].dropna()
                     if not valid_dates.empty:
                         min_date = valid_dates.min().date()
                         max_date = valid_dates.max().date()
                     else:
                         min_date = datetime.now().date()
                         max_date = datetime.now().date()
                 else:
                     min_date = datetime.now().date()
                     max_date = datetime.now().date()

                 all_venues = sorted(df_raw['開催地'].unique().astype(str)) if '開催地' in df_raw.columns else []

                 # Layout
                 col_f1, col_f2 = st.columns(2)
                 with col_f1:
                     date_range = st.date_input(
                         "日付範囲 (Date Range)",
                         value=(min_date, max_date),
                         min_value=min_date,
                         max_value=max_date
                     )
                 with col_f2:
                     sel_venues = st.multiselect("開催地 (Venue)", all_venues, default=[])

                 if st.button("🔍 条件で分析開始"):
                     with st.spinner("データをフィルタリング・分析中..."):
                         df_target = df_raw.copy()
                         
                         # Apply Filters
                         if isinstance(date_range, tuple) and len(date_range) == 2:
                             start, end = date_range
                             msk = (df_target['日付'].dt.date >= start) & (df_target['日付'].dt.date <= end)
                             df_target = df_target[msk]
                         
                         if sel_venues:
                             df_target = df_target[df_target['開催地'].isin(sel_venues)]
                             
                         if df_target.empty:
                             st.warning("条件に一致するデータがありません。")
                         else:
                             # Import Analysis Module
                             import ml.analysis_hard_race as analysis_hard_race
                             importlib.reload(analysis_hard_race)
                             
                             # Calculate Metrics
                             metrics_df = analysis_hard_race.calculate_hard_race_metrics(df_target)
                             
                             if metrics_df.empty:
                                 st.warning("分析可能なデータが不足しています（オッズ情報など）。")
                             else:
                                 # Merge Metadata
                                 meta_cols = ['race_id', '日付', '開催地', 'レース名']
                                 avail_meta = [c for c in meta_cols if c in df_target.columns]
                                 meta_df = df_target[avail_meta].drop_duplicates(subset=['race_id'])
                                 
                                 result_df = pd.merge(metrics_df, meta_df, on='race_id', how='left')
                                 # Format Date back to string for display if needed, but dataframe handles it.
                                 result_df = result_df.sort_values('odds_gap_1_2', ascending=False)
                                 
                                 st.session_state['hist_analysis_result'] = result_df
                                 st.success(f"分析完了: {len(result_df)} レース")

             except Exception as e:
                 st.error(f"データ読み込みエラー: {e}")

        if 'hist_analysis_result' in st.session_state:
             res_df = st.session_state['hist_analysis_result']
             st.markdown("#### 分析結果")
             st.caption("1番人気と2番人気のオッズ差が大きい順に表示")
             st.dataframe(
                 res_df,
                 column_config={
                     "odds_gap_1_2": st.column_config.NumberColumn("Gap 1-2", format="%.1f"),
                     "odds_gap_2_3": st.column_config.NumberColumn("Gap 2-3", format="%.1f"),
                     "odds_std_1_2_3": st.column_config.NumberColumn("Std 1-2-3", format="%.2f"),
                     "odds_std_1_6": st.column_config.NumberColumn("Std 1-6", format="%.2f"),
                 },
                 use_container_width=True
             )
             csv = res_df.to_csv(index=False).encode('utf-8')
             st.download_button("📥 CSV形式でダウンロード", csv, "hard_race.csv", "text/csv", key='dl-hist')
        
else:
    st.warning("レースデータがありません。管理者メニューから更新ボタンを押してください。")
    # No fallback text input for now to keep it clean, or keep it inside Individual mode if needed.
    # But existing code had it. Let's omitting it for Batch mode safety.
    if analysis_mode == "🔍 個別レース分析":
         race_id = st.text_input("レースID直接入力 (12桁)", value="202305021211")


# Main Analysis
if race_id:
    st.header(f"レース分析: {race_id}")

    # Load Model and Metadata
    model = load_model(mode=mode_val)
    model_meta = load_model_metadata(mode=mode_val)
    stats = load_stats(mode=mode_val)
    last_updated, days_ago = get_data_freshness(mode=mode_val)

    # Display Model Information and Data Freshness
    with st.expander("📊 モデル情報・データ品質", expanded=False):
        if model_meta:
            col_info1, col_info2, col_info3 = st.columns(3)

            with col_info1:
                st.metric(
                    "モデルAUC（予測精度）",
                    f"{model_meta.get('performance', {}).get('auc', 0):.3f}",
                    help="0.5=ランダム、1.0=完全予測。0.75以上が目安"
                )
                st.caption(f"学習データ量: {model_meta.get('data_stats', {}).get('total_records', 0):,}件")

            with col_info2:
                if last_updated:
                    freshness_color = "🟢" if days_ago <= 3 else "🟡" if days_ago <= 7 else "🔴"
                    st.metric(
                        "データ最終更新",
                        f"{days_ago}日前",
                        delta=f"{freshness_color} {last_updated}"
                    )
                else:
                    st.metric("データ最終更新", "不明")

            with col_info3:
                data_size = model_meta.get('data_stats', {}).get('total_records', 0)
                if data_size < 1000:
                    quality = "⚠️ 小規模"
                    quality_help = "データ量が少ないため、予測精度は限定的です"
                elif data_size < 3000:
                    quality = "🟡 中規模"
                    quality_help = "さらにデータを増やすと精度向上が期待できます"
                else:
                    quality = "🟢 十分"
                    quality_help = "十分なデータ量で学習されています"

                st.metric("データ品質", quality, help=quality_help)

            # Warnings
            if model_meta.get('warnings'):
                st.warning("**⚠️ 注意事項:**\n" + "\n".join([f"- {w}" for w in model_meta['warnings']]))
        else:
            st.info("モデルメタデータが見つかりません")

    st.markdown("### 🔮 AI予測設定")
    use_odds_bias = st.checkbox("現在オッズ（人気）を加味してAI評価を補正する", value=True, help="チェックすると、AIの純粋な能力評価に「現在のオッズ（市場の支持）」を30%程度ブレンドします。人気馬のスコアが上がり、不人気馬のスコアが下がります。")

    button_analyze = st.button("🚀 このレースを分析する (データ取得・AI予測)", type="primary", use_container_width=True)

    if button_analyze:
        if not race_id:
             st.error("レースIDが選択されていません。")
        elif not model:
             st.error(f"モデル ({mode_val}) が読み込めませんでした。管理画面で学習を実行するか、モデルファイルを確認してください。")
        else:
            # === 処理フローの可視化 ===
            st.markdown("---")
            st.subheader("🔄 AI予測処理フロー")

            # ステップ表示用のプログレスバー
            progress_bar = st.progress(0)
            status_text = st.empty()

            # ステップ1: データ取得
            status_text.info("**ステップ 1/4:** 出馬表データを取得中...")
            progress_bar.progress(25)
            history_df_cache = load_history_csv(mode_val)
            df = auto_scraper.scrape_shutuba_data(race_id, mode=mode_val, history_df=history_df_cache)

            if df is not None and not df.empty:
                status_text.success("✅ ステップ 1/4: 出馬表データを取得しました")

                # ステップ2-4: AI予測プロセス（共通関数化）
                status_text.info("**ステップ 2-4:** 特徴量計算・AI予測・信頼度算出を実行中...")
                progress_bar.progress(60)
                
                if model:

                    processed_df = predict_race_logic(df, model, model_meta, stats=stats, mode=mode_val)
                    
                    if processed_df is not None:
                         df = processed_df
                         status_text.success("✅ AI分析が完了しました！")
                         progress_bar.progress(100)
                    else:
                         status_text.error("❌ 予測処理中にエラーが発生しました。")
                         df['AI_Prob'] = 0.0
                         df['AI_Score'] = 0.0
                else:
                     status_text.warning("モデルが見つかりません。予測スキップ。")
                     df['AI_Prob'] = 0.0
                     df['AI_Score'] = 0.0

                # 4. Display
                # Store in session state to persist edits
                st.session_state[f'data_{race_id}'] = df

                # 完了メッセージ
                st.markdown("---")
                st.success("🎉 **AI分析が完了しました！** 下記の結果をご確認ください。")
            else:
                st.error("データの取得に失敗しました。")

    # Show Data if available
    if f'data_{race_id}' in st.session_state:
        df_display = st.session_state[f'data_{race_id}'].copy()

        # === レース概要の表示 ===
        st.markdown("---")
        st.subheader("🏇 レース概要")

        # レース基本情報
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            # Try multiple possible column names for venue
            venue = "不明"
            for col in ['会場', 'venue', '競馬場', '場所']:
                if col in df_display.columns and len(df_display) > 0:
                    venue = df_display[col].iloc[0]
                    if pd.notna(venue) and venue != "":
                        break

            # If still unknown, try to extract from race_id (first 4 digits indicate place code)
            if venue == "不明" and race_id and len(race_id) >= 6:
                try:
                    place_code = int(race_id[4:6])
                    place_map = {
                        1: "札幌", 2: "函館", 3: "福島", 4: "新潟", 5: "東京",
                        6: "中山", 7: "中京", 8: "京都", 9: "阪神", 10: "小倉",
                        30: "門別", 35: "盛岡", 36: "水沢", 42: "浦和", 43: "船橋",
                        44: "大井", 45: "川崎", 46: "金沢", 47: "笠松", 48: "名古屋",
                        50: "園田", 51: "姫路", 54: "高知", 55: "佐賀", 3: "帯広"
                    }
                    venue = place_map.get(place_code, "不明")
                except:
                    pass

            st.metric("開催場", venue)
        with col_r2:
            race_name = df_display['レース名'].iloc[0] if 'レース名' in df_display.columns else "不明"
            st.metric("レース名", race_name if len(str(race_name)) < 20 else str(race_name)[:17] + "...")
        with col_r3:
            course_type = df_display['コースタイプ'].iloc[0] if 'コースタイプ' in df_display.columns else "不明"
            distance = df_display['距離'].iloc[0] if '距離' in df_display.columns else "不明"
            st.metric("コース", f"{course_type} {distance}m")
        with col_r4:
            num_horses = len(df_display)
            st.metric("出走頭数", f"{num_horses}頭")

        # --- オッズ加味ロジック (Blended Score) ---
        if use_odds_bias and '単勝' in df_display.columns:
            # 単勝オッズから市場の予測確率（Implied Probability）を算出
            # 控除率を考慮して 0.8 / オッズ とする（標準的）
            def calc_implied_prob(x):
                try:
                    odds = float(x)
                    return 0.8 / odds if odds > 0 else 0
                except:
                    return 0

            df_display['Implied_Prob'] = df_display['単勝'].apply(calc_implied_prob)
            
            # ブレンド (AI: 70%, Market: 30%)
            alpha = 0.7
            df_display['AI_Prob_Blended'] = (df_display['AI_Prob'] * alpha) + (df_display['Implied_Prob'] * (1 - alpha))
            
            # Update AI Score & Confidence
            # スコアは単純に確立*100
            df_display['AI_Score_Raw'] = df_display['AI_Score'] # Keep raw for reference
            df_display['AI_Score'] = (df_display['AI_Prob_Blended'] * 100).astype(int)
            
            # Update Confidence (Simple scaling for now, or keep original? 
            # Updating confidence makes sense as market agreement increases certainty)
            # But let's keep Confidence tied to "Model's Confidence" to avoid confusion?
            # Actually, if we change AI Score, we should probably align Confidence or leave it.
            # User wants "Prediction" to include odds. 
            # Let's update Confidence slightly if Market agrees.
            
            # But for simplicity and safety, let's just update the Score which drives the Ranking.
            # Confidence is "How much we trust this evaluation". If Market agrees, trust goes up?
            # Let's just update AI_Score for ranking.
            
            st.warning("⚠️ **現在オッズ加味モード**: AI評価スコアが市場人気（オッズ）の影響を受けて補正されています。")

        # AI予測サマリー
        if 'AI_Score' in df_display.columns and 'Confidence' in df_display.columns:
            avg_confidence = df_display['Confidence'].mean()
            max_ai_score = df_display['AI_Score'].max()
            st.info(f"📊 **AI予測サマリー**: 最高AI勝率 {max_ai_score}% | 平均信頼度 {avg_confidence:.0f}%")

        # コース特性の詳細表示
        venue = df_display['会場'].iloc[0] if '会場' in df_display.columns else None
        if venue:
            try:
                from ml.venue_characteristics import get_venue_characteristics
                venue_char = get_venue_characteristics(venue)

                if venue_char:
                    st.markdown("#### 🏟️ コース特性")

                    col_c1, col_c2, col_c3, col_c4 = st.columns(4)

                    # 直線距離
                    with col_c1:
                        # Determine Turf or Dirt
                        is_dirt = False
                        if 'コースタイプ' in df_display.columns:
                            course_type = str(df_display['コースタイプ'].iloc[0])
                            if 'ダ' in course_type:
                                is_dirt = True
                        
                        straight = venue_char.get('dirt_straight', 0) if is_dirt else venue_char.get('turf_straight', 0)
                        
                        if straight:
                            straight_label = "長い" if straight > 500 else "短い" if straight < 300 else "標準"
                            surface_label = "ダート" if is_dirt else "芝"
                            st.metric(f"直線距離 ({surface_label})", f"{straight}m", delta=straight_label)
                        else:
                            st.metric("直線距離", "不明")

                    # 勾配（傾斜）
                    with col_c2:
                        slope = venue_char.get('slope', 'normal')
                        slope_map = {
                            'steep': '急坂あり',
                            'moderate': '緩やかな坂',
                            'flat': '平坦',
                            'normal': '標準'
                        }
                        slope_label = slope_map.get(slope, slope)
                        slope_icon = "⛰️" if slope == 'steep' else "🏔️" if slope == 'moderate' else "━"
                        st.metric("勾配（傾斜）", slope_label, delta=slope_icon)

                    # コース幅
                    with col_c3:
                        track_width = venue_char.get('track_width', 'standard')
                        width_map = {
                            'narrow': '小回り',
                            'standard': '標準',
                            'wide': '広いコース'
                        }
                        width_label = width_map.get(track_width, track_width)
                        st.metric("コース幅", width_label)

                    # 外枠有利度
                    with col_c4:
                        outer_advantage = venue_char.get('outer_track_advantage', 1.0)
                        if outer_advantage > 1.05:
                            outer_label = "外枠有利"
                            outer_delta = "↑"
                        elif outer_advantage < 0.95:
                            outer_label = "内枠有利"
                            outer_delta = "↓"
                        else:
                            outer_label = "公平"
                            outer_delta = "="
                        st.metric("枠番傾向", outer_label, delta=outer_delta)

                    # 特性の影響説明
                    with st.expander("💡 このコース特性がEV計算に与える影響", expanded=False):
                        st.markdown(f"""
                        #### 🏟️ {venue}の特性

                        **1. 直線距離: {straight}m ({straight_label})**
                        - 長い直線（500m以上）: 人気馬やや不利 (-5%)、穴馬やや有利 (+5%)
                        - 短い直線（300m未満）: 人気馬有利 (+5%)、穴馬不利 (-5%)
                        - 理由: 長い直線は差し馬に有利、短い直線は逃げ・先行馬に有利

                        **2. 勾配（傾斜）: {slope_label}**
                        - 急坂あり: 人気馬（パワーがある馬）が有利 (+2%)
                        - 理由: 坂を登る際に馬力が必要で、実績馬が優位
                        - 該当競馬場: 中山、阪神など

                        **3. コース幅: {width_label}**
                        - 小回り: 人気馬やや有利 (+3%)
                        - 理由: コーナーが多く、器用さが求められる

                        **4. 枠番傾向: {outer_label}**
                        - 外枠有利な場合: 6-8枠の馬の確率を調整 (×{outer_advantage:.2f})
                        - 内枠有利な場合: 1-3枠の馬の確率を調整

                        ⚠️ これらの調整は期待値(EV)計算時に自動的に適用されています。
                        """)
            except Exception as e:
                pass  # venue_characteristics が利用できない場合はスキップ

        # Prepare Editor DF
        # Columns: Horse, Prob, Odds, Mark
        if 'Odds' not in df_display.columns:
             # Try to get scraped odds if available
             if '単勝' in df_display.columns:
                 df_display['Odds'] = pd.to_numeric(df_display['単勝'], errors='coerce').fillna(0.0)
             else:
                 df_display['Odds'] = 0.0
        
        # course_compatibilityがpredict_race_logicで既に生成されていない場合のみ生成
        if 'course_compatibility' not in df_display.columns:
            # Select appropriate course compatibility
            # If 'コースタイプ' contains '芝', use turf, else dirt
            # Default to turf if unknown
            is_turf_race = True
            if 'コースタイプ' in df_display.columns:
                 # Check first row (all same race)
                 c_type = str(df_display['コースタイプ'].iloc[0])
                 if 'ダ' in c_type:
                     is_turf_race = False

            if is_turf_race:
                 df_display['course_compatibility'] = df_display.get('turf_compatibility', 5.0)
            else:
                 df_display['course_compatibility'] = df_display.get('dirt_compatibility', 5.0)

        # === Migration: Ensure D_Index exists (for cached data from old session) ===
        if 'D_Index' not in df_display.columns:
            if 'AI_Score' in df_display.columns:
                # Recalculate using Pure Compatibility (Rank 1-18 -> Score 100-0)
                def _calc_migration_compat(row):
                     scores = []
                     if pd.notna(row.get('jockey_compatibility')): scores.append(float(row['jockey_compatibility']))
                     if pd.notna(row.get('distance_compatibility')): scores.append(float(row['distance_compatibility']))
                     if pd.notna(row.get('course_compatibility')): scores.append(float(row['course_compatibility']))
                     if not scores: return 50.0 
                     avg_rank = sum(scores) / len(scores)
                     score = (18.0 - avg_rank) / 17.0 * 100
                     return max(0, min(100, score))
                
                compat_idx = df_display.apply(_calc_migration_compat, axis=1)
                df_display['D_Index'] = (df_display['AI_Score'] * 0.1) + (compat_idx * 0.9)
                df_display['D_Index'] = df_display['D_Index'].clip(1, 99)
            else:
                 df_display['D_Index'] = 0.0

        # === 適性スコアを適性度に変換（10点満点、高い方が良い） ===
        # 元の値は「平均着順」（小さい方が良い）
        # 適性度 = 10 - 平均着順（0-10点、高い方が良い）

        for compat_col in ['jockey_compatibility', 'distance_compatibility', 'course_compatibility']:
            if compat_col in df_display.columns:
                # 10 - (値 / 2) でスコア化 (平均着順10.0 -> 5.0点)
                # 1位 -> 9.5点, 18位 -> 1.0点
                df_display[compat_col] = df_display[compat_col].apply(
                    lambda x: max(0, min(10, 10 - (x / 2))) if pd.notna(x) else 5.0
                )

        rename_map = {
            'AI_Score': 'AIスコア(%)',
            'D_Index': 'D指数',
            'Confidence': '信頼度',
            'Odds': '現在オッズ',
            '性齢': '年齢',
            '馬 番': '馬番',
            'jockey_compatibility': '騎手適性度',
            'distance_compatibility': '距離適性度',
            'course_compatibility': 'コース適性度',
            'turf_compatibility': '芝適性度',
            'dirt_compatibility': 'ダート適性度',
            'weighted_avg_speed': '平均スピード',
            'weighted_avg_rank': '平均着順',
            'jockey_win_rate': '騎手勝率',
            'stable_win_rate': '厩舎勝率',
            'good_condition_avg': '良馬場適性',
            'heavy_condition_avg': '重馬場適性',
            'trend_rank': '着順トレンド',
            'growth_factor': '成長係数',
            'past_1_rank': '前走着順',
            'past_2_rank': '前々走着順',
            'past_3_rank': '3走前着順'
        }

        # Ensure all display columns exist
        defaults = {
            'jockey_compatibility': 10.0,
            'distance_compatibility': 10.0,
            'course_compatibility': 10.0,
            'turf_compatibility': 10.0,
            'dirt_compatibility': 10.0,
            'weighted_avg_speed': 16.0,
            'weighted_avg_rank': 7.0,
            'jockey_win_rate': 0.1,
            'stable_win_rate': 0.1,
            'good_condition_avg': 10.0,
            'heavy_condition_avg': 10.0,
            'trend_rank': 0.0,
            'growth_factor': 1.0,
            'Confidence': 50,
            'past_1_rank': 0,
            'past_2_rank': 0,
            'past_3_rank': 0,
            'Bloodline_Index': 50.0
        }
        for c, v in defaults.items():
            if c not in df_display.columns:
                df_display[c] = v

        # Add Mark column BEFORE selecting display columns
        if '予想印' not in df_display.columns:
            df_display['予想印'] = ""
            
        # Create Pedigree Column
        if 'father' in df_display.columns and 'mother' in df_display.columns:
             df_display['血統'] = df_display.apply(
                 lambda r: f"{r['father']} / {r['mother']}" + (f" ({r['bms']})" if pd.notna(r.get('bms')) else ""), 
                 axis=1
             )
        else:
             df_display['血統'] = "-"

        # Display columns with 予想印 next to 馬名（基本情報+主要適性度）
        display_cols = [
            '枠', '馬 番', '馬名', '予想印', '性齢',
            'D_Index', 'AI_Score', 'Confidence', 'Odds',
            'jockey_compatibility', 'course_compatibility', 'distance_compatibility',
            'Bloodline_Index',
            'weighted_avg_rank', 'weighted_avg_speed', 'past_1_rank', 'past_2_rank', '血統'
        ]


        edited_df = df_display[display_cols].copy()
        edited_df.rename(columns=rename_map, inplace=True)
        
        # === Data Missing Alerts ===
        unknown_history = []
        
        def to_circled(n):
            try:
                n_int = int(n)
                if 1 <= n_int <= 20: 
                    return chr(9311 + n_int)
                return str(n)
            except:
                return str(n)

        if '前走着順' in edited_df.columns:
            # Format: "① Name"
            unknown_history = [f"{to_circled(row['馬番'])} {row['馬名']}" for _, row in edited_df[edited_df['前走着順'] == 0].iterrows()]
            
        unknown_jockey = []
        hidden_gems = []
        if '騎手適性度' in edited_df.columns:
            # 5.0 is the fallback score for missing data
            jockey_missing_mask = (edited_df['騎手適性度'] == 5.0)
            unknown_jockey = [f"{to_circled(row['馬番'])} {row['馬名']}" for _, row in edited_df[jockey_missing_mask].iterrows()]
            
            # Check if Horse has high potential despite unknown jockey
            # High potential = Course OR Distance > 7.0
            if 'コース適性度' in edited_df.columns and '距離適性度' in edited_df.columns:
                 potential_mask = (edited_df['コース適性度'] >= 7.0) | (edited_df['距離適性度'] >= 7.0)
                 hidden_gems = [f"{to_circled(row['馬番'])} {row['馬名']}" for _, row in edited_df[jockey_missing_mask & potential_mask].iterrows()]

        if unknown_history or unknown_jockey:
             st.warning("⚠️ 一部の馬にデータ不足があります")
             cols_alert = st.columns(2)
             with cols_alert[0]:
                 if unknown_history:
                     st.info(f"**初出走・履歴なし**: {', '.join(unknown_history)}")
             with cols_alert[1]:
                 if unknown_jockey:
                     st.info(f"**騎手データ不足**: {', '.join(unknown_jockey)}")
                 if hidden_gems:
                     st.success(f"✨ **騎手は未知数ですが、馬の適性は高い**: {', '.join(hidden_gems)}")
        
        st.subheader("📝 予想・オッズ入力")
        
        col_input_1, col_input_2 = st.columns([3, 1])
        with col_input_1:
             st.info("「予想印」や「現在オッズ」を編集すると、リアルタイムで期待値(EV)が計算されます。")
        with col_input_2:
             fetch_trigger = False
             if st.button("🔄 最新オッズ (リアルタイム)"):
                 fetch_trigger = True

             if fetch_trigger:
                  with st.spinner("オッズを取得中..."):
                      try:
                          current_odds = auto_scraper.scrape_odds_for_race(race_id, mode=mode_val)
                          # Update session state df
                          if current_odds:
                              odds_map = {x['number']: x['odds'] for x in current_odds}
                              
                              target_df = st.session_state[f'data_{race_id}']
                              
                              # Update '単勝' and 'Odds'
                              def update_odds(row):
                                  try:
                                      num = int(row['馬 番'])
                                      new_odds = odds_map.get(num)
                                      d = {
                                          'Odds': new_odds if new_odds is not None else row.get('Odds', 0.0)
                                      }
                                      return d
                                  except:
                                      return {'Odds': row.get('Odds', 0.0)}
                                  
                              # Apply updates
                              updated_data = target_df.apply(update_odds, axis=1, result_type='expand')
                              target_df['Odds'] = updated_data['Odds']
                              target_df['単勝'] = updated_data['Odds']
                              
                              st.session_state[f'data_{race_id}'] = target_df
                              st.success("オッズ（単勝）を更新しました！")
                              st.rerun()
                          else:
                              st.warning("オッズの取得に失敗したか、データが見つかりませんでした。")
                      except Exception as e:
                          st.error(f"オッズ取得エラー: {e}")

        # Ensure Pedigree exists (Safety)
        if '血統' not in edited_df.columns:
            edited_df['血統'] = "-"
        
        edited_df = st.data_editor(
            edited_df,
            column_config={
                "AIスコア(%)": st.column_config.ProgressColumn(
                    "AI勝率(%)",
                    help="1着になる AI予測確率",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "D指数": st.column_config.ProgressColumn(
                    "D指数",
                    help="適性と信頼度で傾斜をかけた最終スコア",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                ),
                "信頼度": st.column_config.ProgressColumn(
                    "予測信頼度",
                    help="この予測の信頼性スコア",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "現在オッズ": st.column_config.NumberColumn(
                    "単勝オッズ",
                    help="単勝オッズ（参考）",
                    step=0.1,
                    format="%.1f"
                ),
                "血統": st.column_config.TextColumn(
                    "血統",
                    help="父 / 母 (母父)",
                    width="medium"
                ),
                "Bloodline_Index": st.column_config.ProgressColumn(
                    "血統スコア",
                    help="血統統計に基づくスコア (0-100)",
                    format="%.1f",
                    min_value=0,
                    max_value=100
                ),
                "平均スピード": st.column_config.NumberColumn(
                    "平均スピード",
                    help="過去走の平均スピード (m/s)",
                    format="%.1f m/s"
                ),
                "単勝期待値": st.column_config.NumberColumn(
                    "単勝期待値",
                    help="純粋な単勝期待値 = (AI勝率 × 単勝オッズ) - 1.0",
                    format="%.2f"
                ),
                "調整後期待値": st.column_config.NumberColumn(
                    "調整後期待値",
                    help="印・適性を加味した最終的な単勝期待値",
                    format="%.2f"
                ),
                "推奨度(Kelly)": st.column_config.ProgressColumn(
                    "推奨度(Kelly)",
                    help="ケリー基準による推奨賭け率",
                    format="%.1f%%",
                    min_value=0,
                    max_value=30, 
                ),
                "予想印": st.column_config.SelectboxColumn(
                    "予想印",
                    options=["", "◎", "◯", "▲", "△", "✕"],
                    required=False,
                    help="予想印を入力すると、調整後期待値に反映されます"
                ),
                "騎手適性度": st.column_config.ProgressColumn(
                    "騎手適性度",
                    help="この騎手との相性",
                    format="%.1f",
                    min_value=0,
                    max_value=10
                ),
                "コース適性度": st.column_config.ProgressColumn(
                    "コース適性度",
                    help="芝/ダート別 相性",
                    format="%.1f",
                    min_value=0,
                    max_value=10
                ),
                "距離適性度": st.column_config.ProgressColumn(
                    "距離適性度",
                    help="この距離での相性",
                    format="%.1f",
                    min_value=0,
                    max_value=10
                )
            },
            hide_index=True,
            num_rows="fixed"  
        )
        
        # Calculate EV with JRA/NAR distinction
        # Determine race type from user's mode selection (as primary source)
        race_type = mode_val  # Use user's selected mode (JRA or NAR) as primary source of truth
        venue = ''  # Initialize venue

        # Get venue information if available
        if '会場' in df_display.columns and len(df_display) > 0:
            venue = df_display['会場'].iloc[0]

            # If venue is available, use it to verify/override race_type for accuracy
            if venue:
                try:
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml'))
                    from race_classifier import classify_race_type
                    venue_based_type = classify_race_type(venue)
                    # Use venue-based classification (more accurate than mode selection)
                    race_type = venue_based_type
                except:
                    # Fallback: manual classification
                    jra_venues = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']
                    race_type = 'JRA' if venue in jra_venues else 'NAR'

        # EV calculation with race type AND venue specific parameters
        # Import venue characteristics
        venue_char = None
        try:
            from ml.venue_characteristics import get_venue_characteristics, get_distance_category
            if venue:
                venue_char = get_venue_characteristics(venue)
        except Exception as e:
            # Silently fail if venue characteristics not available
            pass

        # === Betting Recommendations for Individual Analysis ===
        st.markdown("---")
        st.markdown("### 🎯 おすすめの買い方 (Beta)")
        
        # Calculate Metrics manually from edited_df
        # We need: Gap (D-Index), Gap 1-2 (Odds), Std 1-3 (Odds), Std 1-6 (Odds), Top D-Index
        
        try:
            # 1. Sort by D-Index for Gap (D-Index) & Top D-Index
            # Note: edited_df might not be sorted by D-Index if user sorted differently in UI, but we need calculation based on values
            df_calc = edited_df.copy()
            
            # Ensure numeric with correct column names from Japanese UI
            df_calc['D_Index'] = pd.to_numeric(df_calc['D指数'], errors='coerce').fillna(0)
            df_calc['Odds'] = pd.to_numeric(df_calc['現在オッズ'], errors='coerce').fillna(0)
            
            # D-Index Metrics
            df_d_sorted = df_calc.sort_values('D_Index', ascending=False).reset_index(drop=True)
            top_d_index = df_d_sorted.iloc[0]['D_Index'] if len(df_d_sorted) > 0 else 0
            gap_d_index = (df_d_sorted.iloc[0]['D_Index'] - df_d_sorted.iloc[1]['D_Index']) if len(df_d_sorted) >= 2 else 0
            gap_d_2_3 = (df_d_sorted.iloc[1]['D_Index'] - df_d_sorted.iloc[2]['D_Index']) if len(df_d_sorted) >= 3 else 0
            gap_d_3_4 = (df_d_sorted.iloc[2]['D_Index'] - df_d_sorted.iloc[3]['D_Index']) if len(df_d_sorted) >= 4 else 0
            
            # Odds Metrics
            # Filter valid odds > 0
            valid_odds = df_calc[df_calc['Odds'] > 0]['Odds'].sort_values().tolist()
            
            gap_odds_1_2 = (valid_odds[1] - valid_odds[0]) if len(valid_odds) >= 2 else 0
            std_odds_1_3 = np.std(valid_odds[:3], ddof=1) if len(valid_odds) >= 3 else 0
            std_odds_1_6 = np.std(valid_odds[:6], ddof=1) if len(valid_odds) >= 6 else 0
            
            # Display Metrics for transparency (Optional, but helpful)
            # st.caption(f"Metrics: Top D={top_d_index:.1f}, Gap D={gap_d_index:.1f}, Gap Odds={gap_odds_1_2:.1f}, Std(1-3)={std_odds_1_3:.2f}, Std(1-6)={std_odds_1_6:.2f}")

            # Define columns to show in recommendation tables
            cols_show = [c for c in ['枠', '馬番', '馬名', '予想印', 'D指数', '現在オッズ', '信頼度', '調整後期待値'] if c in df_d_sorted.columns]

            # Recommender Logic
            rec_found = False
            
            # 1. Sure Win
            if top_d_index >= 80.0:
                 st.success("💎 **【確勝級】圧倒的指数差**")
                 st.write("D指数が2位以下を大きく引き離している場合、単勝で確実に資金を回収しつつ、三連複でボーナスを狙う戦略です。")
                 st.write(f"推奨: **単勝一点 ＋ 三連複軸1頭流し** (本命: {df_d_sorted.iloc[0]['馬名']})")
                 st.dataframe(df_d_sorted.head(1)[cols_show], hide_index=True)
                 rec_found = True
                 
            # 2. Top Priority
            # Logic Update: Also prioritize New Horse/Maiden races for BOX
            is_new_maiden = False
            if 'レース名' in df_display.columns:
                 r_name = str(df_display['レース名'].iloc[0])
                 if '新馬' in r_name or '未勝利' in r_name:
                     is_new_maiden = True
            
            if (gap_d_index > 5.0 and std_odds_1_3 < 1.5) or (is_new_maiden):
                 title_suffix = " (新馬・未勝利はBOX推奨)" if is_new_maiden else ""
                 st.success(f"🔥 **【最優先】的中率・利益の柱{title_suffix}**")
                 st.write("D指数上位4頭の決着を完全に捉えます。2日間で最も安定感があり、多重的中（トリプル的中）が発生しやすい最強の布陣です。")
                 st.write("推奨: **ワイド4頭BOX ＋ 三連複4頭BOX**")
                 st.dataframe(df_d_sorted.head(4)[cols_show], hide_index=True)
                 rec_found = True

            # 3. High Dividend
            if std_odds_1_6 < 4.0:
                 st.info("💰 **【高配当】穴馬を含めた爆発力**")
                 st.write("ワイドよりも三連複に絞ることで、一撃10万馬券クラスを逃さず利益効率を最大化します。")
                 st.write("推奨: **三連複 6頭BOX (20点)**")
                 st.dataframe(df_d_sorted.head(6)[cols_show], hide_index=True)
                 rec_found = True
                 
            # 4. Ironclad
            if gap_d_index > 10.0:
                 st.error("🏰 **【鉄板軸】軸馬の絶対的信頼**")
                 st.write("軸馬（◎）から相手5頭へ。軸馬が3着以内に入る確率が極めて高いため、相手に人気薄が飛び込んだ際の「ヒモ荒れ」を三連複で高配当に変えます。")
                 st.write(f"推奨: **ワイド流し ＋ 三連複軸1頭流し** (軸: {df_d_sorted.iloc[0]['馬名']})")
                 st.dataframe(df_d_sorted.head(1)[cols_show], hide_index=True)
                 rec_found = True

            # 4-2. High Value Win -> Hole Shot
            # Check odds of top horse
            top_odds = df_d_sorted.iloc[0].get('Odds', 0.0)
            if gap_d_index > 10.0 and top_odds >= 3.0:
                 st.success("🌟 **【穴勝負】低投資・高配当**")
                 st.write("指数1位の穴馬が2・3着に食い込むケースが多いため、複勝を厚めに買うことで「的中したのに外れた」という事態を防ぎ、確実にプラスを拾います。")
                 st.write(f"推奨: **単勝 ＋ 複勝 (比率1:2)** (本命: {df_d_sorted.iloc[0]['馬名']})")
                 st.dataframe(df_d_sorted.head(1)[cols_show], hide_index=True)
                 rec_found = True

            # 6. Duel (2 Strong)
            if gap_d_2_3 > 10.0:
                 st.info("⚔️ **【一騎打ちムード】** (2位と3位のD指数差 > 10.0)")
                 st.write(f"推奨: **馬連・ワイド 1-2 一点勝負** ({df_d_sorted.iloc[0]['馬名']} - {df_d_sorted.iloc[1]['馬名']})")
                 st.dataframe(df_d_sorted.head(2)[cols_show], hide_index=True)
                 rec_found = True

            # 7. Top 3 (3 Strong)
            if gap_d_3_4 > 10.0:
                 st.info("🔺 **【3強対決】** (3位と4位のD指数差 > 10.0)")
                 st.write(f"推奨: **3連複 3頭BOX (1点買い)** ({df_d_sorted.iloc[0]['馬名']} - {df_d_sorted.iloc[1]['馬名']} - {df_d_sorted.iloc[2]['馬名']})")
                 st.dataframe(df_d_sorted.head(3)[cols_show], hide_index=True)
                 rec_found = True

            # 5. Chaos (Last check)
            if gap_d_index < 3.0 and top_d_index < 70.0 and not rec_found:
                 st.warning("🌀 **【波乱含み・BOX推奨】** (2位差 < 3.0 かつ TOP D指数 < 70.0)")
                 st.write("推奨: **馬連・3連複のBOX（上位4〜5頭）** で高配当狙い")
                 st.dataframe(df_d_sorted.head(5)[cols_show], hide_index=True)
                 rec_found = True

            if not rec_found:
                 st.write("💡 特におすすめのパターンには該当しませんでした。基本の期待値買いを推奨します。")

        except Exception as e:
            st.error(f"推奨判定エラー: {e}")

        st.markdown("---")

        # === UI: ランキング基準の選択 ===
        st.markdown("#### 📊 ランキング基準")
        ranking_criteria = st.radio(
            "評価方法を選択してください:", 
            ["的中率重視 (AIスコア)", "回収率重視 (期待値)"], 
            horizontal=True,
            help="「的中率」はオッズを無視して純粋に勝つ確率が高い馬を探します。「回収率」はオッズを考慮して儲かる馬を探します。"
        )


        # Base parameters by race type
        if race_type == 'JRA':
            # === 中央競馬（JRA）設定 ===
            # 特徴: 実力が拮抗しており、混戦になりやすい。オッズも割れがち。
            # 対策: 突出した補正は避け、フラットに近い評価を行う。
            mark_weights = {
                "◎": 1.15,  # 本命: 信頼しすぎない (1.15倍)
                "◯": 1.10,  # 対抗: 1.10倍
                "▲": 1.05,  # 単穴: 1.05倍
                "△": 1.02,  # 連下: 1.02倍
                "✕": 0.0,   # 消し: 0倍
                "": 1.0     # 印なし: 1.0倍
            }
            safety_threshold = 0.04  # 1着確率4%未満は除外
            venue_info = f"🏇 中央競馬（JRA）" + (f" - {venue}" if venue else "")
        else:
            # === 地方競馬（NAR）設定 ===
            # 特徴: 能力差が大きく、強い馬が順当に勝つことが多い（堅い決着）。
            # 対策: AIが選んだ本命馬は信頼できるため、評価を少し高める。
            mark_weights = {
                "◎": 1.30,  # 本命: 比較的信頼できる (1.3倍)
                "◯": 1.15,  # 対抗: 1.15倍
                "▲": 1.10,  # 単穴: 1.10倍
                "△": 1.05,  # 連下: 1.05倍
                "✕": 0.0,   # 消し: 0倍
                "": 1.0     # 印なし: 1.0倍
            }
            safety_threshold = 0.03  # 1着確率3%未満は除外
            venue_info = f"🌙 地方競馬（NAR）" + (f" - {venue}" if venue else "")

        # Venue-specific adjustments
        venue_features = []
        if venue_char:
            # 直線距離による調整
            straight = venue_char.get('turf_straight', 300)
            if straight and straight > 500:  # 長い直線（新潟など）
                mark_weights["◎"] *= 0.95  # 人気馬やや不利
                mark_weights["△"] *= 1.05  # 穴馬やや有利
                venue_features.append("長直線")
            # 中山(310m)も含めるため、閾値を330mに緩和
            elif straight and straight < 330:  # 短い直線（中山、函館、福島、小倉など）
                mark_weights["◎"] *= 1.05  # 先行残りやすく、人気馬有利
                mark_weights["△"] *= 0.95  # 穴馬不利（差し届かず）
                venue_features.append("短直線")

            # コース幅による調整
            track_width = venue_char.get('track_width')
            if track_width == 'narrow':  # 狭いコース
                mark_weights["◎"] *= 1.03  # 先行有利、人気馬やや有利
                venue_features.append("小回り")
            elif track_width == 'wide':  # 広いコース
                # 馬群が広がりやすく、展開次第
                pass

            # 勾配による調整
            slope = venue_char.get('slope')
            if slope == 'steep':  # 急坂あり（中山、阪神、中京など）
                mark_weights["◎"] *= 1.02  # パワーある人気馬有利
                mark_weights["△"] *= 0.98  # パワー不足の穴馬は割引
                venue_features.append("坂あり(パワー要)")

        if venue_features:
            venue_info += f" ({', '.join(venue_features)})"

        st.info(venue_info)

        # === 確率較正のチェック ===
        is_calibrated = False
        if model_meta and 'training_config' in model_meta:
             is_calibrated = model_meta['training_config'].get('calibrated', False)

        # Uncalibrated NAR Correction (Global application for consistency)
        if race_type == 'NAR' and not is_calibrated:
             # 地方競馬かつ未較正の場合のみ、保守的な調整を行う
             # これにより、表示されるAIスコアとEV計算に使われる確率が一致する
             def adjust_nar_prob_row(row):
                 p = row['AIスコア(%)'] / 100.0
                 new_p = p * 0.9 + 0.05
                 return int(new_p * 100)
             
             edited_df['AIスコア(%)'] = edited_df.apply(adjust_nar_prob_row, axis=1)
             st.caption("ℹ️ NAR調整: AIスコアと期待値を保守的に補正しました（未較正モデルのため）")

        probs = edited_df['AIスコア(%)'] / 100.0
        odds = edited_df['現在オッズ']
        place_min_odds = edited_df.get('複勝下限', pd.Series([0.0] * len(edited_df), index=edited_df.index)) 
        marks = edited_df['予想印']
        confidences = edited_df['信頼度']

        # Get run style compatibility if available
        run_style_compatibility = None
        if 'venue_run_style_compatibility' in edited_df.columns:
            run_style_compatibility = edited_df['venue_run_style_compatibility']

        # Get frame (枠) for venue-specific frame advantage
        frames = None
        if '枠' in edited_df.columns:
            frames = edited_df['枠']

        evs_pure = []      # 純粋EV（印補正なし）
        evs_adjusted = []  # 調整後EV（印補正あり）
        kellys = []
        bias_reasons_list = [] # 補正理由リスト

        for idx, (p, o_win, o_place, m, c) in enumerate(zip(probs, odds, place_min_odds, marks, confidences)):
            reasons = [] # この馬の補正理由
            
            # Use Win Odds for EV Calculation (since we are predicting target_win)
            calc_odds = 0.0
            if o_win > 1.0:
                 calc_odds = o_win
            elif o_place > 1.0:
                 # Fallback if Win Odds missing but Place Odds exist (rare)
                 calc_odds = o_place * 3.0
                 reasons.append("単勝推定")
            
            # Safety filter (race type specific)
            if p < safety_threshold:
                ev_pure = -1.0
                ev_adj = -1.0
                kelly = 0.0
                reasons.append("確率不足(除外)")
            else:
                w = mark_weights.get(m, 1.0)
                if w != 1.0:
                     reasons.append(f"印{m} (x{w:.2f})")
                
                # Already adjusted in Dataframe if needed
                adjusted_p = p

                # Apply run style compatibility if available
                if run_style_compatibility is not None:
                    run_compat = run_style_compatibility.iloc[idx]
                    if not pd.isna(run_compat) and run_compat != 1.0:
                        # 脚質相性が良い馬は期待値を上げる
                        adjusted_p *= run_compat
                        reasons.append(f"脚質適性 (x{run_compat:.2f})")

                # Apply frame advantage if available
                if frames is not None and venue_char:
                    frame = frames.iloc[idx]
                    if not pd.isna(frame):
                        outer_advantage = venue_char.get('outer_track_advantage', 1.0)
                        try:
                            frame_num = int(frame)
                            if frame_num >= 6 and outer_advantage > 1.0:  # 外枠有利
                                adjusted_p *= outer_advantage
                                reasons.append(f"外枠有利 (x{outer_advantage:.2f})")
                            elif frame_num <= 3 and outer_advantage > 1.0:  # 内枠不利
                                penalty = 2.0 - outer_advantage
                                adjusted_p *= penalty
                                reasons.append(f"内枠不利 (x{penalty:.2f})")
                            
                            # 内枠有利な場合(outer_advantage < 1.0)
                            elif frame_num <= 3 and outer_advantage < 1.0:
                                bonus = 2.0 - outer_advantage
                                adjusted_p *= bonus
                                reasons.append(f"内枠有利 (x{bonus:.2f})")
                            elif frame_num >= 6 and outer_advantage < 1.0:
                                adjusted_p *= outer_advantage
                                reasons.append(f"外枠不利 (x{outer_advantage:.2f})")
                                
                        except: pass

                # 純粋EV: 印補正なし（統計的に正しい）
                # Uses Place Odds
                ev_pure = (adjusted_p * calc_odds) - 1.0

                # 調整後EV: 印・信頼度補正あり（ユーザーの主観＋リスク換算）
                # 信頼度(c)を乗算することで、「AIが自信のない穴馬」のEV過大評価を防ぐ
                trust_factor = c / 100.0
                ev_adj = (adjusted_p * w * calc_odds * trust_factor) - 1.0
                
                if trust_factor < 0.6:
                     reasons.append(f"信頼度低 (x{trust_factor:.2f})")

                # Kelly criterion: 最適賭け金比率の計算
                # Formula: f* = (p * odds - 1) / (odds - 1)
                # ここでpは調整後の確率、oddsはオッズ
                if calc_odds > 1.0:
                    kelly_raw = (adjusted_p * w * calc_odds - 1.0) / (calc_odds - 1.0)
                    # 負の値は0に、上限は10%に制限（リスク管理）
                    kelly = max(0.0, min(0.10, kelly_raw)) * 100  # パーセント表示
                else:
                    kelly = 0.0
            
            evs_pure.append(ev_pure)
            evs_adjusted.append(ev_adj)
            kellys.append(kelly)
            bias_reasons_list.append(", ".join(reasons) if reasons else "-")

        edited_df['単勝期待値'] = evs_pure
        edited_df['調整後期待値'] = evs_adjusted
        edited_df['推奨度(Kelly)'] = kellys
        edited_df['補正内容'] = bias_reasons_list

        # === AI期待度TOP5のグラフ（デフォルト表示） ===
        st.markdown("---")
        st.subheader("📊 AI評価 TOP5 分析")

        # TOP5をAIスコア（勝率）でソート（的中率重視）

        

        # Apply sorting based on ranking criteria
        if ranking_criteria == "回収率重視 (期待値)":
            edited_df.sort_values(by='調整後期待値', ascending=False, inplace=True)
            y_col = '調整後期待値'
            y_label = '期待値(EV)'
            bar_color = '#28a745'
        else: # "的中率重視 (AIスコア)"
            edited_df.sort_values(by='D指数', ascending=False, inplace=True)
            y_col = 'D指数'
            y_label = 'D指数'
            bar_color = '#1f77b4'

        top5_df = edited_df.head(5)
        
        # Plot Top 5
        st.subheader(f"📈 {ranking_criteria} TOP 5")
        
        fig_top5 = go.Figure(go.Bar(
            x=top5_df['馬名'],
            y=top5_df[y_col],
            text=top5_df[y_col].apply(lambda x: f"{x:.2f}" if y_col == '調整後期待値' else f"{x:.1f}"),
            textposition='auto',
            marker_color=bar_color
        ))
        fig_top5.update_layout(
            yaxis_title=y_label,
            xaxis_title="馬名",
            height=400,
            showlegend=False
        )

        st.plotly_chart(fig_top5, width="stretch")

        # 補正内容の表示
        st.markdown("##### ℹ️ 期待値調整の詳細 (TOP5)")
        st.dataframe(
            top5_df[['予想印', '馬名', '現在オッズ', '調整後期待値', '補正内容']],
            column_config={
                "調整後期待値": st.column_config.NumberColumn(format="%.2f"),
                "推奨度(Kelly)": st.column_config.ProgressColumn(format="%.1f%%", max_value=30),
            },
            hide_index=True,
            width='stretch'
        )

        # 2. 適性スコア比較（ヒートマップ）
        st.markdown("#### 🎯 TOP5 適性度比較")

        compatibility_cols = ['騎手適性度', 'コース適性度', '距離適性度']
        compat_data = []
        for idx, row in top5_df.iterrows():
            compat_data.append({
                '馬名': row['馬名'],
                '騎手適性度': row.get('騎手適性度', 5.0),
                'コース適性度': row.get('コース適性度', 5.0),
                '距離適性度': row.get('距離適性度', 5.0)
            })

        compat_df = pd.DataFrame(compat_data)

        # ヒートマップ用データ（既に10点満点に変換済み）
        heatmap_data = []
        for col in compatibility_cols:
            heatmap_data.append([val for val in compat_df[col]])

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=compat_df['馬名'],
            y=compatibility_cols,
            colorscale='RdYlGn',
            text=[[f'{val:.1f}' for val in compat_df[col]] for col in compatibility_cols],
            texttemplate='%{text}',
            textfont={"size": 12},
            colorbar=dict(title="適性度<br>(10点満点)")
        ))

        fig_heatmap.update_layout(
            title="適性度（10点満点、高いほど良い）",
            xaxis_title="馬名",
            height=300
        )

        st.plotly_chart(fig_heatmap, width="stretch")

        # 3. 予測結果の解釈ガイド
        with st.expander("ℹ️ AI分析指標の完全ガイド・計算ロジック", expanded=False):
            st.markdown("""
            ### 🧠 AI指標の読み方・計算ロジック
            
            **1. 📈 AIスコア (AI勝率予測)**
            *   **意味**: 過去の膨大な学習データに基づき、AIが算出した「純粋な勝利確率」です。
            *   **特徴**: オッズや人気（過剰評価）に左右されず、馬の本来の実力と適性だけで評価しています。
            *   **信頼性**: 未来の情報（レース結果）を含まない厳密な学習を行っているため、極めて客観的です。

            **2. 🛡️ 信頼度 (Confidence)**
            *   **意味**: 「この予測に乗っかっても大丈夫か」という安心感を示す独自スコア（0-100）です。
            *   **算出ロジック**: 
                *   AIの確信度（確率の強さ）
                *   データ量（過去のレース数）
                *   適性の一致度（得意な騎手・コースか）
                *   リスク要因（長期休養明けなどは減点）
            *   **活用法**: AIスコアが高くても信頼度が低い場合は、不確定要素（初出走など）が多いことを意味します。

            **3. 💰 調整後期待値 (Adjusted EV)**
            *   **意味**: 「投資対象としてのおいしさ」を示す最重要指標です。
            *   **計算式**: `(補正後AI確率 × 印の重み × オッズ) - 1.0`
            *   **補正内容について**:
                *   **コース特性**: 会場ごとの有利不利（外枠有利、逃げ有利など）を自動補正しています（グラフ下の表で確認可能）。
                *   **印の重み**: あなたの入力した予想印（◎=1.3倍など）も反映されます。
            *   **狙い目**: この数値がプラス（緑色）の馬は、統計的にも主観的にも「買う価値あり」と判断された馬です。

            **4. 適性度（騎手・コース・距離）**
            - **全期間（3年間）のGlobal History**データから計算
            - 平均着順を10点満点スコアに変換: `10 - (平均着順 / 2)`
            - **数値が高いほど良い** (10点=平均1着, 5点=平均10着)
            - **7.0点以上**: 優秀 (平均着順 6着以内)
            - **5.0点**: 標準 (データなし、または平均10着)
            - **3.0点以下**: 不安 (平均14着以下)

            **5. コース特性（傾斜・直線距離・コース幅・枠番）**
            - **勾配（傾斜）**: 急坂ありの競馬場では人気馬が有利（+2%）
              - 中山、阪神など: 坂でパワーが必要なため実績馬が優位
            - **直線距離**:
              - 長い直線（500m以上）: 差し馬有利、穴馬チャンス（人気馬-5%、穴馬+5%）
              - 短い直線（300m未満）: 逃げ・先行馬有利、人気馬堅い（人気馬+5%）
            - **コース幅**:
              - 小回りコース: コーナーが多く器用な馬が有利（人気馬+3%）
            - **枠番傾向**:
              - 外枠有利な競馬場: 6-8枠の確率を上方調整
              - 内枠有利な競馬場: 1-3枠の確率を上方調整

            ⚠️ **これらのコース特性は、レース概要セクションで確認できます**

            ### 🎯 推奨される使い方

            1. **TOP5グラフ**でAI評価の高い馬を確認
            2. **期待値(EV)がプラス**の馬に注目
            3. **信頼度が70%以上**の予測を優先
            4. **適性度**で相性を確認（特に騎手適性度は重要）
            5. **現在オッズ**と**予想印**を入力してEVを最終調整

            ### ⚠️ 重要な注意事項

            - **モデルの再学習が必要**: 現在のモデルは「3着以内」を予測している可能性があります
            - 管理ページで両モデル（JRA/NAR）を再学習してください
            - 再学習後、AI確率は5-15%の範囲（1着確率として妥当）になります
            """)

        st.markdown("---")
        st.markdown("---")
        st.subheader("📋 詳細データテーブル")

        # Rename for clarity if exists
        if 'AI期待値' in edited_df.columns:
            edited_df.rename(columns={'AI期待値': '単勝期待値'}, inplace=True)


        # Highlight high EV and Kelly
        def highlight_ev(s):
            is_high = s > 0
            return ['background-color: #d4edda' if v else '' for v in is_high]

        # Select and Order Columns for Hit Rate Focus
        display_cols = [
            '予想印', '枠', '馬 番', '馬名', 
            'AIスコア(%)', '信頼度', 
            'jockey_compatibility', 'time_stats', 
            '現在オッズ', '単勝期待値', '調整後期待値', '推奨度(Kelly)'
        ]
        # Filter existing columns
        display_cols = [c for c in display_cols if c in edited_df.columns]
        
        st.dataframe(
            edited_df[display_cols].style
            .format({
                '推奨度(Kelly)': lambda x: '-' if x <= 0 else f'{x:.1f}%',
                '単勝期待値': '{:.2f}',
                '調整後期待値': '{:.2f}',
                'AIスコア(%)': '{:.1f}',
                '信頼度': '{:.0f}'
            })
            .map(lambda x: 'background-color: #d4edda' if x > 0 else '', subset=['単勝期待値', '調整後期待値', '推奨度(Kelly)'])
        )



        # Visualization
        st.markdown("---")
        st.subheader("🔍 個別馬の詳細分析")

        # ヘルパー関数：馬の詳細分析を生成
        def create_horse_analysis(horse_name, df_display, edited_df):
            """個別馬の能力チャートと過去5走の推移を生成"""
            # Find row
            row = df_display[df_display['馬名'] == horse_name].iloc[0]

            # --- Scoring Logic (Lower rank is better, so Invert) ---
            # --- Scoring Logic (Lower rank is better, so Invert) ---
            def rank_to_score(r):
                if pd.isna(r) or r > 18: return 0
                # Use same logic as table: 10 - (Rank / 2)
                # Rank 1 -> 9.5
                # Rank 10 -> 5.0
                return max(0, min(10, 10 - (r / 2)))

            # Calculate scores
            sp_val = row.get('weighted_avg_speed', 16.0)
            score_speed = max(0, min(10, (sp_val - 15.0) * 5))
            j_val = row.get('jockey_compatibility', 10.0) # Raw Rank
            score_jockey = rank_to_score(j_val)
            c_val = row.get('course_compatibility', 10.0) # Raw Rank
            score_course = rank_to_score(c_val)
            d_val = row.get('distance_compatibility', 10.0) # Raw Rank
            score_dist = rank_to_score(d_val)
            rank_val = row.get('weighted_avg_rank', 10.0) # Raw Rank
            score_form = rank_to_score(rank_val)

            # Radar Chart
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=[score_speed, score_form, score_jockey, score_course, score_dist, score_speed],
                theta=['スピード', '実績(着順)', '騎手相性', 'コース適性', '距離適性'],
                fill='toself',
                name=horse_name,
                line=dict(color='#1f77b4')
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                height=300,
                margin=dict(l=40, r=40, t=40, b=40)
            )

            # Past 5 Runs Line Chart
            history_data = []
            for i in range(5, 0, -1):
                if f"past_{i}_rank" in row and pd.notna(row[f"past_{i}_rank"]):
                    history_data.append({
                        "Run": f"{i}走前",
                        "着順": row[f"past_{i}_rank"],
                        "3Fタイム": row[f"past_{i}_last_3f"]
                    })

            if history_data:
                hist_df = pd.DataFrame(history_data)
                from plotly.subplots import make_subplots
                fig_line = make_subplots(specs=[[{"secondary_y": True}]])
                fig_line.add_trace(go.Scatter(x=hist_df['Run'], y=hist_df['着順'], name="着順", mode='lines+markers', line=dict(color='#ff7f0e')), secondary_y=False)
                fig_line.add_trace(go.Scatter(x=hist_df['Run'], y=hist_df['3Fタイム'], name="上り3F", mode='lines+markers', line=dict(dash='dot', color='#2ca02c')), secondary_y=True)
                fig_line.update_layout(height=300, margin=dict(l=40, r=40, t=40, b=40))
                fig_line.update_yaxes(title_text="着順", autorange="reversed", secondary_y=False)
                fig_line.update_yaxes(title_text="上り3F (秒)", secondary_y=True)
            else:
                fig_line = go.Figure()
                fig_line.add_annotation(text="過去データなし")
                fig_line.update_layout(height=300)

            # Get prediction summary
            pred_row = edited_df[edited_df['馬名'] == horse_name].iloc[0]

            return fig_radar, fig_line, pred_row

        try:
            # === 分析対象の馬を選択 ===
            st.info("💡 分析対象の馬を選択してください（デフォルトは評価上位5頭）")

            # Get all horses sorted by AI Score
            all_horses = edited_df.sort_values('D指数', ascending=False)['馬名'].tolist()
            default_horses = top5_df['馬名'].tolist()
            
            # Ensure default horses are in the options (sanity check)
            default_horses = [h for h in default_horses if h in all_horses]

            selected_horses = st.multiselect(
                "分析対象の馬を選択",
                options=all_horses,
                default=default_horses
            )

            for idx, horse_name in enumerate(selected_horses):
                with st.expander(f"**{idx+1}位: {horse_name}**", expanded=(idx < 2)):  # 1-2位は展開表示
                    fig_radar, fig_line, pred_row = create_horse_analysis(horse_name, df_display, edited_df)

                    # Prediction Summary
                    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
                    with col_s1:
                         # Use D-Index
                        st.metric("D指数", f"{pred_row['D指数']:.1f}", help="適性と信頼度で傾斜をかけたスコア")
                    with col_s2:
                        st.metric("信頼度", f"{pred_row['信頼度']}%")
                    with col_s3:
                        ai_ev_val = pred_row.get('単勝期待値', 0.0)
                        st.metric("単勝期待値", f"{ai_ev_val:.2f}")
                    with col_s4:
                        adj_ev_val = pred_row['調整後期待値']
                        ev_delta = "買い推奨" if adj_ev_val > 0 else "見送り"
                        st.metric("調整後EV", f"{adj_ev_val:.2f}", delta=ev_delta)
                    with col_s5:
                        odds_val = pred_row.get('現在オッズ', 0.0)
                        st.metric("オッズ", f"{odds_val:.1f}倍")

                    # Charts
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.markdown("**能力チャート**")
                        st.plotly_chart(fig_radar, width="stretch", key=f"radar_{idx}_{horse_name}")
                    with col_c2:
                        st.markdown("**過去5走の推移**")
                        st.plotly_chart(fig_line, width="stretch", key=f"line_{idx}_{horse_name}")

            # === カード表示: ヒートマップ風分析 ===
            st.markdown("---")
            st.subheader("📊 能力バランス分析")
            
            # Helper for circled numbers
            def to_circled_num(n):
                try:
                    val = int(float(n)) 
                    if 1 <= val <= 20: return chr(9311 + val)
                    return f"({val})"
                except: return ""

            # Helper to format horse name
            def fmt_horse(row):
                num = row.get('馬 番')
                if pd.isna(num): num = row.get('馬番', '')
                name = row['馬名']
                c_num = to_circled_num(num)
                if c_num: return f"{c_num} {name}".strip()
                elif pd.notna(num) and str(num).strip(): return f"({num}) {name}".strip()
                else: return name

            # 3 Columns for 3 Types of Analysis
            col_a1, col_a2, col_a3 = st.columns(3)
            
            with col_a1:
                 st.markdown("#### 🚀 スピード重視")
                 st.caption("平均スピード上位")
                 speed_top = edited_df.sort_values('平均スピード', ascending=False).head(3)
                 for _, row in speed_top.iterrows():
                     st.write(f"{fmt_horse(row)}: {row['平均スピード']:.1f}")

            with col_a2:
                 st.markdown("#### 💪 安定感重視")
                 st.caption("平均着順上位")
                 stab_top = edited_df.sort_values('平均着順', ascending=True).head(3)
                 for _, row in stab_top.iterrows():
                     st.write(f"{fmt_horse(row)}: {row['平均着順']:.1f}")

            with col_a3:
                 st.markdown("#### 🧬 血統・適性重視")
                 st.caption("Bloodline_Index上位")
                 blood_top = edited_df.sort_values('Bloodline_Index', ascending=False).head(3)
                 for _, row in blood_top.iterrows():
                     st.write(f"{fmt_horse(row)}: {row['Bloodline_Index']:.1f}")
                    
        except Exception as e:
            st.warning(f"可視化エラー: {e}")
            import traceback
            st.text(traceback.format_exc())




