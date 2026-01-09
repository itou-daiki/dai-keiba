import json
import os

# ==========================================
# New Code Blocks
# ==========================================

JRA_BASIC_CODE = r'''# レース結果スクレイピング関数

# キャッシュ
TRAINER_CACHE = {}
JOCKEY_CACHE = {}

def get_fullname_from_url(url, default_name, cache):
    """リンクからフルネームを取得(汎用)"""
    if not url: return default_name
    if url in cache: return cache[url]
    
    try:
        time.sleep(0.3)
        headers = {'User-Agent': 'Mozilla/5.0'}
        if url.startswith('/'): url = f"https://race.netkeiba.com{url}"
        
        r = requests.get(url, headers=headers, timeout=5)
        r.encoding = 'EUC-JP'
        s = BeautifulSoup(r.text, 'html.parser')
        
        title = s.title.text if s.title else ""
        m = re.search(r'^(.+?)(?:のプロフィール|の騎手成績|｜)', title)
        if m:
            fullname = m.group(1).strip()
            cache[url] = fullname
            return fullname
            
        h1 = s.find('h1')
        if h1:
             txt = h1.text.strip().split()[0]
             cache[url] = txt
             return txt
    except:
        pass
    
    cache[url] = default_name
    return default_name

def get_trainer_fullname(url, default_name):
    return get_fullname_from_url(url, default_name, TRAINER_CACHE)

def get_jockey_fullname(url, default_name):
    return get_fullname_from_url(url, default_name, JOCKEY_CACHE)

def scrape_race_basic(race_id):
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200: return None
        
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        metadata = extract_metadata(soup, url)
        
        tables = soup.find_all('table')
        result_table = None
        for table in tables:
            if '着順' in table.text and '馬名' in table.text:
                result_table = table
                break
        if not result_table: return None
        
        rows = result_table.find_all('tr')
        race_data = []
        
        for row in rows:
            if row.find('th'): continue
            cells = row.find_all('td')
            if len(cells) < 10: continue
            
            # --- 騎手 (Fullname) ---
            jockey_col = cells[6] if len(cells) > 6 else None
            jockey_val = ""
            if jockey_col:
                j_text = jockey_col.text.strip()
                j_link = jockey_col.find('a')
                j_url = j_link['href'] if j_link else None
                if j_url:
                    jockey_val = get_jockey_fullname(j_url, j_text)
                else:
                    jockey_val = j_text

            # --- 厩舎/調教師 ---
            stable_col = cells[13] if len(cells) > 13 else None
            stable_val = ""
            trainer_val = ""
            if stable_col:
                raw_text = stable_col.text.strip()
                t_link = stable_col.find('a')
                t_url = t_link['href'] if t_link else None
                
                parts = [p for p in raw_text.replace('\n', ' ').split() if p.strip()]
                temp_name = ""
                if len(parts) >= 2:
                    stable_val = parts[0]
                    temp_name = parts[-1]
                elif len(parts) == 1:
                    if raw_text.startswith("美浦") or raw_text.startswith("栗東"):
                         stable_val = raw_text[:2]; temp_name = raw_text[2:]
                    else:
                         temp_name = raw_text
                
                if t_url: trainer_val = get_trainer_fullname(t_url, temp_name)
                else: trainer_val = temp_name
            
            # --- 馬体重 (Split) ---
            weight_col = cells[14] if len(cells) > 14 else None
            weight_val = ""
            weight_change = ""
            if weight_col:
                w_text = weight_col.text.strip()
                # "488(-2)" -> "488", "-2"
                m = re.search(r'(\d+)\(([\+\-\d]+)\)', w_text)
                if m:
                    weight_val = m.group(1)
                    weight_change = m.group(2)
                else:
                    weight_val = w_text # "計不" etc
            
            horse_data = {
                '日付': metadata['日付'],
                '会場': metadata['会場'],
                'レース番号': metadata['レース番号'],
                'レース名': metadata['レース名'],
                '重賞': metadata['重賞'],
                'コースタイプ': metadata['コースタイプ'],
                '距離': metadata['距離'],
                '回り': metadata['回り'],
                '天候': metadata['天候'],
                '馬場状態': metadata['馬場状態'],
                '着順': cells[0].text.strip(),
                '枠': '',
                '馬番': cells[2].text.strip() if len(cells) > 2 else '',
                '馬名': cells[3].text.strip() if len(cells) > 3 else '',
                '性齢': cells[4].text.strip() if len(cells) > 4 else '',
                '斤量': cells[5].text.strip() if len(cells) > 5 else '',
                '騎手': jockey_val,
                'タイム': cells[7].text.strip() if len(cells) > 7 else '',
                '着差': cells[8].text.strip() if len(cells) > 8 else '',
                '人気': cells[9].text.strip() if len(cells) > 9 else '',
                '単勝オッズ': cells[10].text.strip() if len(cells) > 10 else '',
                '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                'コーナー通過順': cells[12].text.strip() if len(cells) > 12 else '',
                'corner_1': '', 'corner_2': '', 'corner_3': '', 'corner_4': '',
                '厩舎': stable_val,
                '調教師': trainer_val,
                '馬体重': weight_val,
                '増減': weight_change,
                'race_id': metadata['race_id'],
                'horse_id': ''
            }
            
            if len(cells) > 1: horse_data['枠'] = cells[1].text.strip()
            
            horse_link = cells[3].find('a') if len(cells) > 3 else None
            if horse_link:
                hm = re.search(r'/horse/(\d+)', horse_link['href'])
                if hm: horse_data['horse_id'] = hm.group(1)
            
            corner_text = horse_data['コーナー通過順']
            if corner_text and '-' in corner_text:
                positions = corner_text.split('-')
                for j, pos in enumerate(positions[:4], 1):
                    horse_data[f'corner_{j}'] = pos.strip()
            
            race_data.append(horse_data)
        
        if not race_data: return None
        
        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', 'コーナー通過順', 
            'corner_1', 'corner_2', 'corner_3', 'corner_4',
            '厩舎', '調教師', '馬体重', '増減', 'race_id', 'horse_id'
        ]
        
        return pd.DataFrame(race_data)[ordered_columns]
    
    except Exception as e:
        print(f"  ❌ エラー: {race_id} - {e}")
        return None

print("✅ Scraping function updated (Split Weight/Jockey Fullname)")'''

