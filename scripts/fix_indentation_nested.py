import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_pedigree_nested(filepath):
    print(f"🔧 Fixing Pedigree Nested in {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                in_pedigree_try = False
                indent_level = 0
                
                for line in cell['source']:
                    # Detect start of Pedigree Block
                    if "# --- PEDIGREE FETCH" in line:
                         in_pedigree_try = True
                         new_source.append(line)
                         continue
                    
                    if in_pedigree_try:
                         # Check strict end
                         if "except" in line and "Exception" in line:
                              # End of try block
                              in_pedigree_try = False
                              new_source.append(line)
                              continue
                         
                         if "except: pass" in line:
                              in_pedigree_try = False
                              new_source.append(line)
                              continue
                         
                         clean = line.strip()
                         # Base indent for 'try' body is 16 spaces
                         base_indent = "                " 
                         
                         # Check if this line is part of 'if blood_tbl:' block
                         # 'if blood_tbl:' itself is at 16 spaces.
                         # Lines inside need 20 spaces.
                         
                         if clean.startswith("if blood_tbl:"):
                              new_source.append(base_indent + clean + "\n")
                              continue
                         
                         if clean.startswith("if len(tds)"):
                              # This is inside 'if blood_tbl:' -> 20 spaces
                              new_source.append(base_indent + "    " + clean + "\n")
                              continue
                         
                         if clean.startswith("tds ="):
                              # Inside 'if blood_tbl:' -> 20 spaces
                              new_source.append(base_indent + "    " + clean + "\n")
                              continue
                         
                         if clean.startswith("if len(tds) > 0"):
                              new_source.append(base_indent + "    " + clean + "\n")
                              continue
                         
                         if clean.startswith("details['father']"):
                             # This is inside 'if len(tds) > 0'?? No, it was a one-liner `if ...: code`
                             # `if len(tds) > 0: details['father'] = ...`
                             # My injection script used one-liner.
                             # But let's check what 'clean' looks like.
                             if "if len(tds)" in clean:
                                  # It's the if line.
                                  new_source.append(base_indent + "    " + clean + "\n")
                             else:
                                  # Standalone details assignment? Not in my injected code.
                                  new_source.append(base_indent + clean + "\n")
                             continue
                         
                         if clean == "pass":
                              # pass for 'if blood_tbl' or 'try'?
                              # If indented heavily, it's for 'if'.
                              # Let's assume 20 spaces
                              new_source.append(base_indent + "    " + clean + "\n")
                              continue
                         
                         # Default for other lines (ped_url, r_ped, etc) -> 16 spaces
                         new_source.append(base_indent + clean + "\n")
                         
                    else:
                         new_source.append(line)
                
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Nested Fix Applied to {filepath}")
        else:
            print(f"⚠️ No changes needed for {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_pedigree_nested(nb)
