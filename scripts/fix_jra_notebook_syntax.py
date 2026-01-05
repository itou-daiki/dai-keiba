import json
import os

NB_PATH = 'notebooks/JRA_Scraper.ipynb'

def fix_notebook_syntax():
    if not os.path.exists(NB_PATH):
        print("Notebook not found.")
        return

    with open(NB_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    target_cell = None
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])
            if "def fill_missing_past_data_notebook():" in source and "All pedigree data present" in source:
                target_cell = cell
                break
    
    if not target_cell:
        print("Target cell not found.")
        return

    # Filter out the orphaned else block
    new_source = []
    
    # We want to remove the specific else block at the end that causes error
    # It looks like:
    #     else:
    #         print('All pedigree data present.')
    
    skip_next = False
    
    # Iterate with index to look ahead
    lines = target_cell['source']
    for i in range(len(lines)):
        line = lines[i]
        
        # Identify the specific else (Context: It follows metadata block)
        # But easier: just find the lines exactly and remove them if they appear AFTER metadata logic?
        # The user snippet shows it is at the very end (before function call?)
        
        # Check against the specific content causing error
        # Note: indentation might vary in list (spaces vs \t or implicit in previous line)
        # But usually lines are "    else:\n", "        print('All pedigree data present.')\n"
        
        if "else:" in line and "print('All pedigree data present.')" in lines[i+1]:
             # Check if this else is preceded by Metadata block? 
             # Warning: We don't want to remove valid else blocks if any.
             # But here, we know the "Pedigree" else is the one orphaned.
             # We can just check line content.
             print(f"Removing orphaned else block at line {i}")
             # We skip this line and the next line
             # We need to skip only if we are sure it's orphaned.
             # The error confirms it IS orphaned.
             
             # Actually, simpler loop:
             pass
             
    # Robust approach: Build new list, skipping the specific sequence
    i = 0
    while i < len(lines):
        line = lines[i]
        next_line = lines[i+1] if i+1 < len(lines) else ""
        
        # Clean stripped content for check
        if "else:" in line.strip() and "print('All pedigree data present.')" in next_line:
            print(f"Found orphaned block at index {i}. Removing.")
            i += 2 # Skip both
        else:
            new_source.append(line)
            i += 1

    target_cell['source'] = new_source
    
    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=4, ensure_ascii=False)
        
    print(f"Fixed syntax in {NB_PATH}.")

if __name__ == "__main__":
    fix_notebook_syntax()
