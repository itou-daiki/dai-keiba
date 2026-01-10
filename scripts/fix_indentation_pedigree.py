import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_pedigree_body(filepath):
    print(f"🔧 Fixing Pedigree Body in {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                # State tracking
                in_pedigree_try = False
                
                for line in cell['source']:
                    # Identify the Pedigree Try block
                    if "# --- PEDIGREE FETCH" in line:
                         # Ensure this header is at 12 spaces
                         if not line.startswith("            #"):
                              new_source.append("            # --- PEDIGREE FETCH (Dual URL) ---\n")
                              modified = True
                              continue
                         else:
                              new_source.append(line)
                              continue
                    
                    if "try:" in line and "PEDIGREE" not in line: 
                         # Check context. If previous lines were Pedigree, this is the one.
                         # Or check indent.
                         # If it's the one after PEDIGREE FETCH
                         if len(new_source) > 0 and "PEDIGREE FETCH" in new_source[-1]:
                              in_pedigree_try = True
                              # Ensure 'try:' is at 12 spaces
                              clean = line.strip()
                              if line != "            try:\n":
                                   new_source.append("            try:\n")
                                   modified = True
                              else:
                                   new_source.append(line)
                              continue
                    
                    if in_pedigree_try:
                         # We are inside the Pedigree try block.
                         # Check strict keywords to identify end.
                         if "except" in line:
                              in_pedigree_try = False
                              # exception block should be 12 spaces
                              clean = line.strip()
                              if "except Exception as e: pass" in clean: # One liner
                                   new_source.append("            except Exception as e: pass\n")
                              elif "except: pass" in clean:
                                   new_source.append("            except: pass\n")
                              else:
                                   new_source.append("            except: pass\n") # Force simple
                              modified = True
                              continue
                         
                         # BODY LINES -> Must be 16 spaces
                         # Clean and re-indent
                         clean = line.strip()
                         if clean:
                             new_line = "                " + clean + "\n"
                             if new_line != line:
                                 new_source.append(new_line)
                                 modified = True
                             else:
                                 new_source.append(line)
                         else:
                             new_source.append(line)
                    else:
                         new_source.append(line)
                
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Pedigree Body Fix to {filepath}")
        else:
            print(f"⚠️ No changes needed for {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_pedigree_body(nb)
