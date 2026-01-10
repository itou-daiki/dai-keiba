import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

def robust_date_logic(line):
    # Original: df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
    # New: df['date_obj'] = pd.to_datetime(df['日付'].astype(str).str.replace('.', '/'), errors='coerce')
    # We remove 'format' to let pandas guess after normalizing separators.
    if "df['date_obj'] = pd.to_datetime(df['日付']" in line:
        return "                df['date_obj'] = pd.to_datetime(df['日付'].astype(str).str.replace('.', '/'), errors='coerce')"
    return line

def fix_details_date(filename):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                cell_modified = False
                for line in cell['source']:
                    stripped = line.strip()
                    if "pd.to_datetime(df['日付']" in stripped and "format='%Y/%m/%d'" in stripped:
                         # Replace with robust logic
                         new_line = line.replace("format='%Y/%m/%d'", "").replace("df['日付']", "df['日付'].astype(str).str.replace('.', '/')")
                         # Remove double replace if needed, but the simple replacement above works for the targeted line
                         # Let's use the explicit string from function for clarity
                         indent = line[:line.find("df")]
                         new_line = indent + "df['date_obj'] = pd.to_datetime(df['日付'].astype(str).str.replace('.', '/'), errors='coerce')\n"
                         new_source.append(new_line)
                         cell_modified = True
                         modified = True
                    else:
                        new_source.append(line)
                
                if cell_modified:
                    cell['source'] = new_source

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Robust Date Parsing to {filename}")
        else:
            print(f"⚠️ No date parsing logic found/changed in {filename}")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    fix_details_date('Colab_JRA_Details_v2.ipynb')
    fix_details_date('Colab_NAR_Details_v2.ipynb')
