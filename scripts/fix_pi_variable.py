import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_pi_to_i(filepath):
    print(f"🔧 Fixing {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Revert incorrectly renamed variable back to 'i'
                    if "prefix = f'past_{pi}'" in line:
                        line = line.replace("prefix = f'past_{pi}'", "prefix = f'past_{i}'")
                        modified = True
                        print(f"  📍 Reverted prefix = f'past_{{pi}}' to f'past_{{i}}'")
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
        fix_pi_to_i(nb)
