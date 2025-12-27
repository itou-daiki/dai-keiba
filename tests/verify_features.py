
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.feature_engineering import process_data

def test_feature_generation():
    print("Creating dummy data...")
    # Create improved dummy data with dates, jockeys, etc.
    data = {
        '日付': ['2023年1月1日', '2023年1月1日', '2023年1月2日', '2023年1月2日', '2023年1月3日'],
        '会場': ['大井', '大井', '大井', '大井', '川崎'],
        '距離': [1200, 1200, 1200, 1200, 1400],
        '着 順': [1, 2, 1, 3, 1],
        '馬名': ['HorseA', 'HorseB', 'HorseA', 'HorseC', 'HorseA'],
        '騎手': ['Jockey1', 'Jockey2', 'Jockey1', 'Jockey3', 'Jockey1'],
        '厩舎': ['Stable1', 'Stable2', 'Stable1', 'Stable3', 'Stable1'],
        'レース名': ['R1', 'R1', 'R2', 'R2', 'R3'],
        # Add minimal required cols
        '馬 番': [1, 2, 1, 3, 1],
        '枠': [1, 2, 1, 3, 1],
        '性齢': ['牡3', '牝3', '牡3', '牡3', '牡3'],
        '斤量': [56, 54, 56, 56, 56],
        'タイム': ['1:15.0', '1:15.1', '1:14.9', '1:15.2', '1:29.0'],
        '単勝 オッズ': [2.5, 3.0, 2.0, 5.0, 1.8],
        '馬体重(増減)': ['500(+2)', '480(0)', '500(0)', '490(-2)', '502(+2)'],
        'weather': ['晴', '晴', '曇', '曇', '雨'], # often weather is not in correct col in raw csv, handled by map
        'past_1_date': [None, None, '2023/1/1', None, '2023/1/2'],
        'past_1_rank': [None, None, 1, None, 1]
    }
    df = pd.DataFrame(data)
    
    print("Running process_data...")
    processed_df = process_data(df)
    
    print("Processed Columns:", processed_df.columns.tolist())
    
    print("Checking new features...")
    new_cols = ['jockey_win_rate', 'course_distance_record', 'jockey_compatibility']
    for col in new_cols:
        if col in processed_df.columns:
            print(f"✅ {col} created.")
            # Only print if columns exist
            cols_to_show = [c for c in ['日付', '馬名', '騎手', col] if c in processed_df.columns]
            print(processed_df[cols_to_show])
        else:
            print(f"❌ {col} missing!")

    # Verify Logic
    # HorseA wins on Jan 1. 
    # On Jan 2 (row 2), HorseA should see jockey_win_rate updated?
    # Note: calculate_rolling_stats usage.
    # Row 0: NaN (first race)
    # Row 2 (HorseA, Jan2): Should reflect Jan 1 result?
    # Actually our rolling stats logic groups by Jockey.
    # Jockey1 wins row 0. 
    # Row 2 is Jockey1. So Jockey1 stats for Row 2 should be > 0.
    
    j_win = processed_df.loc[2, 'jockey_win_rate']
    print(f"Jockey1 Win Rate at 2nd race: {j_win}")
    
    if j_win > 0:
        print("✅ Jockey global stats working (look-behind).")
    else:
        print("⚠️ Jockey stats might be 0 if shift logic is strict or data too small.")

if __name__ == "__main__":
    test_feature_generation()
