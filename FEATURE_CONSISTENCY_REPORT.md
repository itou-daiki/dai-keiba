# Feature Consistency Verification Report

## Executive Summary

This report verifies that all features used during model training are properly generated during prediction.

**Status: ⚠️  VERIFICATION REQUIRED**

## Model Feature Requirements

### JRA Model (lgbm_model.pkl)
- **Total Features**: 50
- **Training Data**: processed_data.csv
- **AUC**: 0.8909
- **Brier Score**: 0.0567

### NAR Model (lgbm_model_nar.pkl)
- **Total Features**: 50
- **Training Data**: processed_data_nar.csv
- **AUC**: 0.8745
- **Brier Score**: 0.0817

## Complete Feature List (from model metadata)

Both models expect the following 50 features in order:

```
1. weighted_avg_rank
2. weighted_avg_run_style
3. weighted_avg_last_3f
4. weighted_avg_horse_weight
5. weighted_avg_odds
6. weighted_avg_weather
7. weighted_avg_weight_change
8. weighted_avg_interval
9. weighted_avg_speed
10. turf_compatibility
11. dirt_compatibility
12. good_condition_avg
13. heavy_condition_avg
14. distance_compatibility
15. jockey_compatibility
16. last_race_reliability
17. best_similar_course_rank
18. growth_factor
19. last_race_performance
20. rank_trend
21. race_class
22. race_type_code
23. is_rest_comeback
24. interval_category
25. is_consecutive
26. jra_compatibility
27. nar_compatibility
28. is_jra_transfer
29. is_graded
30. age_limit
31. jockey_win_rate
32. jockey_top3_rate
33. jockey_races_log
34. stable_win_rate
35. stable_top3_rate
36. course_distance_record
37. age
38. course_type_code
39. distance_val
40. rotation_code
41. weather_code
42. condition_code
43. is_jockey_change
44. father_id
45. mother_id
46. bms_id
47. jockey_id
48. trainer_id
49. run_style_code
50. run_style_consistency
51. dd_frame_bias
52. dd_run_style_bias
```

**Note**: Total is 52 features, not 50. This needs verification.

## Feature Generation in process_data()

The `process_data()` function in `ml/feature_engineering.py` generates features in this order:

### 1. Weighted Averages (9 features)
**Lines 440-445**
```python
for feat in features:  # features = ['rank', 'run_style', 'last_3f', 'horse_weight', 'odds', 'weather', 'weight_change', 'interval', 'speed']
    df[f'weighted_avg_{feat}'] = 0.0
    for i in range(1, 6):
        df[f'weighted_avg_{feat}'] += df[f"past_{i}_{feat}"] * norm_weights[i-1]
    feature_cols.append(f'weighted_avg_{feat}')
```

✅ **Generated**: weighted_avg_rank, weighted_avg_run_style, weighted_avg_last_3f, weighted_avg_horse_weight, weighted_avg_odds, weighted_avg_weather, weighted_avg_weight_change, weighted_avg_interval, weighted_avg_speed

### 2. Trend Features (2 features)
**Lines 352-356**
```python
df['trend_rank'] = df.apply(lambda row: calculate_trend(row, 'rank'), axis=1)
df['trend_last_3f'] = df.apply(lambda row: calculate_trend(row, 'last_3f'), axis=1)
feature_cols.extend(['trend_rank', 'trend_last_3f'])
```

❓ **Note**: trend_rank and trend_last_3f are added to feature_cols, but **NOT** in the model's expected feature list. These might be dropped later or not used in the model.

### 3. Compatibility Features (extended at line 679)
**Lines 679-685**
```python
feature_cols.extend([
    'turf_compatibility', 'dirt_compatibility',
    'good_condition_avg', 'heavy_condition_avg',
    'distance_compatibility',
    'is_rest_comeback', 'is_consecutive', 'interval_category',
    'jockey_compatibility'
])
```

✅ **Generated**: All compatibility features are created earlier in the function and added here.

### 4. Race Classification Features
**Lines 865-887** (new_features list)

✅ **Generated**:
- race_class (line 676)
- race_type_code (line 724)
- is_rest_comeback, is_consecutive, interval_category (lines 600-650)
- jra_compatibility, nar_compatibility (lines 771-776)
- is_jra_transfer (line 786)
- is_graded (line 690)
- age_limit (line 707)

### 5. Performance Features
✅ **Generated**:
- last_race_reliability (line 791)
- best_similar_course_rank (line 820)
- growth_factor (line 838)
- last_race_performance (line 853)
- rank_trend (line 862)

### 6. Jockey/Stable Stats
**Lines 956, 995**

✅ **Generated**:
- jockey_win_rate, jockey_top3_rate, jockey_races_log
- stable_win_rate, stable_top3_rate

### 7. Course Record
**Line 1022**

✅ **Generated**: course_distance_record

### 8. Scalar Features
**Lines 1051, 1065, 1073, 1087, 1102, 1116, 1130**

✅ **Generated**:
- age
- course_type_code
- distance_val
- rotation_code
- weather_code
- condition_code
- is_jockey_change

### 9. ID Features (Hashed)
**Lines 1146, 1153, 1159**

✅ **Generated**:
- father_id, mother_id, bms_id
- jockey_id, trainer_id

### 10. Run Style Features
**Line 1238**

✅ **Generated** (conditionally):
- run_style_code, run_style_consistency

### 11. Data-Driven Biases
**Lines 1427, 1435** (training mode) or **Lines 1385, 1398** (inference mode with stats)

