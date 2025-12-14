import requests
from bs4 import BeautifulSoup
import re

def debug_day():
    # 2025/01 List
    cname_month = "pw01skl10202501/3F"
    url = "https://www.jra.go.jp/JRADB/accessS.html"
    
    print(f"Fetching Month List: {cname_month}")
    resp = requests.post(url, data={"cname": cname_month})
    resp.encoding = 'cp932'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find first srl link
    srl_cname = None
    for a in soup.find_all('a'):
        onclick = a.get('onclick', '')
        match = re.search(r"doAction\('[^']+',\s*'([^']+)'\)", onclick)
        if match:
            c = match.group(1)
            if c.startswith('pw01srl'):
                srl_cname = c
                print(f"Found Day CNAME: {srl_cname}")
                break
                
    if not srl_cname:
        print("No Day CNAME found.")
        return

    # Fetch Day List
    print(f"Fetching Day List (POST): {srl_cname}")
    resp_day = requests.post(url, data={"cname": srl_cname})
    resp_day.encoding = 'cp932'
    
    # Inspect content
    print("--- Day List Content Sample ---")
    print(resp_day.text[:2000])
    
    # Check for sde links
    soup_day = BeautifulSoup(resp_day.text, 'html.parser')
    found_sde = 0
    for a in soup_day.find_all('a'):
        onclick = a.get('onclick', '')
        href = a.get('href', '')
        
        if 'pw01sde' in href or 'pw01sde' in onclick:
            print(f"Found SDE Link: href={href}, onclick={onclick}")
            found_sde += 1
            
    print(f"Total SDE links found: {found_sde}")

if __name__ == "__main__":
    debug_day()
