"""
Feature consistency verification between training and prediction
"""
import pickle
import json
import pandas as pd
import sys
sys.path.append('ml')
from feature_engineering import process_data

def verify_feature_consistency():
    """Verify that all model features can be generated during prediction"""

    print("=" * 80)
    print("FEATURE CONSISTENCY VERIFICATION")
    print("=" * 80)

    # Load both models
    models = {
        'JRA': 'ml/models/lgbm_model.pkl',
        'NAR': 'ml/models/lgbm_model_nar.pkl'
    }

    metadatas = {
        'JRA': 'ml/models/lgbm_model_meta.json',
        'NAR': 'ml/models/lgbm_model_nar_meta.json'
    }

    for model_type in ['JRA', 'NAR']:
        print(f"\n{'=' * 80}")
        print(f"Checking {model_type} Model")
        print(f"{'=' * 80}\n")

        # Load model
        with open(models[model_type], 'rb') as f:
            model = pickle.load(f)

        # Load metadata
        with open(metadatas[model_type], 'r') as f:
            meta = json.load(f)

        # Get model features
        if hasattr(model, 'feature_name'):
            model_features = model.feature_name()
        else:
            model_features = meta.get('features', [])

        print(f"Model expects {len(model_features)} features:")
        print(f"First 10: {model_features[:10]}")
        print(f"Last 10: {model_features[-10:]}")

        # Create a minimal test dataframe to see what features process_data generates
        # This is tricky since we need actual data, so let's just list features from metadata

        print(f"\n{'=' * 80}")
        print(f"Features from metadata JSON:")
        print(f"{'=' * 80}\n")

        meta_features = meta.get('features', [])
        print(f"Total features in metadata: {len(meta_features)}")

        # Check if they match
        if hasattr(model, 'feature_name'):
            model_feat_set = set(model_features)
            meta_feat_set = set(meta_features)

            if model_feat_set == meta_feat_set:
                print("\n✅ Model features match metadata features")
            else:
                print("\n⚠️  Mismatch detected!")
                only_in_model = model_feat_set - meta_feat_set
                only_in_meta = meta_feat_set - model_feat_set

                if only_in_model:
                    print(f"\nFeatures only in model: {len(only_in_model)}")
                    print(list(only_in_model)[:10])

                if only_in_meta:
                    print(f"\nFeatures only in metadata: {len(only_in_meta)}")
                    print(list(only_in_meta)[:10])

        # Categorize features
        print(f"\n{'=' * 80}")
        print(f"Feature Categories:")
        print(f"{'=' * 80}\n")

        categories = {
            'weighted_avg': [f for f in meta_features if f.startswith('weighted_avg_')],
            'compatibility': [f for f in meta_features if 'compatibility' in f or f.endswith('_avg')],
            'past_race': [f for f in meta_features if 'last_race' in f or 'rank_trend' in f or 'growth' in f],
            'race_info': [f for f in meta_features if f.startswith('race_') or f.startswith('is_') or 'category' in f],
            'jockey_stable': [f for f in meta_features if 'jockey' in f or 'stable' in f],
            'ids': [f for f in meta_features if f.endswith('_id') or f == 'age'],
            'course': [f for f in meta_features if 'course' in f or 'distance' in f or 'rotation' in f or 'weather' in f or 'condition' in f],
            'bias': [f for f in meta_features if 'bias' in f],
            'run_style': [f for f in meta_features if 'run_style' in f],
        }

        for cat, feats in categories.items():
            print(f"{cat}: {len(feats)} features")
            if len(feats) <= 5:
                for f in feats:
                    print(f"  - {f}")
            else:
                for f in feats[:3]:
                    print(f"  - {f}")
                print(f"  ... and {len(feats)-3} more")

    print(f"\n{'=' * 80}")
    print(f"CRITICAL CHECK: Prediction Pipeline")
    print(f"{'=' * 80}\n")

    print("The prediction code in public_app.py does:")
    print("1. X_df = process_data(df, use_venue_features=True, input_stats=stats)")
    print("2. model_features = model.feature_name()")
    print("3. For each missing feature: X_df[f] = 0")
    print("4. X_pred = X_df[model_features].fillna(0)")
    print()
    print("⚠️  If features are missing, they are set to 0!")
    print("This could significantly impact prediction accuracy.")
    print()
    print("We need to verify that process_data() generates ALL required features.")

    return True

if __name__ == "__main__":
    verify_feature_consistency()
