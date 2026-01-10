import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_extraction_loop(filepath):
    print(f"🔧 Fixing Extraction Loop in {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Target Weight Line
                    if "details[f'{prefix}_horse_weight'] = str(getattr(row, '馬体重', ''))" in line:
                         # Replace with Logic
                         block = [
                            "                    # Weight Split\n",
                            "                    w_val = str(getattr(row, '馬体重', ''))\n",
                            "                    w_num = w_val\n",
                            "                    w_chg = ''\n",
                            "                    if isinstance(w_val, str):\n",
                            "                        wm = re.search(r'(\\d+)\\(([\\+\\-\\d]+)\\)', w_val)\n",
                            "                        if wm:\n",
                            "                            w_num = wm.group(1)\n",
                            "                            w_chg = wm.group(2).replace('+', '')\n",
                            "                    details[f'{prefix}_horse_weight'] = w_num\n",
                            "                    details[f'{prefix}_weight_change'] = w_chg\n"
                         ]
                         new_source.extend(block)
                         modified = True
                    
                    # Target Jockey Line
                    elif "details[f'{prefix}_jockey'] = str(getattr(row, '騎手', ''))" in line:
                         # Replace with Logic
                         # We need the link for full name. But here we only have 'row' (namedtuple).
                         # We can't get the link from 'row' if read_html stripped it.
                         # BUT, we can use the 'get_jockey_fullname' cache if we can scrape the link separately OR 
                         # we can try to guess/search?
                         # The USER requirement was "Full Name".
                         # If we don't have the link, we can't get the full name easily unless we search.
                         # Wait, my previous plan (`update_details_logic_v2`) tried to find the `tr` in soup by index.
                         # "soup_rows = table.find_all('tr')"
                         # "tr_soup = soup_rows[idx + 1]"
                         # We need 'i' (which is 1-based index from enumerate).
                         # So `soup_rows[i]` is likely the header (0) + i?
                         # enumerate(..., 1) means i starts at 1.
                         # If df has N rows. soup_rows has N+1 rows (header).
                         # so row 'i' corresponds to `soup_rows[i]`? Let's verify.
                         # i=1 (first data row). soup_rows[0] is header. soup_rows[1] is first data row.
                         # So yes, soup_rows[i] is correct.
                         
                         block = [
                             "                    # Jockey Full Name\n",
                             "                    j_text = str(getattr(row, '騎手', ''))\n",
                             "                    try:\n",
                             "                        # Recover link from soup\n",
                             "                        # We assume 'table' and 'i' are available in scope.\n",
                             "                        soup_rows = table.find_all('tr')\n",
                             "                        if len(soup_rows) > i:\n",
                             "                            tr_soup = soup_rows[i] # i is 1-based index matching row position?\n",
                             "                            # NO: enumerate is over df.itertuples().\n",
                             "                            # df is FILTERED? Lines 146-152: df = df.head(5).\n",
                             "                            # df is sorted and head(5).\n",
                             "                            # The 'table' soup has ALL rows. df only has 5.\n",
                             "                            # The index 'i' (1,2,3...) does NOT match 'table' rows if we filtered/sorted.\n",
                             "                            # CRITICAL ISSUE: We cannot map df row back to soup row easily by index after sort/filter.\n",
                             "                            \n",
                             "                            # SOLUTION: Search soup for matching date + race_name + jockey text?\n",
                             "                            # OR: Since we want FULL NAME, and we iterate only 5 rows...\n",
                             "                            # Maybe we should rely on the TEXT if it is already full?\n",
                             "                            # JRA text is usually abbrev? 'ルメール'. Full is 'C.ルメール'.\n",
                             "                            # The LINK has the ID.\n",
                             "                            \n",
                             "                            # Alternative: Re-scrape the row from SOUP based on fuzzy match?\n",
                             "                            pass\n",
                             "                    except: pass\n",
                             "                    details[f'{prefix}_jockey'] = j_text\n"
                         ]
                         # Wait, if I can't reliable get the link, I can't fulfill the request 100%.
                         # BUT, does the user really need "C.ルメール" vs "ルメール"?
                         # User said: "past run jockey name should be full name".
                         # In JRA, 'ルメール' IS the registered name often displayed. 
                         # However, for '武豊' vs '武' etc?
                         # Actually, `read_html` usually gives what's visible.
                         # The `get_jockey_fullname` logic was: fetch PROFILE page and get H1.
                         # That requires the link.
                         
                         # Let's try to find the row by DATE.
                         # Row has '日付'. Soup row has '日付'.
                         # `r_date = str(getattr(row, '日付', ''))`
                         # Iterate soup rows, find one with matching date text?
                         # Unique enough? Usually yes for a horse history (one race per day).
                         
                         block = [
                             "                    # Jockey Full Name & Link Recovery\n",
                             "                    j_text = str(getattr(row, '騎手', ''))\n",
                             "                    r_date = str(getattr(row, '日付', ''))\n",
                             "                    try:\n",
                             "                        # Find row in soup by Date match\n",
                             "                        # table is defined.\n",
                             "                        found_link = None\n",
                             "                        for tr in table.find_all('tr'):\n",
                             "                            if r_date in tr.text:\n",
                             "                                # Found match\n",
                             "                                links = tr.find_all('a')\n",
                             "                                for lk in links:\n",
                             "                                    if '/jockey/' in lk.get('href', ''):\n",
                             "                                        found_link = lk.get('href')\n",
                             "                                        break\n",
                             "                                if found_link: break\n",
                             "                        \n",
                             "                        if found_link:\n",
                             "                            j_text = get_jockey_fullname(found_link, j_text)\n",
                             "                    except: pass\n",
                             "                    details[f'{prefix}_jockey'] = j_text\n"
                         ]
                         new_source.extend(block)
                         modified = True
                         
                    else:
                        new_source.append(line)
                
                cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Fix to Extraction in {filepath}")
        else:
            print(f"⚠️ No changes needed for {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_extraction_loop(nb)
