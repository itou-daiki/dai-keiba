import json
import os
import re

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def final_fix_jra(filename='Colab_JRA_Basic_v2.ipynb'):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_text = "".join(cell['source'])
                
                # Check if this cell contains the scraping function
                if "def scrape_race_basic" in source_text:
                    
                    # 1. Fix Regex
                    # Old: m = re.search(r'^([^|]+)のプロフィール', title)
                    # New: m = re.search(r'^(.+?)(?:のプロフィール|の騎手成績|の調教師成績|｜)', title)
                    if "re.search(r'^([^|]+)のプロフィール', title)" in source_text:
                        source_text = source_text.replace(
                            "re.search(r'^([^|]+)のプロフィール', title)",
                            "re.search(r'^(.+?)(?:のプロフィール|の騎手成績|の調教師成績|｜)', title)"
                        )
                        modified = True
                        print("  ✅ Fixed Regex")
                        
                    # 2. Fix Jockey Usage
                    # Old: '騎手': cells[6].text.strip() if len(cells) > 6 else '',
                    # New: '騎手': jockey_val,
                    if "'騎手': cells[6].text.strip() if len(cells) > 6 else ''," in source_text:
                        source_text = source_text.replace(
                            "'騎手': cells[6].text.strip() if len(cells) > 6 else '',",
                            "'騎手': jockey_val,"
                        )
                        modified = True
                        print("  ✅ Fixed Jockey Usage")
                    
                    # 3. Fix Weight Usage
                    # Old: '馬体重(増減)': cells[14].text.strip() if len(cells) > 14 else '',
                    # New: '馬体重': weight_val, '増減': weight_change,
                    if "'馬体重(増減)': cells[14].text.strip() if len(cells) > 14 else ''," in source_text:
                         source_text = source_text.replace(
                            "'馬体重(増減)': cells[14].text.strip() if len(cells) > 14 else '',",
                            "'馬体重': weight_val,\n                '増減': weight_change,"
                        )
                         modified = True
                         print("  ✅ Fixed Weight Usage (Split)")

                    # 4. Fix Columns List (Removal of 'コーナー通過順' and Splitting Weight)
                    # We look for the specific block string because it spans newlines usually.
                    # But replacing standard parts is safer.
                    
                    # Remove 'コーナー通過順'
                     # 'コーナー通過順', 
                    if "'コーナー通過順', " in source_text:
                        source_text = source_text.replace("'コーナー通過順', ", "")
                        modified = True
                        print("  ✅ Removed 'コーナー通過順' from list")
                    
                    # Replace '馬体重(増減)' with '馬体重', '増減'
                    if "'馬体重(増減)'" in source_text:
                        source_text = source_text.replace("'馬体重(増減)'", "'馬体重', '増減'")
                        modified = True
                        print("  ✅ Replaced '馬体重(増減)' with split columns")
                    
                    # 5. Fix Dict Initialization for 'コーナー通過順'
                    # Old: 'コーナー通過順': cells[12].text.strip() if len(cells) > 12 else '',
                    # New: (Removed from dict if we want clean, OR just remove from ordered_columns is enough but verifying script checks dict keys? NO, verification checks scrape result columns)
                    # BUT I previously added code that USES horse_data['コーナー通過順'].
                    #   corner_text = horse_data['コーナー通過順']
                    # Use regex to replace the usage FIRST, creating corner_text from cells.
                    
                    # Fix Usage:
                    # Old: corner_text = horse_data['コーナー通過順']
                    # New: corner_text = cells[12].text.strip() if len(cells) > 12 else ''
                    if "corner_text = horse_data['コーナー通過順']" in source_text:
                        source_text = source_text.replace(
                            "corner_text = horse_data['コーナー通過順']",
                            "corner_text = cells[12].text.strip() if len(cells) > 12 else ''"
                        )
                        modified = True
                        print("  ✅ Fixed corner_text extraction usage")
                    
                    # Remove from Dict:
                    if "'コーナー通過順':" in source_text:
                         # Regex to remove lines containing this key
                         source_text = re.sub(r"\s*'コーナー通過順':.+,\n", "", source_text)
                         modified = True
                         print("  ✅ Removed 'コーナー通過順' from dict")
                
                # Update cell source
                cell['source'] = []
                for l in source_text.splitlines(keepends=True):
                    cell['source'].append(l)

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved FINAL FIX JRA {filename}")
        else:
            print(f"⚠️ No changes made to {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    final_fix_jra()