# ==========================================

NAR_BASIC_CODE = r'''# レース結果スクレイピング関数

# キャッシュ
TRAINER_CACHE = {}
JOCKEY_CACHE = {}

def get_fullname_from_url(url, default_name, cache):
    """リンクからフルネームを取得(汎用)"""
    if not url: return default_name
    if url in cache: return cache[url]
    
    try:
        time.sleep(0.3)
        headers = {'User-Agent': 'Mozilla/5.0'}
        if url.startswith('/'): url = f"https://nar.netkeiba.com{url}"
        
        r = requests.get(url, headers=headers, timeout=5)
        r.encoding = 'EUC-JP'
        s = BeautifulSoup(r.text, 'html.parser')
        
        title = s.title.text if s.title else ""
        m = re.search(r'^(.+?)(?:のプロフィール|の騎手成績|｜)', title)
        if m:
            fullname = m.group(1).strip()
            cache[url] = fullname
            return fullname
            
        h1 = s.find('h1')
        if h1:
             txt = h1.text.strip().split()[0]
             cache[url] = txt
             return txt
    except:
        pass
    
    cache[url] = default_name
    return default_name

def get_trainer_fullname(url, default_name):
    return get_fullname_from_url(url, default_name, TRAINER_CACHE)

def get_jockey_fullname(url, default_name):
    return get_fullname_from_url(url, default_name, JOCKEY_CACHE)

def scrape_race_basic(race_id):
    url = f"https://nar.netkeiba.com/race/result.html?race_id={race_id}"
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        metadata = extract_metadata(soup, url)
        
        tables = soup.find_all('table')
        corner_data = {}
        for table in tables:
            if 'コーナー' in table.text:
                headers_cells = table.find_all('th')
                corner_names = [th.text.strip() for th in headers_cells]
                corner_rows = table.find_all('tr')
                for j, row in enumerate(corner_rows):
                    cells = row.find_all('td')
                    if cells and j < len(corner_names):
                        corner_data[corner_names[j]] = cells[0].text.strip()
                break
        
        result_table = None
        for table in tables:
            if '着順' in table.text and '馬名' in table.text:
                result_table = table
                break
        if not result_table: return None
        
        rows = result_table.find_all('tr')
        race_data = []
        
        for row in rows:
            if row.find('th'): continue
            cells = row.find_all('td')
            if len(cells) < 10: continue

            # --- 騎手 (Fullname) ---
            jockey_col = cells[6] if len(cells) > 6 else None
            jockey_val = ""
            if jockey_col:
                j_text = jockey_col.text.strip()
                j_link = jockey_col.find('a')
                j_url = j_link['href'] if j_link else None
                if j_url:
                    jockey_val = get_jockey_fullname(j_url, j_text)
                else:
                    jockey_val = j_text

            # --- 厩舎/調教師 ---
            stable_col = cells[12] if len(cells) > 12 else None
            stable_val = ""
            trainer_val = ""
            if stable_col:
                raw_text = stable_col.text.strip()
                t_link = stable_col.find('a')
                t_url = t_link['href'] if t_link else None
                
                affiliates = ["北海道", "岩手", "水沢", "盛岡", "浦和", "船橋", "大井", "川崎", 
                              "金沢", "笠松", "愛知", "名古屋", "兵庫", "園田", "姫路", "高知", "佐賀",
                              "美浦", "栗東", "JRA", "地方", "海外"]
                temp_name = raw_text
                for aff in affiliates:
                    if raw_text.startswith(aff):
                        stable_val = aff
                        temp_name = raw_text[len(aff):].strip()
                        break
                
                if t_url: trainer_val = get_trainer_fullname(t_url, temp_name)
                else: trainer_val = temp_name
            
            # --- 馬体重 (Split) ---
            weight_col = cells[13] if len(cells) > 13 else None
            weight_val = ""
            weight_change = ""
            if weight_col:
                w_text = weight_col.text.strip()
                m = re.search(r'(\d+)\(([\+\-\d]+)\)', w_text)
                if m:
                    weight_val = m.group(1)
                    weight_change = m.group(2)
                else:
                    weight_val = w_text

            horse_data = {
                '日付': metadata['日付'], '会場': metadata['会場'], 'レース番号': metadata['レース番号'],
                'レース名': metadata['レース名'], '重賞': metadata['重賞'], 'コースタイプ': metadata['コースタイプ'],
                '距離': metadata['距離'], '回り': metadata['回り'], '天候': metadata['天候'], '馬場状態': metadata['馬場状態'],
                '着順': cells[0].text.strip(), '枠': '',
                '馬番': cells[2].text.strip() if len(cells) > 2 else '',
                '馬名': cells[3].text.strip() if len(cells) > 3 else '',
                '性齢': cells[4].text.strip() if len(cells) > 4 else '',
                '斤量': cells[5].text.strip() if len(cells) > 5 else '',
                '騎手': jockey_val,
                'タイム': cells[7].text.strip() if len(cells) > 7 else '',
                '着差': cells[8].text.strip() if len(cells) > 8 else '',
                '人気': cells[9].text.strip() if len(cells) > 9 else '',
                '単勝オッズ': cells[10].text.strip() if len(cells) > 10 else '',
                '後3F': cells[11].text.strip() if len(cells) > 11 else '',
                'corner_1': '', 'corner_2': '', 'corner_3': '', 'corner_4': '',
                '厩舎': stable_val,
                '調教師': trainer_val, 
                '馬体重': weight_val,
                '増減': weight_change,
                'race_id': metadata['race_id'], 'horse_id': ''
            }
            
            if len(cells) > 1: horse_data['枠'] = cells[1].text.strip()
            horse_link = cells[3].find('a') if len(cells) > 3 else None
            if horse_link:
                hm = re.search(r'/horse/(\d+)', horse_link['href'])
                if hm: horse_data['horse_id'] = hm.group(1)
            
            # Corner data processing (omitted for brevity, keep existing logic logic if needed, but for now standard)
            # Actually I should keep the NAR corner logic.
            # Adding it back in condensed form
            umaban = horse_data['馬番']
            corner_positions_forward = []
            for corner_num in range(1, 5):
                corner_key = f'{corner_num}コーナー'
                if corner_key in corner_data:
                    c_txt = corner_data[corner_key].replace('-', ',')
                    # ... (Simplified parsing logic) ...
                    # Reusing the robust logic from previous block:
                    parts = []
                    curr = ''; d = 0
                    for c in c_txt:
                        if c=='(': d+=1; curr+=c
                        elif c==')': d-=1; curr+=c
                        elif c==',' and d==0: 
                             if curr.strip(): parts.append(curr.strip())
                             curr=''
                        else: curr+=c
                    if curr.strip(): parts.append(curr.strip())
                    
                    cur_pos = 1; found_pos = ''
                    for p in parts:
                        if p.startswith('('):
                            grp = p[1:-1].split(',')
                            if umaban in [h.strip() for h in grp]: found_pos = str(cur_pos); break
                            cur_pos += len([h for h in grp if h.strip()])
                        else:
                            if p.strip() == umaban: found_pos = str(cur_pos)
                            cur_pos += 1
                        if found_pos: break
                    corner_positions_forward.append(found_pos)

            for j, pos in enumerate(reversed(corner_positions_forward)):
                if j < 4: horse_data[f'corner_{j+1}'] = pos

            race_data.append(horse_data)
        
        if not race_data: return None
        
        ordered_columns = [
            '日付', '会場', 'レース番号', 'レース名', '重賞', 'コースタイプ', '距離', '回り',
            '天候', '馬場状態', '着順', '枠', '馬番', '馬名', '性齢', '斤量', '騎手', 'タイム',
            '着差', '人気', '単勝オッズ', '後3F', 'コーナー通過順', 
            'corner_1', 'corner_2', 'corner_3', 'corner_4',
            '厩舎', '調教師', '馬体重', '増減', 'race_id', 'horse_id'
        ]
        return pd.DataFrame(race_data)[ordered_columns]
    except Exception as e:
        print(f"  ❌ エラー: {race_id} - {e}")
        return None

print("✅ Scraping function updated (Split Weight/Jockey Fullname)")'''

