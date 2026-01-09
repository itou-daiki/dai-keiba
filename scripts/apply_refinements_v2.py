import json
import os
import re

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def apply_refinements_v2(filename, is_jra=True):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_text = "".join(cell['source'])
                
                # 1. REMOVE 'コーナー通過順' from ordered_columns
                # List removal is cleaner via string replacement of the item
                if "'コーナー通過順'" in source_text:
                    source_text = source_text.replace("'コーナー通過順', ", "")
                    source_text = source_text.replace(", 'コーナー通過順'", "")
                    source_text = source_text.replace("'コーナー通過順'", "")
                    modified = True
                    print(f"  ✅ Removed 'コーナー通過順' from ordered_columns in {filename}")

                # 2. REMOVE 'コーナー通過順' initialization in dict
                # Regex to find the line: 'コーナー通過順': ..., \n
                # Or my previous broken append: ... else '', 'コーナー通過順': '',
                # Let's just remove the key-value string if found.
                if "'コーナー通過順':" in source_text:
                    # Logic: Replace matching lines
                    lines = source_text.splitlines(keepends=True)
                    new_lines = []
                    for line in lines:
                        if "'コーナー通過順':" in line:
                             # If it's the simple key line: remove it
                             if line.strip().startswith("'コーナー通過順':"):
                                 continue
                             # If it's my broken append: '後3F': ... 'コーナー通過順': '',
                             if "'コーナー通過順': ''," in line:
                                 # Strip the appended part
                                 line = line.replace(" 'コーナー通過順': '',", "")
                                 line = line.replace("'コーナー通過順': '',", "")
                                 # Check if I left a trailing comma or something invalid?
                                 # If line was "... else '',", replacing the suffix just leaves "... else ''," which is fine.
                                 pass
                        
                        # Also check for my previous JRA Optimization Syntax Error
                        # Pattern: elif j_url:\n                    jockey_val = ...
                        # The error was `expected an indented block`.
                        # I should create a clean block for JRA.
                        if is_jra and "if j_url:" in line and "Optimization: Try title" not in source_text:
                             # Wait, if I already applied it, it's there.
                             # If I applied it badly, I need to detect the bad block.
                             pass
                        
                        new_lines.append(line)
                    source_text = "".join(new_lines)
                    modified = True

                # 3. FIX JRA OPTIMIZATION SYNTAX (If JRA)
                if is_jra and "Optimization: Try title attribute first" in source_text:
                    # The previous script appended lines naively.
                    # We want to replace the whole jockey scraping block with a clean version.
                    # Block start: # --- 騎手 (Fullname) ---
                    # Block end: # --- 厩舎/調教師 ---
                    # Let's find this block range.
                    pattern = r"(# --- 騎手 \(Fullname\) ---[\s\S]+?)(# --- 厩舎/調教師 ---)"
                    # New clean block logic
                    clean_block = r"""# --- 騎手 (Fullname) ---
            jockey_col = cells[6] if len(cells) > 6 else None
            jockey_val = ""
            if jockey_col:
                j_text = jockey_col.text.strip()
                j_link = jockey_col.find('a')
                j_url = j_link['href'] if j_link else None
                
                # Optimization: Try title attribute first
                if j_link and j_link.get('title'):
                    jockey_val = j_link.get('title')
                    if j_url: JOCKEY_CACHE[j_url] = jockey_val
                elif j_url:
                    jockey_val = get_jockey_fullname(j_url, j_text)
                else:
                    jockey_val = j_text

            """
                    match = re.search(pattern, source_text)
                    if match:
                        source_text = source_text.replace(match.group(1), clean_block)
                        modified = True
                        print("  ✅ Replaced/Fixed JRA Jockey Scraping Block")
                
                # 4. Final check for "Trainer Regex" and "Weight" (Safe to apply again if regex matches old, but if already new, skip)
                # Trainer
                if "re.search(r'^(.+?)(?:のプロフィール|の騎手成績|｜)', title)" in source_text:
                    source_text = source_text.replace(
                        "re.search(r'^(.+?)(?:のプロフィール|の騎手成績|｜)', title)",
                        "re.search(r'^(.+?)(?:のプロフィール|の騎手成績|の調教師成績|｜)', title)"
                    )
                    modified = True
                
                # Weight
                if "weight_change = m.group(2)" in source_text and "replace" not in source_text:
                     # This check is weak if "replace" appears elsewhere, but specific enough for this line?
                     # Better: look for the exact line
                     source_text = source_text.replace(
                         "weight_change = m.group(2)",
                         "weight_change = m.group(2).replace('+', '')"
                     )
                     modified = True
                
                cell['source'] = [s + "\n" for s in source_text.split('\n')][:-1] # Split adds empty string at end if trailing newline
                # Re-normalize newlines
                cell['source'] = []
                for l in source_text.splitlines(keepends=True):
                    cell['source'].append(l)

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved fixed {filename}")
        else:
            print(f"⚠️ No changes made to {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    apply_refinements_v2('Colab_JRA_Basic_v2.ipynb', is_jra=True)
    apply_refinements_v2('Colab_NAR_Basic_v2.ipynb', is_jra=False)
