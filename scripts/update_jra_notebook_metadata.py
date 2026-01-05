import json
import os

NB_PATH = 'notebooks/JRA_Scraper.ipynb'

def update_notebook_metadata():
    if not os.path.exists(NB_PATH):
        print("Notebook not found.")
        return

    with open(NB_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Find the cell defining 'fill_missing_past_data_notebook'
    target_cell = None
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = "".join(cell['source'])
            if "def fill_missing_past_data_notebook():" in source:
                target_cell = cell
                break
    
    if not target_cell:
        print("Target cell not found.")
        return

    # Prepare new code lines (indented 4 spaces)
    # Logic: Insert AFTER "Done filling pedigree." print.
    # We add logic to fix Course/Distance/Weather.
    
    new_code = [
        "\n",
        "    # 4. Backfill Missing Metadata (Course Type, Distance, Weather)\n",
        "    # -----------------------------------------------------------\n",
        "    print('Checking Metadata (Course, Distance, Weather)...')\n",
        "    meta_cols = ['コースタイプ', '距離', '天候', '馬場状態']\n",
        "    for c in meta_cols:\n",
        "        if c not in df.columns: df[c] = None\n",
        "\n",
        "    # Filter missing\n",
        "    missing_meta_mask = (df['コースタイプ'].isna()) | (df['コースタイプ'] == '')\n",
        "    if 'race_id' in df.columns:\n",
        "         rids_missing = df.loc[missing_meta_mask, 'race_id'].unique()\n",
        "    else:\n",
        "         rids_missing = []\n",
        "\n",
        "    if len(rids_missing) > 0:\n",
        "        print(f'Found {len(rids_missing)} races with missing metadata. Fetching...')\n",
        "        meta_results = {}\n",
        "        \n",
        "        def fetch_meta_entry(rid):\n",
        "            scr = RaceScraper()\n",
        "            return scr.get_race_metadata(rid)\n",
        "            \n",
        "        with ThreadPoolExecutor(max_workers=5) as executor:\n",
        "            futures = {executor.submit(fetch_meta_entry, rid): rid for rid in rids_missing}\n",
        "            completed = 0\n",
        "            for future in as_completed(futures):\n",
        "                completed += 1\n",
        "                if completed % 20 == 0: print(f'  [Metadata] {completed}/{len(rids_missing)}')\n",
        "                try:\n",
        "                    data = future.result()\n",
        "                    if data and data.get('course_type'):\n",
        "                        meta_results[data['race_id']] = data\n",
        "                except:\n",
        "                    pass\n",
        "        \n",
        "        print('Applying metadata...')\n",
        "        # Create maps\n",
        "        c_map = {rid: d['course_type'] for rid, d in meta_results.items()}\n",
        "        d_map = {rid: d['distance'] for rid, d in meta_results.items()}\n",
        "        w_map = {rid: d['weather'] for rid, d in meta_results.items()}\n",
        "        cond_map = {rid: d['condition'] for rid, d in meta_results.items()}\n",
        "        \n",
        "        df.loc[missing_meta_mask, 'コースタイプ'] = df.loc[missing_meta_mask, 'race_id'].map(c_map).fillna(df.loc[missing_meta_mask, 'コースタイプ'])\n",
        "        df.loc[missing_meta_mask, '距離'] = df.loc[missing_meta_mask, 'race_id'].map(d_map).fillna(df.loc[missing_meta_mask, '距離'])\n",
        "        df.loc[missing_meta_mask, '天候'] = df.loc[missing_meta_mask, 'race_id'].map(w_map).fillna(df.loc[missing_meta_mask, '天候'])\n",
        "        df.loc[missing_meta_mask, '馬場状態'] = df.loc[missing_meta_mask, 'race_id'].map(cond_map).fillna(df.loc[missing_meta_mask, '馬場状態'])\n",
        "        \n",
        "        df.to_csv(csv_path, index=False, encoding='utf-8-sig')\n",
        "        print('Done filling metadata.')\n",
        "    else:\n",
        "        print('All metadata present.')\n",
        "\n"
    ]

    # Reconstruct source
    new_source = []
    inserted = False
    
    # We look for "Done filling pedigree." which was added in previous step.
    # If not found (maybe overwrite?), look for "Done filling past data." and append AFTER previous insertion.
    
    found_pedigree = False
    for line in target_cell['source']:
        if "Done filling pedigree." in line:
            found_pedigree = True
            break
            
    insert_marker = "print('Done filling pedigree.')" if found_pedigree else "print('Done filling past data.')"
    
    for line in target_cell['source']:
        new_source.append(line)
        if insert_marker in line and not inserted:
            new_source.extend(new_code)
            inserted = True
            
    target_cell['source'] = new_source
    
    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=4, ensure_ascii=False)
        
    print(f"Updated {NB_PATH} with metadata backfill logic.")

if __name__ == "__main__":
    update_notebook_metadata()
