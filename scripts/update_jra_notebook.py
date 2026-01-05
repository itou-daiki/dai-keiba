import json
import os

NB_PATH = 'notebooks/JRA_Scraper.ipynb'

def update_notebook():
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
            if "def fill_missing_past_data_notebook():" in source and "fill_missing_past_data_notebook()" in source:
                target_cell = cell
                break
    
    if not target_cell:
        print("Target cell not found.")
        return

    # Prepare new code lines (indented 4 spaces)
    # Logic: Insert AFTER "Done filling past data." print, and BEFORE the final function call.
    
    new_code = [
        "\n",
        "    # 3. Fill Blood/Pedigree Data (father, mother, bms)\n",
        "    # -------------------------------------------------\n",
        "    print('Checking Pedigree Data...')\n",
        "    ped_cols = ['father', 'mother', 'bms']\n",
        "    # Ensure columns exist\n",
        "    new_ped_cols = [c for c in ped_cols if c not in df.columns]\n",
        "    if new_ped_cols:\n",
        "         df_ped = pd.DataFrame(None, index=df.index, columns=new_ped_cols, dtype='object')\n",
        "         df = pd.concat([df, df_ped], axis=1)\n",
        "\n",
        "    # Identify horses with missing 'father'\n",
        "    unique_horses_df = df[['horse_id', 'father']].drop_duplicates('horse_id')\n",
        "    missing_horses = unique_horses_df[unique_horses_df['father'].isna() | (unique_horses_df['father'] == '')]['horse_id'].dropna().unique()\n",
        "    \n",
        "    if len(missing_horses) > 0:\n",
        "        print(f'Found {len(missing_horses)} horses with missing pedigree. Fetching...')\n",
        "        ped_map = {}\n",
        "        \n",
        "        def fetch_ped_entry(hid):\n",
        "            scr = RaceScraper()\n",
        "            return (hid, scr.get_horse_profile(hid))\n",
        "            \n",
        "        with ThreadPoolExecutor(max_workers=5) as executor:\n",
        "            futures = {executor.submit(fetch_ped_entry, hid): hid for hid in missing_horses}\n",
        "            completed = 0\n",
        "            for future in as_completed(futures):\n",
        "                completed += 1\n",
        "                if completed % 50 == 0: print(f'  [Pedigree] {completed}/{len(missing_horses)}')\n",
        "                try:\n",
        "                    hid, p_data = future.result()\n",
        "                    if p_data:\n",
        "                        ped_map[hid] = p_data\n",
        "                except:\n",
        "                    pass\n",
        "        \n",
        "        print('Applying pedigree data...')\n",
        "        f_map = {h: d.get('father') for h, d in ped_map.items()}\n",
        "        m_map = {h: d.get('mother') for h, d in ped_map.items()}\n",
        "        b_map = {h: d.get('bms') for h, d in ped_map.items()}\n",
        "        \n",
        "        mask = df['horse_id'].isin(ped_map.keys())\n",
        "        df.loc[mask, 'father'] = df.loc[mask, 'horse_id'].map(f_map).fillna(df.loc[mask, 'father'])\n",
        "        df.loc[mask, 'mother'] = df.loc[mask, 'horse_id'].map(m_map).fillna(df.loc[mask, 'mother'])\n",
        "        df.loc[mask, 'bms'] = df.loc[mask, 'horse_id'].map(b_map).fillna(df.loc[mask, 'bms'])\n",
        "        \n",
        "        df.to_csv(csv_path, index=False, encoding='utf-8-sig')\n",
        "        print('Done filling pedigree.')\n",
        "    else:\n",
        "        print('All pedigree data present.')\n",
        "\n"
    ]

    # Reconstruct source
    new_source = []
    inserted = False
    
    for line in target_cell['source']:
        new_source.append(line)
        if "print('Done filling past data.')" in line and not inserted:
            new_source.extend(new_code)
            inserted = True
            
    target_cell['source'] = new_source
    
    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=4, ensure_ascii=False)
        
    print(f"Updated {NB_PATH} with pedigree logic.")

if __name__ == "__main__":
    update_notebook()
