import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_skip_logic(filepath):
    print(f"🔧 Fixing Skip Logic in {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Target the existing_ids accumulation logic
                    if "existing_ids = set(df_existing['race_id'] + '_' + df_existing['horse_id'])" in line:
                         # Replace with logic that checks data validity
                         block = [
                             "            # Re-scrape if data is missing (e.g. 'father' is empty)\n",
                             "            # If 'father' column exists, use it to filter completed rows\n",
                             "            if 'father' in df_existing.columns:\n",
                             "                # Robust check: father is not null and not empty string\n",
                             "                completed_df = df_existing[df_existing['father'].notna() & (df_existing['father'] != '')]\n",
                             "                existing_ids = set(completed_df['race_id'] + '_' + completed_df['horse_id'])\n",
                             "            else:\n",
                             "                # If column missing, assume all need scraping (or fallback to old logic?)\n",
                             "                # Better to clear existing_ids if we can't verify completeness\n",
                             "                existing_ids = set() # Force re-scrape if format is old\n",
                             "                # existing_ids = set(df_existing['race_id'] + '_' + df_existing['horse_id']) # Old Logic\n"
                         ]
                         new_source.extend(block)
                         modified = True
                    else:
                        new_source.append(line)
                
                if len(new_source) != len(cell['source']):
                    cell['source'] = new_source
                    modified = True

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Smart Skip Logic to {filepath}")
        else:
            print(f"⚠️ Skip Logic line not found in {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_skip_logic(nb)
