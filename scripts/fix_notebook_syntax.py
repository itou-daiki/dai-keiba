
import json
import os

def fix_notebook_syntax():
    nb_path = 'notebooks/JRA_Scraper.ipynb'
    if not os.path.exists(nb_path):
        print(f"Notebook {nb_path} not found.")
        return

    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    fixed = False
    
    # We are looking for the cell with 'clean_id_str' that has the weird escaping
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            new_source = []
            changed_cell = False
            for line in cell['source']:
                # Detect the corrupted line
                if "def clean_id_str(x):" in line and "\\n" in line:
                    print(f"Found corrupted line: {line[:50]}...")
                    # Split by the literal escaped ' \n ' pattern
                    # The line is likely: "df = ... \n    def clean_id_str..."
                    # We simply split by '\\n' (represented as \n in the loaded string if it was \\n in file?)
                    # Wait, if I see it as `\\n` in the file view, it means it's literal backslash+n in the string.
                    # so split by '\n' might not work if it's actually `\` then `n`.
                    # But Python's json.load handles standard escapes.
                    # If I wrote `\\n` in the previous script, it put a literal backslash and n.
                    # So in the string it is `\n` (two chars).
                    
                    # Fix: replace literal '\n' sequence with actual newline char, then split
                    # Actually, better to just completely replace the known corrupted block with the clean block list.
                    
                    # Identifiable start
                    if line.startswith("    df = pd.read_csv(csv_path, low_memory=False"):
                         # Clean known good version
                         clean_lines = [
                             "    df = pd.read_csv(csv_path, low_memory=False, dtype={'race_id': str, 'horse_id': str})\n",
                             "    def clean_id_str(x):\n",
                             "        if pd.isna(x) or x == '': return None\n",
                             "        s = str(x)\n",
                             "        if s.endswith('.0'): return s[:-2]\n",
                             "        return s\n",
                             "    if 'race_id' in df.columns:\n",
                             "        df['race_id'] = df['race_id'].apply(clean_id_str)\n",
                             "    if 'horse_id' in df.columns:\n",
                             "        df['horse_id'] = df['horse_id'].apply(clean_id_str)\n"
                         ]
                         new_source.extend(clean_lines)
                         changed_cell = True
                         fixed = True
                    else:
                        # Fallback: splitting
                        parts = line.split('\\n') 
                        # if it was \\n in json, json.load makes it `\n` if it was escaped?
                        # No, if I wrote `\\n`, json wrote `\\n`. json.load reads `\n` (literal backslash n).
                        if len(parts) > 1:
                            for idx, part in enumerate(parts):
                                s = part
                                if idx < len(parts) - 1:
                                    s += '\n'
                                new_source.append(s)
                            changed_cell = True
                            fixed = True
                        else:
                             new_source.append(line)
                
                # Also check the other occurrence (jra_scrape_execution)
                elif "clean_id_s" in line and "\\n" in line:
                    print(f"Found corrupted line (execution): {line[:50]}...")
                    parts = line.split('\\n')
                    if len(parts) > 1:
                        for idx, part in enumerate(parts):
                            s = part
                            if idx < len(parts) - 1:
                                s += '\n'
                            new_source.append(s)
                        changed_cell = True
                        fixed = True
                    else:
                         new_source.append(line)
                else:
                    new_source.append(line)
            
            if changed_cell:
                cell['source'] = new_source

    if fixed:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=4, ensure_ascii=False)
        print("Notebook syntax fixed.")
    else:
        print("No corrupted lines found to fix.")

if __name__ == "__main__":
    fix_notebook_syntax()