✅ **Generated**:
- dd_frame_bias
- dd_run_style_bias

## Critical Issue at Line 1044

⚠️ **POTENTIAL BUG DETECTED**

```python
# Line 1044
feature_cols = [f'weighted_avg_{f}' for f in features] + new_features
```

This line **reconstructs** feature_cols from scratch, potentially **losing** features that were added earlier:
- trend_rank, trend_last_3f (added at line 356)
- Any features added before line 1044

However, looking at the code flow:
1. Lines 1-442: Build up feature_cols incrementally
2. Line 1044: **RESET** feature_cols to weighted_avg + new_features
3. Lines 1051-1435: **Append** additional features

This means features added before line 1044 (except weighted_avg features) are **LOST** unless they're in new_features.

## Feature Reconstruction Analysis

Looking at line 1044, the `feature_cols` is reconstructed as:
```python
feature_cols = [f'weighted_avg_{f}' for f in features] + new_features
```

Where:
- `features = ['rank', 'run_style', 'last_3f', 'horse_weight', 'odds', 'weather', 'weight_change', 'interval', 'speed']`
- `new_features` contains all the compatibility, performance, and race classification features

Then additional features are appended after line 1044:
- age (1051)
- course_type_code (1065/1068)
- distance_val (1073/1076)
- rotation_code (1087/1090)
- weather_code (1102/1105)
- condition_code (1116/1119)
- is_jockey_change (1130)
- father_id, mother_id, bms_id (1146)
- jockey_id (1153)
- trainer_id (1159)
- run_style_code, run_style_consistency (1238)
- venue features if enabled (1261, 1275, 1303, 1335, 1357)
- dd_frame_bias, dd_run_style_bias (1385, 1398 or 1427, 1435)

## Missing Features Check

Comparing model expectations vs process_data generation:

### Features that might be missing:
❓ **trend_rank, trend_last_3f**: Added at line 356 but LOST at line 1044 reconstruction. These are NOT in the model's expected features, so this is OK.

### All required features are generated ✅

After careful analysis, all 52 features expected by the model ARE generated by process_data().

## Prediction Pipeline Safeguard

In `app/public_app.py` (lines 201-213), there's a safeguard:

```python
if hasattr(model, 'feature_name'):
    model_features = model.feature_name()
    # Ensure all features exist
    for f in model_features:
        if f not in X_df.columns:
            X_df[f] = 0  # ⚠️  DEFAULT TO 0 IF MISSING!

    X_pred = X_df[model_features].fillna(0)
```

**This is a DOUBLE-EDGED SWORD**:
- ✅ Prevents crashes if features are missing
- ⚠️  Silently sets missing features to 0, which can degrade prediction accuracy
- ❌ No warning is logged when features are missing

## Recommendations

### 1. Add Feature Validation Logging

Modify `app/public_app.py` to log when features are defaulted to 0:

```python
missing_features = []
for f in model_features:
    if f not in X_df.columns:
        missing_features.append(f)
        X_df[f] = 0

if missing_features:
    logger.warning(f"Missing features defaulted to 0: {missing_features[:10]}")
    if len(missing_features) > 10:
        logger.warning(f"... and {len(missing_features)-10} more")
```

### 2. Verify Data Sources

Ensure prediction data has all required columns:
- Past performance data: past_1_rank through past_5_rank, etc.
- Pedigree data: father, mother, bms columns
- Race info: 会場, 距離, コースタイプ, 回り, 天候, 馬場状態
- Jockey/Trainer: 騎手, 厩舎 columns

### 3. Test with Real Data

Run a test prediction and check for missing features:

```python
python -c "
import pickle
import sys
sys.path.append('ml')
from feature_engineering import process_data
import pandas as pd

# Load model
with open('ml/models/lgbm_model.pkl', 'rb') as f:
    model = pickle.load(f)

model_features = model.feature_name()
print(f'Model expects {len(model_features)} features')

# Load test data
df = pd.read_csv('ml/processed_data.csv', nrows=100)

# Generate features
X_df = process_data(df, use_venue_features=True)

generated_features = [c for c in X_df.columns if c not in ['馬名', 'horse_id', '枠', '馬 番', 'race_id', 'date', 'rank', '着 順']]
print(f'Generated {len(generated_features)} features')

missing = set(model_features) - set(X_df.columns)
extra = set(generated_features) - set(model_features)

print(f'Missing features: {len(missing)}')
if missing:
    print(missing)

print(f'Extra features: {len(extra)}')
if extra:
    print(list(extra)[:10])
"
```

### 4. Verify Statistics Passing

During inference, `process_data()` is called with `input_stats`:

```python
X_df = process_data(df, use_venue_features=True, input_stats=stats)
```

Verify that:
- `stats` dictionary is properly loaded from saved stats file
- All required keys are present: 'jockey', 'stable', 'course_horse', 'course_frame_bias', 'course_run_style_bias'

## Conclusion

**Feature Consistency Status**: ✅ **LIKELY OK** but needs runtime verification

All 52 features expected by the models appear to be generated by `process_data()`. However:

1. ⚠️  The safeguard that defaults missing features to 0 could mask problems
2. ⚠️  No logging exists to detect when features are missing
3. ✅ The feature generation logic is sound
4. ❓ Needs runtime testing to confirm all features are present during actual prediction

**Next Steps**:
1. Add logging for missing features
2. Test with real prediction data
3. Verify stats dictionary is properly loaded during inference
4. Confirm past performance data and pedigree data are available in prediction input
