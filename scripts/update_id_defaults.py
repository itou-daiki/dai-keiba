import json
import os

NOTEBOOK_PATH = '/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_ID_Fetcher.ipynb'

def update_defaults():
    try:
        with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Update Constants
                    if "START_YEAR = 2025" in line:
                         print("  Found START_YEAR constant")
                         new_source.append(line.replace("2025", "2020"))
                         modified = True
                    
                    # Update Function Definition
                    elif "def fetch_race_ids(mode='JRA', start_year=2025, end_year=2026):" in line:
                         print("  Found fetch_race_ids definition")
                         new_source.append(line.replace("start_year=2025", "start_year=2020"))
                         modified = True
                         
                    else:
                        new_source.append(line)
                cell['source'] = new_source

        if modified:
            with open(NOTEBOOK_PATH, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Updated Defaults in {NOTEBOOK_PATH}")
        else:
            print(f"⚠️ No changes made (Patterns not found)")

    except Exception as e:
        print(f"❌ Error updating notebook: {e}")

if __name__ == "__main__":
    update_defaults()
