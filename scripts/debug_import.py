import sys
import os

# Mimic public_app.py
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml'))

print("Attempting to import auto_scraper...")
try:
    import auto_scraper
    print("Success: auto_scraper imported.")
except ImportError as e:
    print(f"Failed: {e}")
except Exception as e:
    print(f"Error during import: {e}")
