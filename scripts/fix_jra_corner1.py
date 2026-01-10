import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def fix_jra_corner1(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Target the combined line
                    if "'後3F'" in line and "'corner_1': ''," in line:
                         print("  Found combined line.")
                         new_line = line.replace("'corner_1': '',", "'corner_1': corner_vals[0],")
                         new_source.append(new_line)
                         modified = True
                    else:
                        new_source.append(line)
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Fixed corner_1 in {filename}")
        else:
            print(f"⚠️ corner_1 combined line not found in {filename}")

    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    fix_jra_corner1('Colab_JRA_Basic_v2.ipynb')
