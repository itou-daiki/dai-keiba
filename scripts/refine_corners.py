import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def refine_jra_corners(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Hook into JRA loop
                    if "'後3F': cells[11].text.strip()" in line:
                         new_source.append(line)
                         # Insert Logic used to be here or after
                    
                    elif "'corner_1': ''," in line:
                        # We leave initialization as ''
                        new_source.append(line)
                    
                    elif "# 基本情報を辞書で構築" in line:
                        # Insert parsing block BEFORE dict construction
                        block = [
                            "            # --- Corner Extraction (Refined) ---\n",
                            "            corner_vals = ['', '', '', '']\n",
                            "            corner_cell = cells[12] if len(cells) > 12 else None\n",
                            "            if corner_cell:\n",
                            "                raw_c = corner_cell.text.strip()\n",
                            "                if raw_c:\n",
                            "                    # Split by - and take last 4\n",
                            "                    parts = raw_c.replace(' ', '-').split('-')\n",
                            "                    valid_c = parts[-4:]\n",
                            "                    for i, v in enumerate(valid_c):\n",
                            "                        if i < 4: corner_vals[i] = v\n",
                            "            \n"
                        ]
                        new_source.extend(block)
                        new_source.append(line)
                        modified = True
                    
                    elif "'corner_1': ''," in line and False: 
                        # This logic is hard to replace via simple string match since it's inside dict
                        # Instead, we will REPLACE the values inside the dict definition
                        pass # handled by variable prep
                        
                    elif "'corner_1': ''," in line:
                         # We can replace this line with variable
                         new_source.append("                'corner_1': corner_vals[0],\n")
                    elif "'corner_2': ''," in line:
                         new_source.append("                'corner_2': corner_vals[1],\n")
                    elif "'corner_3': ''," in line:
                         new_source.append("                'corner_3': corner_vals[2],\n")
                    elif "'corner_4': ''," in line:
                         new_source.append("                'corner_4': corner_vals[3],\n")
                         
                    else:
                        new_source.append(line)
                
                if modified:
                    cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Updated JRA Corners in {filename}")
        else:
            print(f"⚠️ No massive change for JRA corners (check if already applied)")

    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

def refine_nar_corners(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Find NAR loop reversed logic
                    if "for j, pos in enumerate(reversed(corner_positions_forward)):" in line:
                        # Replace with forward last-4 logic
                        new_source.append("            # Take Last 4 Chronological\n")
                        new_source.append("            valid_corners = corner_positions_forward[-4:]\n")
                        new_source.append("            for j, pos in enumerate(valid_corners):\n")
                        new_source.append("                horse_data[f'corner_{j+1}'] = pos\n")
                        modified = True
                    elif "if j < 4: horse_data[f'corner_{j+1}'] = pos" in line:
                         # This line is removed/replaced by above block logic implicitly
                         pass 
                    else:
                        new_source.append(line)
                        
                if modified:
                    cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Updated NAR Corners in {filename}")
        else:
            print(f"⚠️ NAR Corners logic not matched")

    except Exception as e:
        print(f"❌ Error checking {filename}: {e}")

if __name__ == "__main__":
    refine_jra_corners('Colab_JRA_Basic_v2.ipynb')
    refine_nar_corners('Colab_NAR_Basic_v2.ipynb')
