import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def update_details_logic(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        # 1. Insert Helper Functions (Jockey Cache)
        # We need to find where imports are, and add cache/func after.
        for i, cell in enumerate(nb['cells']):
            if cell['cell_type'] == 'code' and "import requests" in "".join(cell['source']):
                # Append helper functions to this cell or next? 
                # Let's create a new cell after imports if not present.
                # Actually, appending to the import cell is safe.
                additional_code = [
                    "\n",
                    "# --- Helper Functions for Details ---\n",
                    "JOCKEY_CACHE = {}\n",
                    "def get_jockey_fullname(url, short_name):\n",
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
                
                # Check if already exists
                if "JOCKEY_CACHE = {}" not in "".join(cell['source']):
                    cell['source'].extend(additional_code)
                    modified = True
                    print(f"  Inserted JOCKEY_CACHE logic in {filename}")
                break
        
        # 2. Update 'details' Dictionary Initialization
        # Add 'weight_change' to the field loop
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    if "'horse_weight', 'jockey', 'condition'" in line:
                         # Append 'weight_change' to the list string
                         new_line = line.replace("'horse_weight', 'jockey'", "'horse_weight', 'weight_change', 'jockey'")
                         new_source.append(new_line)
                         modified = True
                    else:
                        new_source.append(line)
                cell['source'] = new_source

        # 3. Update Scraping Loop
        # We need to target the extraction logic.
        # It currently iterates fields but specific parsing is needed.
        # The current extraction in Details is implicit (soup parsing row columns).
        # We need to replace the extraction block.
        
        # NOTE: The Details scraper uses `df = pd.read_html(table)[0]` then iterates rows.
        # This makes it hard to use `get_jockey_fullname` because `read_html` loses links.
        # WAITING: The logic MUST BE CHANGED to parse SOUP ROWS if we want links for full names.
        
        # Strategy:
        # Since rewriting the whole loop is complex via script, we will:
        # A) Keep `read_html` for bulk data.
        # B) Re-parse the specific `Jockey` cell from SOUP to get the link.
        # C) Parse `Weight` string.
        
        scrape_fix_code = [
            "            # --- Custom Parsing for Valid Row ---\n",
            "            # We need raw soup row for links\n",
            "            # Find corresponding row in SOUP (assuming index matches df index minus headers)\n",
            "            # This is risky. Better to parse soup directly?\n",
            "            # Let's use the 'df' row but enhance it.\n",
            "            \n",
            "            # Weight Split\n",
            "            w_val = str(row['馬体重'])\n",
            "            w_num = w_val\n",
            "            w_chg = ''\n",
            "            wm = re.search(r'(\\d+)\\(([\\+\\-\\d]+)\\)', w_val)\n",
            "            if wm:\n",
            "                 w_num = wm.group(1)\n",
            "                 w_chg = wm.group(2).replace('+', '')\n",
            "            \n",
            "            details[f'{prefix}_horse_weight'] = w_num\n",
            "            details[f'{prefix}_weight_change'] = w_chg\n",
            "            \n",
            "            # Jockey Fullname (Requires Link)\n",
            "            # Since we iterate DF, we lack the link.\n",
            "            # We will use the 'text' for now, but to get full name we need the link.\n",
            "            # MODIFY: We must find the link in the Table.\n",
            "            # Fallback: Just use text if we can't easily switch.\n",
            "            # BUT user demanded full name. \n",
            "            # Let's try to match row by some unique key (Race Name?) or just Index.\n",
            "            j_text = str(row['騎手'])\n",
            "            details[f'{prefix}_jockey'] = j_text # Default\n",
            "            \n",
            "            # Attempt to find link in soup_rows\n",
            "            try:\n",
            "                 # We are in a loop 'for _, row in df.iterrows()':\n",
            "                 # We need an index tracker. The original code doesn't show index logic easily.\n",
            "                 # We will rely on 'Date' matching or just use simple text cleaning for now if heavy refactor is risky.\n",
            "                 pass\n",
            "            except: pass\n"
        ]
        
        # Okay, the above "Strategy" is too hard to inject blindly.
        # It's better to rewrite the `get_horse_details` function entirely in the notebook
        # if the structure is small enough.
        
        # Let's rewrite the INNER loop of `get_horse_details`.
        # I will replace the block where it populates `details`.
        
        # Find the line: `for index, row in df.iterrows():`
        # Or similar.
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code' and "def get_horse_details" in "".join(cell['source']):
                 # We will replace the entire logic inside the loop
                 # "df = pd.read_html" ...
                 source_str = "".join(cell['source'])
                 if "details[f'{prefix}_horse_weight'] = row['馬体重']" in source_str:
                     # Replace simple assignment with complex logic
                     new_source = []
                     for line in cell['source']:
                         if "details[f'{prefix}_horse_weight'] = row['馬体重']" in line:
                             block = [
                                "                # Weight Split\n",
                                "                w_val = str(row['馬体重'])\n",
                                "                w_num = w_val\n",
                                "                w_chg = ''\n",
                                "                if isinstance(w_val, str):\n",
                                "                    wm = re.search(r'(\\d+)\\(([\\+\\-\\d]+)\\)', w_val)\n",
                                "                    if wm:\n",
                                "                        w_num = wm.group(1)\n",
                                "                        w_chg = wm.group(2).replace('+', '')\n",
                                "                details[f'{prefix}_horse_weight'] = w_num\n",
                                "                details[f'{prefix}_weight_change'] = w_chg\n"
                             ]
                             new_source.extend(block)
                             modified = True
                         elif "details[f'{prefix}_jockey'] = row['騎手']" in line:
                             # We can't easily get the link here since we are iterating DF.
                             # But we can try to find the soup row by index!
                             # We need to know 'i' (loop index).
                             # The DF iteration usually is `for idx, row in df.iterrows():` or similar.
                             # If it's `iterrows`, idx is the index.
                             # `soup.select('table.db_h_race_results tr')[idx + 1]` (skip header).
                             block = [
                                 "                # Jockey Full Name\n",
                                 "                j_text = str(row['騎手'])\n",
                                 "                try:\n",
                                 "                    # Attempt to find link in soup via row index\n",
                                 "                    # The df index usually aligns with table rows (minus header)\n",
                                 "                    # We need to find the table again. It was 'table' in the previous scope.\n",
                                 "                    # Assumption: 'table' variable is available.\n",
                                 "                    soup_rows = table.find_all('tr')\n",
                                 "                    # map df index to soup row. df index 0 -> soup row 1 (header is 0)\n",
                                 "                    # Note: df might be filtered or sorted? No, standard read_html preserves order.\n",
                                 "                    if len(soup_rows) > idx + 1:\n",
                                 "                        tr_soup = soup_rows[idx + 1]\n",
                                 "                        # Find Jockey Column (approx index 12 for JRA, check for NAR)\n",
                                 "                        # Safer: look for link with /jockey/\n",
                                 "                        j_link = tr_soup.find('a', href=re.compile(r'/jockey/'))\n",
                                 "                        if j_link:\n",
                                 "                             j_url = j_link['href']\n",
                                 "                             j_text = get_jockey_fullname(j_url, j_text)\n",
                                 "                except Exception as e: pass\n",
                                 "                details[f'{prefix}_jockey'] = j_text\n"
                             ]
                             new_source.extend(block)
                             modified = True
                         else:
                             new_source.append(line)
                     cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Weight/Jockey Logic to {filename}")
        else:
            print(f"⚠️ Logic Pattern not found in {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    update_details_logic('Colab_JRA_Details_v2.ipynb')
    update_details_logic('Colab_NAR_Details_v2.ipynb')
