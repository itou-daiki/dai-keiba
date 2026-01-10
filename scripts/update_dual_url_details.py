import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def update_dual_url(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Hook into the main scraping block
                    # We look for where 'soup' is created from 'r.text' or similar.
                    if "soup = BeautifulSoup(r.text" in line:
                         new_source.append(line)
                         # Insert Pedigree Request Logic AFTER main soup creation
                         # But wait, we need to do this efficiently.
                         # Doing it sequentially is fine.
                         
                    elif "details['bms'] = ''" in line:
                         # This is initialization. We want to insert the logic where finding happens.
                         new_source.append(line)
                         
                    # Target a unique line inside get_horse_details, preferably early.
                    # "if '日付' in df.columns:" happens after df is cleaned.
                    # We can inject BEFORE this check.
                    elif "if '日付' in df.columns:" in line:
                        # Logic block for Pedigree
                        block = [
                           "        # --- PEDIGREE FETCH (Dual URL) ---\n",
                           "        try:\n",
                           "            # Only fetch if we are actually processing this horse\n",
                           "            ped_url = f\"https://db.netkeiba.com/horse/ped/{horse_id}/\"\n",
                           "            # Simple check to avoid hammer if needed, but we do it every time for now\n",
                           "            time.sleep(0.5) # Be polite\n",
                           "            r_ped = requests.get(ped_url, headers=headers)\n",
                           "            r_ped.encoding = 'EUC-JP'\n",
                           "            soup_ped = BeautifulSoup(r_ped.text, 'html.parser')\n",
                           "            blood_tbl = soup_ped.select_one('table.blood_table')\n",
                           "            if blood_tbl:\n",
                           "                tds = blood_tbl.find_all('td')\n",
                           "                # Flattened TDs: 0=Father, 1=Unknown(Mother?), but heuristic: 0 is Father\n",
                           "                if len(tds) > 0: details['father'] = tds[0].text.strip().split('\\n')[0]\n",
                           "                # Mother is tricky. Let's try to get 'bms' (Broodmare Sire) -> Mother's Father\n",
                           "                # If table is 5 generation:\n",
                           "                # 0: Father, 1: F-Father, 2: F-F-Father, 3: F-F-Mother\n",
                           "                # Mother is in the bottom half of the first split.\n",
                           "                # Table structure: tr1 has Father (rowspan 16), tr17 has Mother (rowspan 16)\n",
                           "                # If we use find_all('td', rowspan='...'):\n",
                           "                # Let's try finding the row for Mother.\n",
                           "                # Heuristic: The text in the cell with rowspan that appears 2nd in the 'Parents' column.\n",
                           "                # Simplified: Just grab Father for now as proof.\n",
                           "                pass\n",
                           "        except Exception as e: pass\n",
                           "        # ---------------------------------\n",
                           "\n"
                        ]
                        new_source.extend(block)
                        new_source.append(line)
                        modified = True
                        
                    elif "table = soup.select_one('table.db_h_race_results')" in line:
                         # Fallback/Old target - keep just in case or remove if conflict?
                         # Better remove old target to avoid double insertion if script runs twice (though modified flag handles it per run)
                         # We will use the 'if 日付' target above as primary.
                         new_source.append(line)
                    
                    else:
                        new_source.append(line)
                
                if modified:
                    cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Inserted Dual URL Logic into {filename}")
        else:
            print(f"⚠️ Insertion point not found in {filename}")

    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    update_dual_url('Colab_JRA_Details_v2.ipynb')
    update_dual_url('Colab_NAR_Details_v2.ipynb')
