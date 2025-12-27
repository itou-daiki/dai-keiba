import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

# --- 1. Mock Streamlit to avoid Import Side-Effects ---
# This prevents public_app.py from capturing inputs or running logic at module level that triggers load_model
mock_st = MagicMock()
mock_st.text_input.return_value = "" # race_id is empty, preventing if race_id: block
mock_st.radio.return_value = "JRA (中央競馬)"
# Mock columns to return dynamic list
def mock_columns(spec):
    if isinstance(spec, int):
        return [MagicMock() for _ in range(spec)]
    elif isinstance(spec, list):
        return [MagicMock() for _ in range(len(spec))]
    return [MagicMock(), MagicMock()]

mock_st.columns.side_effect = mock_columns
mock_st.button.return_value = False
mock_st.checkbox.return_value = False
mock_st.session_state = {}
sys.modules['streamlit'] = mock_st

# Add paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT))
sys.path.append(os.path.join(PROJECT_ROOT, 'ml'))
sys.path.append(os.path.join(PROJECT_ROOT, 'app'))

# Import after mocking
from ml.feature_engineering import process_data
from app.public_app import load_stats, predict_race_logic

# --- 2. Dummy Model ---
class DummyModel:
    def feature_name(self):
        # Return features expected by the model. 
        # These must match what process_data produces roughly or just be generic
        return ['jockey_win_rate', 'course_distance_record', 'weight_change']
    
    def predict(self, X):
        # Return random probabilities
        return np.random.rand(len(X))

def verify_prediction(mode="NAR"):
    print(f"=== Verifying Prediction Logic ({mode}) ===")
    
    # 1. Load Stats (Real Stats)
    print("1. Loading Stats...")
    stats = load_stats(mode)
    if stats:
        print("   Success!")
        if 'jockey' in stats:
            print(f"   Jockey Stats: {len(stats['jockey']['win_rate'])} entries")
    else:
        print("   Failed to load stats (Check if export_stats.py ran)!")
        # Proceed with empty stats to test logic robustness
        stats = {'jockey': {'win_rate': {}, 'top3_rate': {}}}

    # 2. Use Dummy Model
    print("\n2. Using Dummy Model...")
    model = DummyModel()
    model_meta = {'performance': {'auc': 0.8}, 'data_stats': {'total_records': 5000}}

    # 3. Create Dummy Data
    print("\n3. Creating Dummy Race Data...")
    data = {
        '日付': ['2025年05月01日'],
        '会場': ['大井'],
        'レース名': ['テストレース'],
        '枠': ['1'],
        '馬 番': ['1'],
        '馬名': ['テストホース'],
        'horse_id': ['123456'],
        '騎手': ['森泰斗'], # Known jockey
        '斤量': ['56.0'],
        '距離': ['1200'],
        'コースタイプ': ['ダ'],
        '回り': ['右'],
        '天候': ['晴'],
        '馬場状態': ['良'],
        '性齢': ['牡4'],
        '単勝': [1.0],
        'date': ['2025/05/01'],
    }
    # Add minimal past data
    for i in range(1, 6):
        data[f'past_{i}_date'] = [None]
        data[f'past_{i}_rank'] = [None]
        
    df = pd.DataFrame(data)

    # 4. Run Prediction Logic
    print("\n4. Running predict_race_logic with Stats...")
    try:
        # Pass stats explicitly
        processed_df = predict_race_logic(df, model, model_meta, stats=stats)
        
        if processed_df is not None:
             print("   Prediction Success!")
             
             # Check if stats columns exist
             if 'jockey_win_rate' in processed_df.columns:
                 val = processed_df['jockey_win_rate'].iloc[0]
                 print(f"   jockey_win_rate: {val}")
                 
                 # Logic check: if stats loaded and '森泰斗' exists, val should be > 0
                 # If using empty stats, val is 0.0
                 if stats.get('jockey', {}).get('win_rate'):
                      print("   (Stats were available for lookup)")
             else:
                 print("   ERROR: jockey_win_rate column missing!")

             if 'Confidence' in processed_df.columns:
                 print(f"   Confidence: {processed_df['Confidence'].iloc[0]}")
             else:
                 print("   ERROR: Confidence column missing!")
                 
        else:
             print("   Prediction Failed (returned None)")
             
    except Exception as e:
        print(f"   Error during prediction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_prediction("NAR")
