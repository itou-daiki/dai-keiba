
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
import auto_scraper

def test_jra_schedule():
    print("Testing JRA Schedule Scraping with auto_scraper...")
    success, msg = auto_scraper.scrape_todays_schedule(mode="JRA")
    print(f"Result: {success}, Message: {msg}")
    
    # Check JSON
    import json
    try:
        with open("todays_data.json", "r") as f:
            data = json.load(f)
            print(f"Saved Date: {data.get('date')}")
            races = data.get("races", [])
            print(f"Saved {len(races)} races.")
            if races:
                print("First 5 races:")
                for r in races[:5]:
                    print(f"  {r['date']} {r['venue']} {r['number']}R: {r['name']}")
                    
                # Check for Unknown
                unknowns = [r for r in races if r['venue'] == 'Unknown']
                print(f"Unknown Venues Count: {len(unknowns)}")
                if unknowns:
                    print(f"Sample Unknown: {unknowns[0]}")
    except Exception as e:
        print(f"Error reading JSON: {e}")

if __name__ == "__main__":
    test_jra_schedule()
