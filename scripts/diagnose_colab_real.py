# === COPY AND PASTE THIS INTO A COLAB CELL ===
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

def diagnose_environment():
    print("🔍 DIAGNOSTIC START")
    
    # 1. Target URL (JRA Horse - Equinox)
    url = "https://db.netkeiba.com/horse/2019105219/"
    
    # 2. Test Configurations
    configs = [
        ("Base UA", {'User-Agent': 'Mozilla/5.0'}),
        ("Chrome macOS", {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://db.netkeiba.com/',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8'
        })
    ]
    
    for name, headers in configs:
        print(f"\n--- Testing Configuration: {name} ---")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"  Status Code: {resp.status_code}")
            resp.encoding = 'EUC-JP'
            
            if resp.status_code == 200:
                print(f"  Response Length: {len(resp.text)} chars")
                
                # Check for blocking messages
                if "アクセスが拒否されました" in resp.text or "Forbidden" in resp.text:
                    print("  ⚠️ Likely BLOCKED (Content contains 'Forbidden' or similar)")
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Check Table
                table = soup.select_one("table.db_h_race_results")
                if table:
                    print("  ✅ Access OK! 'table.db_h_race_results' FOUND.")
                    # Try simplified parsing
                    try:
                        df = pd.read_html(io.StringIO(str(table)))[0]
                        print(f"  ✅ Pandas Read OK. Columns: {df.columns.tolist()[:5]}...")
                    except Exception as e:
                        print(f"  ❌ Pandas Read Failed: {e}")
                else:
                    print("  ❌ Table NOT FOUND. Printing all table classes found:")
                    tables = soup.find_all("table")
                    for i, t in enumerate(tables):
                        print(f"    Table {i}: Classes={t.get('class', 'No Class')}, TextSnippet={t.text[:30].strip()}...")
            else:
                print("  ❌ Request Failed (Non-200 Status)")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")

    print("\n🔍 DIAGNOSTIC END")

if __name__ == "__main__":
    diagnose_environment()
