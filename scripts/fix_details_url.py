import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def fix_url_logic(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Target: url = f"https://db.netkeiba.com/horse/{horse_id}/"
                    if 'url = f"https://db.netkeiba.com/horse/{horse_id}/"' in line:
                         print(f"  Found URL line in {filename}")
                         new_line = line.replace("/horse/{horse_id}/", "/horse/result/{horse_id}/")
                         new_source.append(new_line)
                         modified = True
                    else:
                        new_source.append(line)
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Updated URL to /result/ in {filename}")
        else:
            print(f"⚠️ URL pattern not found/changed in {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    fix_url_logic('Colab_JRA_Details_v2.ipynb')
    fix_url_logic('Colab_NAR_Details_v2.ipynb')
