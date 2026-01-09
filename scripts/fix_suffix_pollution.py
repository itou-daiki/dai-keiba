import json
import os
import re

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def clean_name_logic(name_var):
    """
    Returns the code string to clean the name variable.
    Removes "の調教師成績", "の騎手成績", "のプロフィール" etc.
    """
    return f"{name_var} = re.sub(r'(の調教師成績|の騎手成績|のプロフィール|｜).*', '', {name_var}).strip()"

def fix_suffix_pollution(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_lines = [l.rstrip('\n') for l in cell['source']]
                new_source = []
                
                # Logic: Find where trainer_val and jockey_val are assigned FINAL values and inject cleaning logic.
                
                for line in source_lines:
                    new_source.append(line)
                    
                    # Fix JOCKEY
                    # Look for lines that assign jockey_val from title or text
                    # "jockey_val = j_link.get('title')"
                    # "jockey_val = j_text"
                    # "jockey_val = get_jockey_fullname..."
                    
                    # Instead of inserting after every assignment, let's insert a cleaning block 
                    # RIGHT BEFORE the horse_data dictionary is created.
                    
                    if "horse_data = {" in line:
                         # Insert cleaning logic before this line
                         # But need to do it before `new_source.append(line)` which was already done.
                         # Pop the line, insert cleaning, then re-append.
                         last = new_source.pop()
                         
                         clean_code = [
                             "            # --- CLEANING NAMES (Suffix Fix) ---",
                             "            if jockey_val: jockey_val = re.sub(r'(の調教師成績|の騎手成績|のプロフィール|｜).*', '', jockey_val).strip()",
                             "            if trainer_val: trainer_val = re.sub(r'(の調教師成績|の騎手成績|のプロフィール|｜).*', '', trainer_val).strip()",
                             "            "
                         ]
                         new_source.extend(clean_code)
                         print(f"  ✅ Inserted Name Cleaning Logic in {filename}")
                         modified = True
                         
                         new_source.append(last)

                if modified:
                    cell['source'] = [s + "\n" for s in new_source]
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved FIXED SUFFIX {filename}")
        else:
            print(f"⚠️ No changes made to {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    fix_suffix_pollution('Colab_JRA_Basic_v2.ipynb')
    fix_suffix_pollution('Colab_NAR_Basic_v2.ipynb')
