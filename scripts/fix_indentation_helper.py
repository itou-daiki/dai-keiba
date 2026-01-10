import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_helper_function(filepath):
    print(f"🔧 Fixing Helper in {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                # Check if this is the helper cell (contains get_jockey_fullname)
                source_str = "".join(cell['source'])
                if "def get_jockey_fullname" in source_str:
                    # Logic: Rewrite the helper cell content entirely to ensure clean indent.
                    # We can't easily parse line-by-line because of mixed state.
                    # We will replace the KNOWN lines with CLEAN lines.
                    
                    for line in cell['source']:
                        # Checking lines of helper function
                        clean_line = line.lstrip()
                        # If it matches helper logic, apply fixed indent.
                        if "if not url:" in line:
                            new_source.append("    if not url: return short_name\n")
                        elif "if url in JOCKEY_CACHE:" in line:
                            new_source.append("    if url in JOCKEY_CACHE: return JOCKEY_CACHE[url]\n")
                        elif "time.sleep(0.5)" in line and "def" not in line: # helper internal
                             # The indentation depth here is inside try (8 spaces) or function (4)?
                             # `def get_jockey_fullname` -> 0 indent if cell level.
                             # `try:` -> 4 indent
                             # `time.sleep` -> 8 indent
                             
                             if "try:" in cell['source']: # complex check
                                 # Let's assume standard python structure:
                                 # def ...
                                 #     try:
                                 #         time...
                                 pass 
                        
                        else:
                             # Just pass through? No, if the error is unindent mismatch.
                             pass
                    
                    # BETTER STRATEGY: Replace the specific BAD lines found in the error report?
                    # Error: `Line 26: if not url.startswith('http'):`
                    # `                if not url.startswith('http'):\n` (16 spaces?)
                    # In my injection script `update_details_logic_v2.py`, I used:
                    # "        if not url.startswith('http'):\n", (8 spaces)
                    
                    # BUT `def get_jockey_fullname` was at 0 spaces?
                    # "JOCKEY_CACHE = {}\n",
                    # "def get_jockey_fullname(url, short_name):\n",
                    # "    if not url: return short_name\n",
                    # ...
                    # "    try:\n",
                    # "        time.sleep(0.5)\n",
                    # "        if not url.startswith('http'):\n", (8 spaces)
                    
                    # The error `unindent does not match` usually means line 26 has DIFFERENT indentation than expected (e.g. 7 spaces or 9 spaces).
                    # Or maybe tabs.
                    
                    # Let's just blindly FORCE clean indentation for the helper block.
                    # We will reconstruct the function string.
                    
                    pass 
                
                # Re-do: Just read the cell, identify the helper function lines, and replace them with a correct Block.
                
                code_lines = cell['source']
                final_lines = []
                in_helper = False
                
                for line in code_lines:
                    if "def get_jockey_fullname" in line:
                        in_helper = True
                        final_lines.append("def get_jockey_fullname(url, short_name):\n")
                        # Add the rest of the body correct here
                        body = [
                            "    if not url: return short_name\n",
                            "    if url in JOCKEY_CACHE: return JOCKEY_CACHE[url]\n",
                            "    try:\n",
                            "        time.sleep(0.5)\n",
                            "        if not url.startswith('http'):\n",
                            "            url = 'https://db.netkeiba.com' + url\n",
                            "        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})\n",
                            "        r.encoding = 'EUC-JP'\n",
                            "        s = BeautifulSoup(r.text, 'html.parser')\n",
                            "        h1 = s.find('h1')\n",
                            "        if h1:\n",
                            "             title = h1.text.split()[0].strip()\n",
                            "             clean = re.sub(r'(の調教師成績|の騎手成績|のプロフィール|｜).*', '', title).strip()\n",
                            "             JOCKEY_CACHE[url] = clean\n",
                            "             return clean\n",
                            "    except:\n",
                            "        pass\n",
                            "    return short_name\n"
                        ]
                        final_lines.extend(body)
                        # Skip original lines until we exit helper
                        # How to know we exit? The helper was appended at the end of cell usually.
                        # Or until next def/class or end of cell.
                        # Since I injected it, I know the content.
                        
                    elif in_helper:
                        # Skip lines that look like the old helper body
                        if "return short_name" in line and "if not url" not in line: 
                             # This is the last line of helper usually
                             in_helper = False
                        # We skip everything else
                        pass
                    else:
                        final_lines.append(line)
                
                if len(final_lines) != len(code_lines):
                    cell['source'] = final_lines
                    modified = True

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Fixed Helper in {filepath}")
        else:
            print(f"⚠️ Helper logic not updated in {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_helper_function(nb)
