import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_indent_force(filepath):
    print(f"🔧 Forcing Indent for {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Target the Pedigree block lines
                    # They start with 8 spaces based on previous view.
                    # We want 12 spaces to be inside 'if table:' block.
                    
                    targets = [
                        "# --- PEDIGREE FETCH",
                        "try:",
                        "except Exception as e: pass",
                        "except: pass",
                        "# Only fetch if",
                        "ped_url =",
                        "time.sleep(0.5)",
                        "r_ped =",
                        "soup_ped =",
                        "blood_tbl =",
                        "if blood_tbl:",
                        "tds =",
                        "if len(tds)",
                        "details['father'] =",
                        "pass",
                        "# ---------------------------------"
                    ]
                    
                    # Check if line contains any target and starts with 8 spaces
                    # But we must be careful not to trigger on other try/excepts.
                    # We can use the 'PEDIGREE' comment as a state switch?
                    # Or just brute force: if it looks like our injected code, indent it.
                    
                    is_injected = False
                    for t in targets:
                        if t in line:
                            is_injected = True
                            break
                    
                    if is_injected:
                        # Check current indent
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent == 8:
                            # Add 4 spaces
                            new_line = "    " + line
                            new_source.append(new_line)
                            modified = True
                        else:
                            new_source.append(line)
                    else:
                        new_source.append(line)
                
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Re-indented {filepath}")
        else:
            print(f"⚠️ No massive re-indent needed for {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_indent_force(nb)
