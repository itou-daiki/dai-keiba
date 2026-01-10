import requests
from bs4 import BeautifulSoup
import time

def inspect_pedigree(horse_id="2019105219"): # Equinox
    url = f"https://db.netkeiba.com/horse/ped/{horse_id}/"
    print(f"Fetching {url}...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers)
        r.encoding = 'EUC-JP'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        tbl = soup.select_one('table.blood_table')
        if not tbl:
            print("❌ No blood_table found.")
            return

        print("\n--- Blood Table Structure ---")
        # Print first few TDs with row/col span info
        # Structure is usually:
        # TR1: Father (rowspan 16?), F-Father, ...
        # TR...: Mother is usually halfway down.
        
        trs = tbl.find_all('tr')
        print(f"Total Rows: {len(trs)}")
        
        for i, tr in enumerate(trs):
            tds = tr.find_all('td')
            row_info = []
            for j, td in enumerate(tds):
                txt = td.text.strip().split('\n')[0]
                rs = td.get('rowspan', 1)
                row_info.append(f"[{txt} (rs={rs})]")
            
            # Print only key rows to avoid spam
            if i in [0, 8, 16, 17, 32]: # Guessing indices
                print(f"Row {i}: {', '.join(row_info)}")
            elif i < 5:
                print(f"Row {i}: {', '.join(row_info)}")
                
        # Heuristic Check
        # Father: tr[0].td[0]
        # Mother: tr[16].td[0]? (If 32 rows?) Or tr[8]?
        # Usually 5 generation = 2^5 = 32 leaf nodes? 
        # Netkeiba usually shows 5 generations.
        
        # Let's find "Mother" by identifying the rowspan structure.
        # Father has huge rowspan.
        # Mother has huge rowspan (2nd in column 0?).
        
        # Collect Generation 1 (Parents)
        parents = []
        for i, tr in enumerate(trs):
            tds = tr.find_all('td')
            for td in tds:
                if 'rowspan' in td.attrs:
                    rs = int(td['rowspan'])
                    if rs >= 16: # Likely Parent
                         parents.append((i, td.text.strip().split('\n')[0]))
        
        print("\n--- Detected Parents (Heuristic rs>=16) ---")
        for idx, p in parents:
            print(f"Row {idx}: {p}")

        # BMS (Mother's Father)
        # Mother is usually the 2nd parent.
        # BMS is the 1st parent of the Mother.
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_pedigree()
