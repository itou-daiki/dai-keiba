import json
import os
import re

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def fix_pedigree_logic_rewrite(filepath):
    print(f"🔧 Rewriting Pedigree Logic in {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        # We need to find the cell with "PEDIGREE FETCH" and replace the logic inside the try block.
        # It's fragile to replace line-by-line using previous methods because indentation is mixed.
        # We will detect the START of the block and the END (except), and replace CONTENT.
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_str = "".join(cell['source'])
                if "PEDIGREE FETCH" in source_str:
                    new_source = []
                    in_pedigree_block = False
                    
                    cleaned_pedigree_code = [
                        "                # --- PEDIGREE FETCH (Dual URL) ---\n", 
                        "                try:\n",
                        "                    ped_url = f\"https://db.netkeiba.com/horse/ped/{horse_id}/\"\n",
                        "                    time.sleep(0.5)\n",
                        "                    r_ped = requests.get(ped_url, headers=headers)\n",
                        "                    r_ped.encoding = 'EUC-JP'\n",
                        "                    soup_ped = BeautifulSoup(r_ped.text, 'html.parser')\n",
                        "                    blood_tbl = soup_ped.select_one('table.blood_table')\n",
                        "                    if blood_tbl:\n",
                        "                         trs = blood_tbl.find_all('tr')\n",
                        "                         # Father: Row 0, Col 0\n",
                        "                         if len(trs) > 0:\n",
                        "                             tds0 = trs[0].find_all('td')\n",
                        "                             if len(tds0) > 0: details['father'] = tds0[0].text.strip().split('\\n')[0]\n",
                        "                         \n",
                        "                         # Mother & BMS: Middle Row (Row 16 for 32 rows)\n",
                        "                         # Calculate mid point\n",
                        "                         mid_idx = int(len(trs) / 2)\n",
                        "                         if mid_idx > 0 and len(trs) > mid_idx:\n",
                        "                             tds_m = trs[mid_idx].find_all('td')\n",
                        "                             if len(tds_m) > 0:\n",
                        "                                 details['mother'] = tds_m[0].text.strip().split('\\n')[0]\n",
                        "                             if len(tds_m) > 1:\n",
                        "                                 details['bms'] = tds_m[1].text.strip().split('\\n')[0]\n",
                        "                except Exception as e: pass\n"
                    ]
                    
                    # NOTE: We assume indentation of 16 spaces for try body.
                    # The outer block (try) should be 12 spaces if inside 'if table:'?
                    # Wait, our previous fix established:
                    # '            try:' (12 spaces)
                    
                    cleaned_pedigree_code = [
                        "            # --- PEDIGREE FETCH (Dual URL) ---\n",
                        "            try:\n",
                        "                ped_url = f\"https://db.netkeiba.com/horse/ped/{horse_id}/\"\n",
                        "                time.sleep(0.5)\n",
                        "                r_ped = requests.get(ped_url, headers=headers)\n",
                        "                r_ped.encoding = 'EUC-JP'\n",
                        "                soup_ped = BeautifulSoup(r_ped.text, 'html.parser')\n",
                        "                blood_tbl = soup_ped.select_one('table.blood_table')\n",
                        "                if blood_tbl:\n",
                        "                    trs = blood_tbl.find_all('tr')\n",
                        "                    if len(trs) > 0:\n",
                        "                        tds0 = trs[0].find_all('td')\n",
                        "                        if len(tds0) > 0: details['father'] = tds0[0].text.strip().split('\\n')[0]\n",
                        "                    \n",
                        "                    mid_idx = int(len(trs) / 2)\n",
                        "                    if mid_idx > 0 and len(trs) > mid_idx:\n",
                        "                        tds_m = trs[mid_idx].find_all('td')\n",
                        "                        if len(tds_m) > 0:\n",
                        "                             details['mother'] = tds_m[0].text.strip().split('\\n')[0]\n",
                        "                        if len(tds_m) > 1:\n",
                        "                             details['bms'] = tds_m[1].text.strip().split('\\n')[0]\n",
                        "            except: pass\n"
                    ]

                    skip_mode = False
                    
                    for line in cell['source']:
                        if "# --- PEDIGREE FETCH" in line:
                            skip_mode = True
                            # Extend with new logic
                            new_source.extend(cleaned_pedigree_code)
                        
                        if skip_mode:
                            # We verify if we are out of the block
                            # The end of block is identified by... what?
                            # 'except' line.
                            if "except" in line and ("pass" in line or "Exception" in line):
                                skip_mode = False
                                # Do NOT append this line, because cleaned_pedigree_code included the except block.
                                continue
                            
                            # If we see `if '日付' in df.columns:` that means we went too far?
                            # No, pedigree is usually before.
                            
                            # Just skip lines
                            pass
                        else:
                            new_source.append(line)
                            
                    cell['source'] = new_source
                    modified = True
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Pedigree Rewrite to {filepath}")
        else:
            print(f"⚠️ Pedigree Block not found in {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        fix_pedigree_logic_rewrite(nb)
