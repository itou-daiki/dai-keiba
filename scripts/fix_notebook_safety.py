import json
import os

def get_safe_jra_logic():
    return [
        "    def save_chunk(df_chunk):\\n",
        "        if os.path.exists(CSV_FILE_PATH):\\n",
        "            try:\\n",
        "                # Read types as string to prevent auto-float for IDs\\n",
        "                existing_df = pd.read_csv(CSV_FILE_PATH, dtype={'race_id': str, 'horse_id': str}, low_memory=False)\\n",
        "                combined_df = pd.concat([existing_df, df_chunk], ignore_index=True)\\n",
        "            except pd.errors.EmptyDataError:\\n",
        "                print(\"  Note: File empty, creating new.\")\\n",
        "                combined_df = df_chunk\\n",
        "            except Exception as e:\\n",
        "                # ★ CRITICAL FIX: Do NOT overwrite on generic read errors (e.g. MemoryError)\\n",
        "                print(f\"❌ CRITICAL ERROR: Could not read existing CSV ({e}). Aborting save to prevent data loss.\")\\n",
        "                raise e\\n",
        "        else:\\n",
        "            combined_df = df_chunk\\n",
        "\\n",
        "        # Deduplication\\n",
        "        subset_cols = ['race_id', '馬名']\\n",
        "        subset_cols = [c for c in subset_cols if c in combined_df.columns]\\n",
        "        if subset_cols:\\n",
        "            combined_df.drop_duplicates(subset=subset_cols, keep='last', inplace=True)\\n",
        "\\n",
        "        combined_df.to_csv(CSV_FILE_PATH, index=False, encoding=\"utf-8-sig\")\\n",
        "        print(f\"  [Saved] Total rows: {len(combined_df)} (+{len(df_chunk)} new)\")\\n"
    ]

def get_safe_nar_logic():
    return [
        "    def save_callback(df_new):\\n",
        "        if df_new is None or df_new.empty: return\\n",
        "\\n",
        "        if os.path.exists(CSV_FILE_PATH_NAR):\\n",
        "            try:\\n",
        "                existing = pd.read_csv(CSV_FILE_PATH_NAR, dtype={'race_id': str, 'horse_id': str}, low_memory=False)\\n",
        "                combined = pd.concat([existing, df_new], ignore_index=True)\\n",
        "                # Deduplicate\\n",
        "                if 'race_id' in combined.columns and '馬 番' in combined.columns:\\n",
        "                    combined = combined.drop_duplicates(subset=['race_id', '馬 番'], keep='last')\\n",
        "                combined.to_csv(CSV_FILE_PATH_NAR, index=False)\\n",
        "                print(f\"  [Saved] {len(df_new)} rows added. Total: {len(combined)}\")\\n",
        "            except Exception as e:\\n",
        "                # ★ CRITICAL FIX\\n",
        "                print(f\"❌ Read Error: {e}. Aborting to PREVENT OVERWRITE.\")\\n",
        "                raise e\\n",
        "        else:\\n",
        "            df_new.to_csv(CSV_FILE_PATH_NAR, index=False)\\n",
        "            print(f\"  [Created] {CSV_FILE_PATH_NAR} with {len(df_new)} rows.\")\\n"
    ]

