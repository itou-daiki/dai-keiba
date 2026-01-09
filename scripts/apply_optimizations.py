import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def optimize_details_notebook(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    if "pd.read_csv(basic_path" in line and "usecols" not in line:
                        # Add usecols
                        # Original: df_basic = pd.read_csv(basic_path, dtype=str, on_bad_lines='skip')
                        # New:      df_basic = pd.read_csv(basic_path, dtype=str, on_bad_lines='skip', usecols=['race_id', 'horse_id', '日付'])
                        # We need to be careful with matching.
                        if "pd.read_csv(basic_path, dtype=str, on_bad_lines='skip')" in line:
                             new_line = line.replace(
                                 "pd.read_csv(basic_path, dtype=str, on_bad_lines='skip')",
                                 "pd.read_csv(basic_path, dtype=str, on_bad_lines='skip', usecols=['race_id', 'horse_id', '日付'])"
                             )
                             new_source.append(new_line)
                             modified = True
                             print(f"  ✅ Optimized line in {filename}")
                        else:
                             new_source.append(line)
                    else:
                        new_source.append(line)
                cell['source'] = new_source
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved optimized {filename}")
        else:
            print(f"⚠️ No changes made to {filename} (maybe already optimized?)")
            
    except Exception as e:
        print(f"❌ Error optimizing {filename}: {e}")

def fix_nar_basic_notebook(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Fix missing 'コーナー通過順'
                    if "'後3F': cells[11].text.strip()" in line and "コーナー通過順" not in line:
                         # We append the missing key
                         # Original: '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                         # We want to add 'コーナー通過順': '',
                         # But easier to just replace or append.
                         # Let's verify the line content precisely from previous view.
                         # Line 345: '                '単勝オッズ': cells[10].text.strip() if len(cells) > 10 else '',\n'
                         # Wait, line 345 in step 17 is '後3F'.
                         # 345: "                '後3F': cells[11].text.strip() if len(cells) > 11 else '',\n"
                         new_line = line.rstrip() + " 'コーナー通過順': '',\n"
                         new_source.append(new_line)
                         modified = True
                         print(f"  ✅ Fixed missing column in {filename}")
                    else:
                        new_source.append(line)
                cell['source'] = new_source
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved fixed {filename}")
        else:
            print(f"⚠️ No fixes made to {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    optimize_details_notebook('Colab_JRA_Details_v2.ipynb')
    optimize_details_notebook('Colab_NAR_Details_v2.ipynb')
    fix_nar_basic_notebook('Colab_NAR_Basic_v2.ipynb')
