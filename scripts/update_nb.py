
import json
import os

nb_path = '/Users/itoudaiki/Program/dai-keiba/notebooks/JRA_Scraper.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find the cell to patch
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        # Check if this is the patch cell
        if any('JRA_MONTH_PARAMS.update' in line for line in source):
            print("Found target cell.")
            # Find the line with 2022 and update it/insert after
            new_lines = []
            for line in source:
                if '"2022":' in line and not line.strip().endswith(','): 
                   # Add comma to the 2022 line inside the string if it's missing? 
                   # Actually source is a list of strings. Usually they end with \n.
                   # If it's a multiline dict, we need to ensure the previous line ends with comma.
                   # Let's see the line content.
                   line = line.rstrip('\n') + ",\n"
                   new_lines.append(line)
                   
                   # Insert 2021 and 2020
                   new_lines.append('        "2021": { "01": "0F", "02": "DD", "03": "AB", "04": "79", "05": "47", "06": "15", "07": "E3", "08": "B1", "09": "7F", "10": "EE", "11": "BC", "12": "8A" },\n')
                   new_lines.append('        "2020": { "01": "83", "02": "51", "03": "1F", "04": "ED", "05": "BB", "06": "89", "07": "57", "08": "25", "09": "F3", "10": "62", "11": "30", "12": "FE" }\n')
                elif '"2022":' in line:
                    # If it already had comma (unlikely based on my read), just append
                    new_lines.append(line)
                    new_lines.append('        "2021": { "01": "0F", "02": "DD", "03": "AB", "04": "79", "05": "47", "06": "15", "07": "E3", "08": "B1", "09": "7F", "10": "EE", "11": "BC", "12": "8A" },\n')
                    new_lines.append('        "2020": { "01": "83", "02": "51", "03": "1F", "04": "ED", "05": "BB", "06": "89", "07": "57", "08": "25", "09": "F3", "10": "62", "11": "30", "12": "FE" }\n')
                else:
                    new_lines.append(line)
            cell['source'] = new_lines
            break

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=4, ensure_ascii=False)
    print("Notebook updated.")
