import re

def extract_params():
    try:
        with open('scraper/jra_search_dump.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex to find objParam assignments
        # objParam["2501"] = "xx";
        matches = re.findall(r'objParam\["(\d+)"\]\s*=\s*"([^"]+)";', content)
        
        print(f"Found {len(matches)} params.")
        for k, v in matches:
            if k.startswith("25") or k.startswith("24"): # 2025 or 2024
                print(f"{k} -> {v}")
                
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    extract_params()
