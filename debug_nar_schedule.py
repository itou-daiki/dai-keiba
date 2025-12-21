
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
import auto_scraper

def test_nar_schedule_save():
    print("Testing scrape_todays_schedule(mode='NAR')...")
    success, msg = auto_scraper.scrape_todays_schedule(mode="NAR")
    print(f"Success: {success}, Msg: {msg}")
    
    expected_file = "todays_data_nar.json" # Relative to scraper usually.. no, relative to project root in my fix?
    # Fix in auto_scraper was: os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
    # auto_scraper is in scraper/, so dirname is scraper/, dirname(dirname) is root.
    # So it should be in root.
    
    if os.path.exists(expected_file):
        print(f"File {expected_file} created successfully.")
        import json
        with open(expected_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded {len(data.get('races', []))} races.")
    else:
        print(f"File {expected_file} NOT found.")

if __name__ == "__main__":
    test_nar_schedule_save()