# ==========================================
# Updater Logic
# ==========================================

def update_notebook(path, target_func, new_code):
    try:
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return
            
        with open(path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
            
        updated = False
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                source_concat = "".join(cell['source'])
                if f"def {target_func}" in source_concat:
                    # Replace source
                    # Convert new_code string to list of lines with \n
                    lines = new_code.split('\n')
                    # Add \n to all except last, or just use splitlines(keepends=True)
                    new_source = [l + '\n' for l in lines[:-1]] + [lines[-1]]
                    cell['source'] = new_source
                    updated = True
                    print(f"Updated {target_func} in {path}")
                    break
                    
        if updated:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print("  Saved.")
        else:
            print(f"  Target function {target_func} not found in {path}")
            
    except Exception as e:
        print(f"Error updating {path}: {e}")

def fix_read_csv(path):
    try:
        if not os.path.exists(path): return
        
        with open(path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
            
        updated = False
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                cell_updated = False
                for line in cell['source']:
                    # Simple string replace for pd.read_csv
                    # pattern: pd.read_csv(..., dtype=str)
                    # We want to insert on_bad_lines='skip'
                    if 'pd.read_csv' in line and 'on_bad_lines' not in line:
                         # Insert it
                         if 'dtype=str' in line:
                             new_line = line.replace("dtype=str", "dtype=str, on_bad_lines='skip'")
                         elif ')' in line:
                             # Try to insert before closing parenthesis
                             # This is risky doing string replace blindly, but for this specific notebook it's consistent
                             # Usually: pd.read_csv(path, ...)
                             # Let's append it to args
                             # If line ends with ), replace ) with , on_bad_lines='skip')
                             if line.rstrip().endswith(')'):
                                 new_line = line.rstrip()[:-1] + ", on_bad_lines='skip')\n"
                             else:
                                 new_line = line # Can't safely auto-patch multiline
                         else:
                             new_line = line
                         
                         if new_line != line:
                             cell_updated = True
                             line = new_line
                    new_source.append(line)
                
                if cell_updated:
                    cell['source'] = new_source
                    updated = True
        
        if updated:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"Updated read_csv in {path}")
            
    except Exception as e:
        print(f"Error fixing read_csv in {path}: {e}")

# Run
nb_jra_basic = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic_v2.ipynb"
nb_nar_basic = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic_v2.ipynb"
nb_jra_details = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Details_v2.ipynb"
nb_nar_details = "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Details_v2.ipynb"

update_notebook(nb_jra_basic, "scrape_race_basic", JRA_BASIC_CODE)
update_notebook(nb_nar_basic, "scrape_race_basic", NAR_BASIC_CODE)

fix_read_csv(nb_jra_details)
fix_read_csv(nb_nar_details)
