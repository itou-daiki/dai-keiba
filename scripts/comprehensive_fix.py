"""
Comprehensive fix for Details notebooks.
This script addresses the variable shadowing issue in the column ordering loop.
"""
import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def comprehensive_fix(filepath):
    print(f"🔧 Comprehensive fix for {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                in_column_ordering_block = False
                
                for line in cell['source']:
                    # Detect start of column ordering block
                    # This is inside run_details_scraping, after df_chunk = pd.DataFrame(buffer)
                    # The problematic loop: "            for i in range(1, 6):\n"
                    # This is at 12 spaces indentation (inside if block, inside for loop, inside function)
                    
                    # Fix: Rename the column ordering loop variable from 'i' to 'col_i'
                    if "            for i in range(1, 6):" in line:
                        # Check if this is in the main scraping function (not get_horse_details)
                        # The get_horse_details function is in a different cell and uses different indentation
                        line = line.replace("for i in range(1, 6):", "for col_i in range(1, 6):")
                        in_column_ordering_block = True
                        modified = True
                        print(f"  📍 Renamed loop variable 'i' to 'col_i' in column ordering")
                    
                    # Also need to update the prefix line that follows
                    if in_column_ordering_block and "                prefix = f'past_{i}'" in line:
                        line = line.replace("prefix = f'past_{i}'", "prefix = f'past_{col_i}'")
                        in_column_ordering_block = False  # Reset flag after fixing
                        print(f"  📍 Updated prefix to use 'col_i'")
                    
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
        comprehensive_fix(nb)
