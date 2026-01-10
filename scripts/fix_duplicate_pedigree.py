import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def remove_duplicate_pedigree(filepath):
    print(f"🔧 Fixing {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source = cell['source']
                
                # Find and remove the SECOND occurrence of the pedigree block
                # The duplicate starts with "            # --- PEDIGREE FETCH (Dual URL) ---\n"
                # and ends before "            # ---------------------------------\n"
                
                # Strategy: Find the pattern, mark first occurrence as "keep", remove second
                pedigree_start_marker = "            # --- PEDIGREE FETCH (Dual URL) ---\n"
                pedigree_end_marker = "            # ---------------------------------\n"
                
                first_start_idx = None
                second_start_idx = None
                
                for i, line in enumerate(source):
                    if pedigree_start_marker in line:
                        if first_start_idx is None:
                            first_start_idx = i
                        else:
                            second_start_idx = i
                            break
                
                if second_start_idx is not None:
                    # Find the end of the second block (the line ending with # ---)
                    second_end_idx = None
                    for j in range(second_start_idx, len(source)):
                        if pedigree_end_marker in source[j]:
                            second_end_idx = j
                            break
                    
                    if second_end_idx is not None:
                        # Remove lines from second_start_idx to second_end_idx (inclusive)
                        print(f"  📍 Removing duplicate pedigree block: lines {second_start_idx}-{second_end_idx}")
                        new_source = source[:second_start_idx] + source[second_end_idx+1:]
                        cell['source'] = new_source
                        modified = True
                    else:
                        print(f"  ⚠️ Could not find end of duplicate block in {filepath}")
                
                # Also fix variable shadowing: change inner loop 'i' to 'j'
                # Target: "            for i in range(1, 6):\n"
                new_source = []
                for line in cell['source']:
                    # Fix variable shadowing in column ordering loop
                    if "            for i in range(1, 6):" in line:
                        line = line.replace("for i in range(1, 6):", "for pi in range(1, 6):")
                        modified = True
                    if "                prefix = f'past_{i}'" in line:
                        line = line.replace("prefix = f'past_{i}'", "prefix = f'past_{pi}'")
                        modified = True
                    new_source.append(line)
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"✅ Fixed {filepath}")
        else:
            print(f"⚠️ No changes needed for {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        remove_duplicate_pedigree(nb)