def patch_notebook(path, target_func_name, safe_logic):
    print(f"Patching {path}...")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        params_cell_idx = -1
        
        for idx, cell in enumerate(nb['cells']):
            if cell['cell_type'] == 'code':
                source_str = "".join(cell['source'])
                if f"def {target_func_name}" in source_str:
                    print(f"  Found target function '{target_func_name}' in cell {idx}.")
                    
                    # We need to preserve the outer function definition line and global vars if any
                    # But the easiest way is to read the source, find the function start, and replace the body.
                    # Since the structure is consistent, we can reconstruct the whole cell or just the inner function.
                    
                    # Simpler approach: Re-write the cell content completely if it matches our expectation of "Execution Function Definition" cell.
                    # JRA: def jra_scrape_execution...
                    # NAR: def nar_scrape_execution...
                    
                    new_source = []
                    
                    # Reconstruct JRA Cell
                    if target_func_name == 'save_chunk': # JRA
                        new_source.append("# 3. スクレイピング実行関数の定義\n\n")
                        new_source.append("def jra_scrape_execution(year_str, start_date=None, end_date=None):\n")
                        new_source.append("    CSV_FILE_PATH = os.path.join(PROJECT_PATH, \"database.csv\")\n")
                        new_source.append("    print(f\"Using CSV Path: {CSV_FILE_PATH}\")\n\n")
                        # Logic lines already have \n from get_safe_jra_logic which returns strings with \n (if corrected)
                        # Actually get_safe_jra_logic also has \\n. We need to fix that too.
                        # Let's handle the extend part separately or trust the helper fix.
                        # For now, fix the append lines.
                        for line in safe_logic:
                            new_source.append(line.replace("\\n", "\n") if "\\n" in line else line)
                        
                        new_source.append("\n")
                        new_source.append("    print(f\"Starting Scraping for {year_str} ({start_date} ~ {end_date})\")\n\n")
                        new_source.append("    # Load existing IDs to skip\n")
                        new_source.append("    existing_ids = set()\n")
                        new_source.append("    if os.path.exists(CSV_FILE_PATH):\n")
                        new_source.append("        try:\n")
                        new_source.append("             df_e = pd.read_csv(CSV_FILE_PATH, usecols=['race_id'], dtype={'race_id': str}, low_memory=False)\n")
                        new_source.append("             existing_ids = set(df_e['race_id'].astype(str))\n")
                        new_source.append("             print(f\"  Loaded {len(existing_ids)} existing race IDs to skip.\")\n")
                        new_source.append("        except:\n")
                        new_source.append("             pass\n\n")
                        new_source.append("    scrape_jra_year(year_str, start_date=start_date, end_date=end_date, save_callback=save_chunk, existing_race_ids=existing_ids)\n")
                    
                    # Reconstruct NAR Cell
                    elif target_func_name == 'save_callback': # NAR
                        new_source.append("# 3. スクレイピング実行関数の定義\n\n")
                        new_source.append("def nar_scrape_execution(year_str, start_date=None, end_date=None):\n")
                        new_source.append("    CSV_FILE_PATH_NAR = os.path.join(PROJECT_PATH, \"database_nar.csv\")\n")
                        new_source.append("    print(f\"Using CSV Path: {CSV_FILE_PATH_NAR}\")\n\n")
                        
                        for line in safe_logic:
                            new_source.append(line.replace("\\n", "\n") if "\\n" in line else line)

                        new_source.append("\n")
                        new_source.append("    print(f\"Starting NAR Scraping for {year_str} ({start_date} ~ {end_date})\")\n\n")
                        new_source.append("    # Load existing IDs to skip\n")
                        new_source.append("    existing_ids = set()\n")
                        new_source.append("    if os.path.exists(CSV_FILE_PATH_NAR):\n")
                        new_source.append("        try:\n")
                        new_source.append("             df_e = pd.read_csv(CSV_FILE_PATH_NAR, usecols=['race_id'], dtype={'race_id': str}, low_memory=False)\n")
                        new_source.append("             existing_ids = set(df_e['race_id'].astype(str))\n")
                        new_source.append("             print(f\"  Loaded {len(existing_ids)} existing race IDs to skip.\")\n")
                        new_source.append("        except:\n")
                        new_source.append("             pass\n\n")
                        new_source.append("    scrape_nar_year(year_str, start_date=start_date, end_date=end_date, save_callback=save_callback, existing_race_ids=existing_ids)\n")

                    cell['source'] = new_source
                    print(f"  Applied patch to cell {idx}.")
                    params_cell_idx = idx
                    break
        
        if params_cell_idx != -1:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print("  Success.")
        else:
            print("  Target cell not found.")

    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    base_dir = "/Users/itoudaiki/Program/dai-keiba"
    jra_path = os.path.join(base_dir, "notebooks/JRA_Scraper.ipynb")
    nar_path = os.path.join(base_dir, "notebooks/NAR_Scraper.ipynb")
    
    if os.path.exists(jra_path):
        patch_notebook(jra_path, "save_chunk", get_safe_jra_logic())
        
    if os.path.exists(nar_path):
        patch_notebook(nar_path, "save_callback", get_safe_nar_logic())
