import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    print("Importing scraper.chrome_driver...")
    from scraper import chrome_driver
    print("SUCCESS: chrome_driver imported.")

    print("Importing scraper.auto_scraper...")
    from scraper import auto_scraper
    print("SUCCESS: auto_scraper imported.")
    
    # Check function existence
    if hasattr(auto_scraper, 'scrape_odds_for_race'):
        print("SUCCESS: scrape_odds_for_race exists.")
    else:
        print("FAILURE: scrape_odds_for_race MISSING.")
        
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
