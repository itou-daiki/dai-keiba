"""
SHAP値による予測根拠の可視化
"""

import pandas as pd
import numpy as np
import pickle
import os

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠️ SHAP not installed. Install with: pip install shap")


def explain_prediction(model, X_pred, feature_names, horse_names=None):
    """
    SHAP値を使って予測の根拠を説明

    Args:
        model: 学習済みモデル
        X_pred: 予測対象データ (DataFrame or ndarray)
        feature_names: 特徴量名のリスト
        horse_names: 馬名のリスト (optional)

    Returns:
        dict: SHAP値の解析結果
    """
    if not SHAP_AVAILABLE:
        return None

    print("🔍 Calculating SHAP values...")

    # Create explainer for tree-based models
    explainer = shap.TreeExplainer(model)

    # Calculate SHAP values
    shap_values = explainer.shap_values(X_pred)

    # If binary classification, shap_values might be for class 1
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # Class 1 (top 3)

    # Get base value
    base_value = explainer.expected_value
    if isinstance(base_value, list):
        base_value = base_value[1]

    results = []

    for i in range(len(X_pred)):
        horse_name = horse_names[i] if horse_names and i < len(horse_names) else f"Horse {i+1}"

        # Get feature contributions for this horse
        contributions = []

        for j, feature in enumerate(feature_names):
            shap_val = shap_values[i][j]
            feature_val = X_pred.iloc[i, j] if isinstance(X_pred, pd.DataFrame) else X_pred[i][j]

            contributions.append({
                'feature': feature,
                'value': feature_val,
                'shap_value': shap_val,
                'impact': '+' if shap_val > 0 else '-'
            })

        # Sort by absolute SHAP value
        contributions = sorted(contributions, key=lambda x: abs(x['shap_value']), reverse=True)

        # Get top 5 positive and negative contributions
        top_positive = [c for c in contributions if c['shap_value'] > 0][:5]
        top_negative = [c for c in contributions if c['shap_value'] < 0][:5]

        results.append({
            'horse_name': horse_name,
            'base_value': base_value,
            'prediction': base_value + shap_values[i].sum(),
            'top_positive': top_positive,
            'top_negative': top_negative,
            'all_contributions': contributions
        })

    return results


def format_explanation_text(explanation):
    """
    説明を読みやすいテキストにフォーマット

    Args:
        explanation: explain_predictionの結果（1頭分）

    Returns:
        str: フォーマットされた説明文
    """
    text = f"🐴 {explanation['horse_name']}\n"
    text += f"AI予測: {explanation['prediction']:.1%}\n\n"

    text += "📈 プラス要因（トップ5）:\n"
    for contrib in explanation['top_positive']:
        feature = contrib['feature']
        shap_val = contrib['shap_value']
        feature_val = contrib['value']
        text += f"  ✅ {feature}: {feature_val:.2f} (+{shap_val:.3f})\n"

    text += "\n📉 マイナス要因（トップ5）:\n"
    for contrib in explanation['top_negative']:
        feature = contrib['feature']
        shap_val = contrib['shap_value']
        feature_val = contrib['value']
        text += f"  ⚠️ {feature}: {feature_val:.2f} ({shap_val:.3f})\n"

    return text


def explain_race(model_path, X_pred, feature_names, horse_names=None):
    """
    レース全体の予測を説明

    Args:
        model_path: モデルファイルのパス
        X_pred: 予測対象データ
        feature_names: 特徴量名のリスト
        horse_names: 馬名のリスト

    Returns:
        list: 各馬の説明
    """
    if not SHAP_AVAILABLE:
        print("⚠️ SHAP is not installed. Cannot generate explanations.")
        return None

    # Load model
    if not os.path.exists(model_path):
        print(f"Model file {model_path} not found.")
        return None

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # Calculate explanations
    explanations = explain_prediction(model, X_pred, feature_names, horse_names)

    return explanations


def create_simple_explanation(prediction, features_df):
    """
    SHAP不要の簡易説明（特徴量の値を直接表示）

    Args:
        prediction: 予測確率
        features_df: 特徴量DataFrame（1行）

    Returns:
        dict: 簡易説明
    """
    # Feature importance based on typical patterns
    important_features = {
        'weighted_avg_rank': '直近平均着順',
        'weighted_avg_last_3f': '直近上り3F',
        'jockey_compatibility': '騎手相性',
        'turf_compatibility': '芝適性',
        'dirt_compatibility': 'ダート適性',
        'distance_compatibility': '距離適性',
        'is_rest_comeback': '休養明け',
        'race_class': 'レースクラス',
    }

    explanation_parts = []

    for col, label in important_features.items():
        if col in features_df.columns:
            value = features_df[col].values[0]

            if col == 'weighted_avg_rank':
                if value < 5:
                    explanation_parts.append(f"✅ {label}: {value:.1f}着 (好成績)")
                elif value > 10:
                    explanation_parts.append(f"⚠️ {label}: {value:.1f}着 (やや不安)")
                else:
                    explanation_parts.append(f"➖ {label}: {value:.1f}着 (平均的)")

            elif col == 'weighted_avg_last_3f':
                if value < 37:
                    explanation_parts.append(f"✅ {label}: {value:.1f}秒 (高速)")
                elif value > 40:
                    explanation_parts.append(f"⚠️ {label}: {value:.1f}秒 (やや遅い)")

            elif col in ['jockey_compatibility', 'turf_compatibility', 'dirt_compatibility', 'distance_compatibility']:
                if value < 5:
                    explanation_parts.append(f"✅ {label}: 好適性")
                elif value > 10:
                    explanation_parts.append(f"⚠️ {label}: 不向き")

            elif col == 'is_rest_comeback' and value == 1:
                explanation_parts.append(f"⚠️ {label}: 3ヶ月以上の休養明け")

    if len(explanation_parts) == 0:
        explanation_parts.append("特徴量データ不足")

    return {
        'prediction': prediction,
        'explanation': '\n'.join(explanation_parts)
    }


if __name__ == "__main__":
    # Test
    if SHAP_AVAILABLE:
        print("✅ SHAP is available")
    else:
        print("❌ SHAP is not available")

    print("\nTo install SHAP, run:")
    print("  pip install shap")
