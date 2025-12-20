import requests
from bs4 import BeautifulSoup
import re

def explore_nav():
    url = "https://www.jra.go.jp/JRADB/accessS.html"
    cname = "pw01skl00999999/B3" # Past Race Search Page
    
    print(f"POSTing to {url} with cname={cname}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
    }
    
    try:
        response = requests.post(url, data={"cname": cname}, headers=headers, timeout=10)
        response.encoding = 'cp932'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for Year and Month option values
        # id="kaisaiY_list"
        # id="kaisaiM_list"
        
        y_list = soup.find('select', id="kaisaiY_list")
        m_list = soup.find('select', id="kaisaiM_list")
        
        if y_list:
             print("Years found:")
             for opt in y_list.find_all('option'):
                 print(f"  {opt.text}: {opt.get('value')}")
                 
        if m_list:
             print("Months found:")
             for opt in m_list.find_all('option'):
                 print(f"  {opt.text}: {opt.get('value')}")
                 
        # Look for the 'execute' button which likely triggers another CNAME or JS
        # Usually onClick="doAction('/JRADB/accessS.html', 'pw01sk00<YEAR><MONTH>/<SUFFIX>');"
        # Wait, the JS `setParameter` logic in curl output suggests simple string concat maybe?
        
        # Let's verify how the button works by finding the submit button
        btn = soup.find('a', onclick=re.compile("doAction"))
        if btn:
            print(f"Submit action: {btn['onclick']}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    explore_nav()
