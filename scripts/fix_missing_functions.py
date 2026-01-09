import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

JOCKEY_HELPER_CODE = """
# 騎手名キャッシュ
JOCKEY_CACHE = {}

def get_jockey_fullname(url, default_name):
    \"\"\"騎手ページのリンクからフルネームを取得\"\"\"
    if not url: return default_name
    if url in JOCKEY_CACHE: return JOCKEY_CACHE[url]
    
    try:
        time.sleep(0.3)
        headers = {'User-Agent': 'Mozilla/5.0'}
        if url.startswith('/'): url = f"https://race.netkeiba.com{url}"
        
        r = requests.get(url, headers=headers, timeout=5)
        r.encoding = 'EUC-JP'
        s = BeautifulSoup(r.text, 'html.parser')
        
        title = s.title.text if s.title else ""
        m = re.search(r'^(.+?)(?:のプロフィール|の騎手成績|の調教師成績|｜)', title)
        if m:
            fullname = m.group(1).strip()
            JOCKEY_CACHE[url] = fullname
            return fullname
            
        h1 = s.find('h1')
        if h1:
             txt = h1.text.strip().split()[0]
             JOCKEY_CACHE[url] = txt
             return txt
    except:
        pass
    
    JOCKEY_CACHE[url] = default_name
    return default_name
"""

def fix_missing_functions(filename='Colab_JRA_Basic_v2.ipynb'):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_text = "".join(cell['source'])
                
                # Check if this cell is the main function cell
                if "def scrape_race_basic" in source_text:
                    
                    # Check if JOCKEY_CACHE is missing
                    if "JOCKEY_CACHE = {}" not in source_text:
                        # Insert it. Best place: After TRAINER_CACHE
                        if "TRAINER_CACHE = {}" in source_text:
                            # We can split the source and insert.
                            # But splitting by string replacement is safer for exact match.
                            # Or we can just prepend/append it.
                            # But we need it defined BEFORE use.
                            # Let's insert it before "def get_trainer_fullname" line, or just after TRAINER_CACHE.
                            
                            lines = source_text.splitlines(keepends=True)
                            new_lines = []
                            for line in lines:
                                new_lines.append(line)
                                if "TRAINER_CACHE = {}" in line:
                                    new_lines.append("\n" + JOCKEY_HELPER_CODE + "\n")
                                    print("  ✅ Inserted Jockey Helper Code")
                                    modified = True
                            
                            cell['source'] = new_lines
                        else:
                            # Fallback: Prepend to the cell
                            cell['source'] = [JOCKEY_HELPER_CODE + "\n"] + cell['source']
                            print("  ✅ Prepened Jockey Helper Code")
                            modified = True

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved FIXED JRA {filename}")
        else:
            print(f"⚠️ No changes made to {filename} (Jockey functions might be present?)")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

if __name__ == "__main__":
    fix_missing_functions()
