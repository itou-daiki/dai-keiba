import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def robust_fix(filepath):
    print(f"🔧 Robust Fix for {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    clean = line.strip()
                    
                    # Target specific lines and FORCE correct indent level
                    if clean.startswith("# --- PEDIGREE FETCH"):
                        new_source.append("            # --- PEDIGREE FETCH (Dual URL) ---\n") # 12 spaces
                    elif clean.startswith("try:") and "PEDIGREE" not in line and "Exception" not in line: # Dangerous?
                         # Context check? 
                         # Let's assume the try inside the pedigree block is unique or we match sequence.
                         # Instead, match by content we know is in pedigree block
                         pass 
                    
                    # Better: If we see known pedigree lines, output them with correct indent.
                    
                    if "ped_url =" in clean and "https://db.netkeiba.com/horse/ped/" in clean:
                         new_source.append("                ped_url = f\"https://db.netkeiba.com/horse/ped/{horse_id}/\"\n") # 16 spaces
                    elif "time.sleep(0.5)" in clean and "try" not in clean: # 16 spaces
                         # Only if inside pedigree (check context or assume unique line in this cell?)
                         # This line appears in helper too?
                         # Helper loop uses 8 spaces. This uses 16.
                         # We can't blindly replace.
                         new_source.append(line) 
                         
                    elif "r_ped =" in clean:
                         new_source.append("                r_ped = requests.get(ped_url, headers=headers)\n") # 16
                    elif "r_ped.encoding =" in clean:
                         new_source.append("                r_ped.encoding = 'EUC-JP'\n") # 16
                    elif "soup_ped =" in clean:
                         new_source.append("                soup_ped = BeautifulSoup(r_ped.text, 'html.parser')\n") # 16
                    elif "blood_tbl =" in clean:
                         new_source.append("                blood_tbl = soup_ped.select_one('table.blood_table')\n") # 16
                    elif clean.startswith("if blood_tbl:"):
                         new_source.append("                if blood_tbl:\n") # 16
                    elif "tds = blood_tbl.find_all('td')" in clean:
                         new_source.append("                    tds = blood_tbl.find_all('td')\n") # 20
                    elif "if len(tds) > 0" in clean:
                         new_source.append("                    if len(tds) > 0: details['father'] = tds[0].text.strip().split('\\n')[0]\n") # 20
                    elif "pass" == clean and "except" not in line:
                         # 20 spaces?
                         new_source.append("                    pass\n")
                    else:
                         new_source.append(line)
                         
                if len(new_source) == len(cell['source']):
                     # Simple check if meaningful change
                     if new_source != cell['source']:
                         cell['source'] = new_source
                         modified = True
                else: 
                     cell['source'] = new_source
                     modified = True

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Robust Fix to {filepath}")
        else:
            print(f"⚠️ No changes needed for {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        robust_fix(nb)
