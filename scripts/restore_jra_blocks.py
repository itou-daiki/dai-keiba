import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def restore_jra_blocks(filename='Colab_JRA_Basic_v2.ipynb'):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        # New Blocks to Insert
        JOCKEY_BLOCK = [
            "            # --- 騎手 (Fullname) ---",
            "            jockey_col = cells[6] if len(cells) > 6 else None",
            "            jockey_val = \"\"",
            "            if jockey_col:",
            "                j_text = jockey_col.text.strip()",
            "                j_link = jockey_col.find('a')",
            "                j_url = j_link['href'] if j_link else None",
            "                ",
            "                # Optimization: Try title attribute first",
            "                if j_link and j_link.get('title'):",
            "                    jockey_val = j_link.get('title')",
            "                    if j_url: JOCKEY_CACHE[j_url] = jockey_val",
            "                elif j_url:",
            "                    jockey_val = get_jockey_fullname(j_url, j_text)",
            "                else:",
            "                    jockey_val = j_text",
            "            "
        ]
        
        WEIGHT_BLOCK = [
            "            # --- 馬体重 (Split) ---",
            "            weight_col = cells[14] if len(cells) > 14 else None",
            "            weight_val = \"\"",
            "            weight_change = \"\"",
            "            if weight_col:",
            "                w_text = weight_col.text.strip()",
            "                m = re.search(r'(\d+)\(([\+\-\d]+)\)', w_text)",
            "                if m:",
            "                    weight_val = m.group(1)",
            "                    weight_change = m.group(2).replace('+', '')",
            "                else:",
            "                    weight_val = w_text",
            "            "
        ]

        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_lines = [l.rstrip('\n') for l in cell['source']]
                new_source = []
                
                # Check if this is the scraping function cell
                if "def scrape_race_basic" not in "".join(source_lines):
                    continue
                
                # Logic: iterate and insert
                # Flag to check if we already have the blocks (to avoid double insertion if I misdiagnosed)
                has_jockey = any("jockey_col =" in l for l in source_lines)
                has_weight = any("weight_col =" in l for l in source_lines)
                
                it = iter(source_lines)
                for line in it:
                    new_source.append(line)
                    
                    # Insert Jockey Block after "if len(cells) < 10: ... continue"
                    # But finding "continue" is hard if indented.
                    # Look for stable_col init line? No, jockey should be BEFORE stable.
                    # Look for "if len(cells) < 10:"
                    if "if len(cells) < 10:" in line:
                         # Consume the next line which should be "continue"
                         try:
                             next_line = next(it)
                             new_source.append(next_line)
                             
                             if not has_jockey:
                                 new_source.extend(JOCKEY_BLOCK)
                                 print("  ✅ Inserted Jockey Block")
                                 modified = True
                         except StopIteration:
                             pass
                    
                    # Insert Weight Block: After Stable Block
                    # Stable block ends when `trainer_val` is assigned?
                    # Or before `horse_data = {`
                    if "# 基本情報を辞書で構築" in line or "horse_data = {" in line:
                        # Insert BEFORE this line.
                        # We just appended `line` (which is horse_data start).
                        # So we need to insert validly.
                        # Pop the last line, insert block, then push line back.
                        last = new_source.pop()
                        
                        if not has_weight:
                            new_source.extend(WEIGHT_BLOCK)
                            print("  ✅ Inserted Weight Block")
                            modified = True
                        
                        new_source.append(last)

                if modified:
                    # Restore newlines
                    cell['source'] = [s + "\n" for s in new_source]
                    # Fix any trailing \n issue or double \n if needed?
                    # JSON usually expects \n at end of strings.
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved RESTORED JRA {filename}")
        else:
            print(f"⚠️ No changes made to {filename} (Blocks might be present?)")
            
    except Exception as e:
        print(f"❌ Error restoring {filename}: {e}")

if __name__ == "__main__":
    restore_jra_blocks()
