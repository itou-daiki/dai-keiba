import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_indent(filepath):
    print(f"🔧 Fixing {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # The error reported "unexpected indent" at "if '日付' in df.columns:"
                    # This implies the previous line (Dual URL block) might have left an indent open OR the injected line itself is double indented.
                    # Actually, the previous script APPENDED the "if '日付'..." line to the NEW block,
                    # effectively duplicating it? 
                    # Let's check the source view result first.
                    # The error says "if '日付' in df.columns:" is the problem.
                    # If I look at the view_file, I might see "if '日付'" is duplicated or indented wrong.
                    
                    # Heuristic: If line matches the target and has > 12 spaces, dedent.
                    # Standard indent in this function seems to be 12 (3 tabs) or 16?
                    # Let's just strip and re-apply uniform indent based on PREVIOUS line? No.
                    
                    # Wait, the previous script `update_dual_url_details.py` did:
                    # new_source.append(line) -> Original line
                    # But BEFORE that, it extended a block.
                    # "new_source.extend(block)"
                    # "new_source.append(line)"
                    # So the original line was appended AFTER the block.
                    # EXCEPT: The block itself contained matched logic?
                    
                    # Fix: Just ensure "if '日付' in df.columns:" is aligned with "df.columns = ..."
                    # The "df.columns =" line has 12 spaces usually.
                    
                    if "if '日付' in df.columns:" in line:
                         # Normalize to 12 spaces
                         clean = line.strip()
                         new_line = "            " + clean + "\n"
                         if new_line != line:
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
            print(f"💾 Fixed indent in {filepath}")
        else:
            print(f"⚠️ No changes needed for {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_indent(nb)
