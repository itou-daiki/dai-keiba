import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
print(sys.path)

try:
    import auto_scraper
except ImportError:
    # If running from root, scraper is a package
    from scraper import auto_scraper

# Test ID: 202305021211 (2023 Tokyo Derby)
# Or a smaller race to be polite?
# Let's try a 5-horse race? hard to find.
# Just try 202305021211.
race_id = "202305021211" 

print(f"Testing scrape_race_data for {race_id}...")
df = auto_scraper.scrape_race_data(race_id)

if df is not None:
    print("Scrape successful!")
    print("Columns:", df.columns)
    print("Head:", df.head(1))
    
    if 'past_1_run_style' in df.columns:
        print("Past Data Columns Found.")
        print("Sample Past Run Style:", df['past_1_run_style'].iloc[0])
    else:
        print("Past Data Columns MISSING.")
else:
    print("Scrape returned None.")
