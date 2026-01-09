import json
import os
import re

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def fix_broken_code(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                # We need to process line by line, but also look for the bad block logic
                # However, source is a list of strings (lines with \n).
                
                skip_block = False
                
                for line in cell['source']:
                    # 1. Remove Orphan Values (JRA: : cells[...], NAR: : '',)
                    # Regex for line starting with whitespace + : + something
                    if re.match(r'^\s*:\s*(cells|\||\'\')', line):
                        # Matches ": cells..." or ": ''"
                        print(f"  ✅ Removing orphan line in {filename}: {line.strip()}")
                        modified = True
                        continue
                    
                    # Also specific check for the NAR garbage ": ''," which might be appended to previous line or on its own line?
                    # In Step 191, line 345 was: '                '後3F': cells[11].text.strip() if len(cells) > 11 else '': '',\n'
                    # It's on the SAME LINE.
                    if "else '': ''," in line:
                        new_line = line.replace(": '',", ",") # Restore comma!
                        # Check if it results in valid python (trailing comma is okay)
                        # "else ''," is valid in list/dict
                        new_source.append(new_line)
                        modified = True
                        print(f"  ✅ Fixed inline garbage in {filename}")
                        continue
                        
                    # Also check if we simply created a line without comma previously
                    if "'後3F':" in line and not line.strip().endswith(','):
                         # Just append comma
                         new_line = line.rstrip() + ",\n"
                         new_source.append(new_line)
                         modified = True
                         print(f"  ✅ Restored missing comma in {filename}")
                         continue

                    # 2. Remove Broken Usage (JRA: horse_data[])
                    if "horse_data[]" in line:
                         # We need to skip this block (the corner parsing logic)
                         # Block starts here.
                         skip_block = True
                         modified = True
                         print(f"  ✅ Removing broken usage block in {filename}")
                         continue
                    
                    if skip_block:
                        # How to end skip?
                        # The block usually ends when we hit "race_data.append" or indentation change?
                        # Block was:
                        # corner_text = ...
                        # if corner_text...
                        #    ...
                        # race_data.append...
                        if "race_data.append" in line:
                            skip_block = False
                            # and we include this line
                            new_source.append(line)
                            continue
                        else:
                            # Still in usage block (formatting corner data)
                            continue

                    new_source.append(line)
                
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved fixed {filename}")
        else:
            print(f"⚠️ No fixes needed for {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    fix_broken_code('Colab_JRA_Basic_v2.ipynb')
    fix_broken_code('Colab_NAR_Basic_v2.ipynb')
