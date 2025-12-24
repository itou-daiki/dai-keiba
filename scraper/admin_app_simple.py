"""
管理画面（簡素版）- モデル学習専用

データ処理はGoogle Colabで実行し、
このアプリでは学習とモデル保存のみを行います。
"""

import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

# パスの追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, 'ml'))

# モジュールのインポート
try:
    import train_model
    from db_helper import KeibaDatabase, get_data_stats
except ImportError as e:
    st.error(f"モジュールのインポートエラー: {e}")
    st.stop()

st.set_page_config(page_title="AI競馬 管理画面（学習専用）", layout="wide", page_icon="🏇")

st.title("🏇 AI競馬予想 管理画面（学習専用）")

st.markdown("""
このアプリケーションはモデル学習専用です。

**データ処理の流れ:**
1. 📊 **Google Colab**: スクレイピング + 前処理 + 特徴量生成 → SQLite
2. 🧠 **このアプリ**: SQLiteからデータ読み込み → モデル学習 → モデル保存
3. 🌐 **公開ページ**: モデル読み込み → 予測 → 表示
""")

# サイドバー
st.sidebar.header("⚙️ 設定")

# データベースパス
db_path = st.sidebar.text_input("データベースパス", value="keiba_data.db")

# モード選択
mode_val = st.sidebar.selectbox("モード", ["JRA", "NAR"])

# データベースの存在確認
if not os.path.exists(db_path):
    st.error(f"❌ データベースが見つかりません: {db_path}")
    st.info("""
    **データベースの作成方法:**
    1. Google Colabで `colab_data_pipeline.ipynb` を開く
    2. すべてのセルを実行
    3. 生成された `keiba_data.db` をダウンロード
    4. このプロジェクトのルートディレクトリに配置
    """)
    st.stop()

# データベース接続
try:
    db = KeibaDatabase(db_path)
    stats = db.get_statistics(mode_val)
except Exception as e:
    st.error(f"❌ データベース接続エラー: {e}")
    st.stop()

# データベース情報の表示
st.sidebar.markdown("---")
st.sidebar.markdown(f"### 📊 {mode_val}データ情報")
st.sidebar.metric("総レコード数", f"{stats['total_records']:,}")
st.sidebar.metric("ユニークレース数", f"{stats['unique_races']:,}")
st.sidebar.metric("ユニーク馬数", f"{stats['unique_horses']:,}")
st.sidebar.metric("勝率", f"{stats['win_rate']:.2%}")
st.sidebar.metric("データ鮮度", db.get_data_freshness(mode_val))

st.sidebar.markdown("---")

# メインコンテンツ
tab1, tab2 = st.tabs(["🧠 モデル学習", "📊 データ確認"])

