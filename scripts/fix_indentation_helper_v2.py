import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def force_helper_rewrite(filepath):
    print(f"🔧 Force Rewrite Helper in {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_str = "".join(cell['source'])
                if "def get_jockey_fullname" in source_str:
                    # Found the target cell.
                    # We will KEEP lines BEFORE the helper, and REPLACE lines of the helper.
                    
                    new_source = []
                    helper_started = False
                    
                    for line in cell['source']:
                        if "def get_jockey_fullname" in line:
                            helper_started = True
                            # Insert Clean Logic Here ONCE
                            clean_helper = [
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
                            new_source.extend(clean_helper)
                        
                        elif helper_started:
                            # We are inside the old helper body (or what we think it is).
                            # We skip lines until we see something that clearly isn't helper.
                            # But since helper was likely at the end, we can verify.
                            # Or just skip indent 4+ lines?
                            if line.startswith("def ") or line.startswith("class "):
                                # New block?
                                new_source.append(line)
                                helper_started = False
                            else:
                                # Skip old body
                                pass
                        else:
                            new_source.append(line)
                    
                    if len(new_source) != len(cell['source']): # or modified check is hard
                        cell['source'] = new_source
                        modified = True
                        print(f"  Rewrote cell in {filepath}")

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Applied Force Rewrite to {filepath}")
        else:
            print(f"⚠️ Helper function not found to rewrite in {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        force_helper_rewrite(nb)
