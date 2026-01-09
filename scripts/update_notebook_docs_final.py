import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

# The correct list of 32 columns (Removed コーナー通過順 from 33)
# Old: 33カラム: ... コーナー通過順、corner_1~4 ...
# New: 32カラム: ... corner_1~4 ...
CORRECT_COLUMNS_TEXT = "- **32カラム**: 日付、会場、レース番号、レース名、重賞、コースタイプ、距離、回り、天候、馬場状態、着順、枠、馬番、馬名、性齢、斤量、騎手、タイム、着差、人気、単勝オッズ、後3F、corner_1~4、厩舎、調教師、馬体重、増減、race_id、horse_id"

def update_notebook_docs_final(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        for cell in nb['cells']:
            if cell['cell_type'] == 'markdown':
                new_source = []
                for line in cell['source']:
                    if "- **33カラム**:" in line or "- **26カラム**:" in line:
                         new_source.append(CORRECT_COLUMNS_TEXT + "\n")
                         modified = True
                         print(f"  ✅ Updated documentation in {filename}")
                    else:
                        new_source.append(line)
                cell['source'] = new_source
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved updated {filename}")
        else:
            print(f"⚠️ No documentation changes made to {filename}")
            
    except Exception as e:
        print(f"❌ Error updating {filename}: {e}")

if __name__ == "__main__":
    update_notebook_docs_final('Colab_JRA_Basic_v2.ipynb')
    update_notebook_docs_final('Colab_NAR_Basic_v2.ipynb')