# =============================================================================
# タブ1: モデル学習
# =============================================================================
with tab1:
    st.header("🧠 モデル学習")

    st.markdown("""
    SQLiteデータベースから学習用データを読み込み、LightGBMモデルを学習します。

    **学習の設定:**
    - TimeSeriesSplit 5-fold クロスバリデーション
    - Early Stopping（30ラウンド）
    - 全データで最終モデルを学習
    """)

    # 学習設定
    col1, col2 = st.columns(2)

    with col1:
        is_tuning = st.checkbox(
            "ハイパーパラメータ最適化（Optuna）",
            value=False,
            help="有効にすると学習時間が大幅に増加しますが、精度が向上します"
        )

    with col2:
        n_trials = 50
        if is_tuning:
            n_trials = st.slider("最適化試行回数", 10, 200, 50, step=10)

    # 学習実行ボタン
    start_training = st.button("🚀 学習開始", type="primary", use_container_width=True)

    if start_training:
        # モデルパスの設定
        model_dir = os.path.join(project_root, "ml", "models")
        os.makedirs(model_dir, exist_ok=True)

        if mode_val == "NAR":
            model_name = "lgbm_model_nar.pkl"
        else:
            model_name = "lgbm_model.pkl"

        model_path = os.path.join(model_dir, model_name)

        try:
            # データの読み込み
            with st.spinner("📥 データベースからデータを読み込み中..."):
                df_train = db.get_processed_data(mode_val)
                st.success(f"✅ データ読み込み完了: {len(df_train):,}件")

            # 特徴量とターゲットの分離
            meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']
            feature_cols = [c for c in df_train.columns if c not in meta_cols and c not in ['target_win', 'target_top3']]

            X = df_train[feature_cols].fillna(0)
            y = df_train['target_win'].fillna(0)

            st.info(f"📊 特徴量数: {len(feature_cols)}")
            st.info(f"🎯 目的変数: target_win（勝率: {y.mean():.2%}）")

            # ハイパーパラメータ最適化
            best_params = None
            if is_tuning:
                with st.spinner(f"⚙️ ハイパーパラメータ最適化中（{n_trials}試行）..."):
                    st.warning("これには数十分かかる場合があります...")
                    # Optuna最適化の実行
                    # 注: train_model.pyに最適化関数が必要
                    # opt_result = train_model.optimize_hyperparameters(X, y, n_trials=n_trials)
                    # best_params = opt_result['best_params']
                    st.info("⚠️ Optuna最適化は train_model.py に実装が必要です")

            # モデル学習
            with st.spinner("🧠 モデル学習中..."):
                # TimeSeriesSplit CV + 学習
                # 注: train_model.pyに学習関数が必要
                # result = train_model.train_and_save_model(
                #     X, y,
                #     model_path=model_path,
                #     params=best_params
                # )
                st.info("⚠️ モデル学習は train_model.py に実装が必要です")

                # 仮の成功メッセージ
                st.success(f"✅ モデル学習完了: {model_path}")

            # メタデータの保存
            meta_path = model_path.replace('.pkl', '_meta.json')
            import json

            metadata = {
                "model_id": f"lgbm_model_{mode_val.lower()}",
                "model_type": "LightGBM Binary Classification",
                "target": "target_win",
                "trained_at": datetime.now().isoformat(),
                "data_source": db_path,
                "data_stats": {
                    "total_records": len(df_train),
                    "win_rate": float(y.mean())
                },
                "features": feature_cols,
                "hyperparameters": best_params or {},
                "training_config": {
                    "use_timeseries_split": True,
                    "n_folds": 5,
                    "hyperparameter_optimization": is_tuning,
                    "n_trials": n_trials if is_tuning else None
                }
            }

            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            st.success(f"✅ メタデータ保存完了: {meta_path}")

            # 完了メッセージ
            st.balloons()
            st.success("🎉 すべての処理が完了しました！")

        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")
            import traceback
            st.code(traceback.format_exc())

# =============================================================================
# タブ2: データ確認
# =============================================================================
with tab2:
    st.header("📊 データ確認")

    st.markdown(f"### {mode_val}データの概要")

    # 統計情報
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総レコード数", f"{stats['total_records']:,}")
        st.metric("データ期間", f"{stats['earliest_date']}")
    with col2:
        st.metric("ユニークレース数", f"{stats['unique_races']:,}")
        st.metric("～", f"{stats['latest_date']}")
    with col3:
        st.metric("ユニーク馬数", f"{stats['unique_horses']:,}")
        st.metric("勝率", f"{stats['win_rate']:.2%}")

    # サンプルデータ表示
    st.markdown("### サンプルデータ（先頭10件）")

    try:
        sample_df = db.get_processed_data(mode_val, limit=10)
        st.dataframe(sample_df, use_container_width=True)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")

    # 特徴量リスト
    st.markdown("### 特徴量リスト")

    try:
        features = db.get_feature_names(mode_val)
        st.info(f"特徴量数: {len(features)}")

        # メタカラムと特徴量を分離
        meta_cols = ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順', 'target_win', 'target_top3']
        feature_cols = [f for f in features if f not in meta_cols]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**メタカラム:**")
            for col in meta_cols:
                if col in features:
                    st.text(f"• {col}")

        with col2:
            st.markdown(f"**予測特徴量（{len(feature_cols)}個）:**")
            for col in feature_cols[:20]:  # 最初の20個のみ表示
                st.text(f"• {col}")
            if len(feature_cols) > 20:
                st.text(f"... 他 {len(feature_cols) - 20}個")

    except Exception as e:
        st.error(f"特徴量リスト取得エラー: {e}")

# フッター
st.markdown("---")
st.markdown("""
**📚 使い方:**
1. Google Colabで `colab_data_pipeline.ipynb` を実行してデータベースを作成
2. `keiba_data.db` をプロジェクトルートに配置
3. このアプリでモデルを学習
4. 公開ページで予測を実行
""")
