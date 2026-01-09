import json
import re
import ast
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup
import sys
import os

# Configuration
DATA_DIR = '/Users/itoudaiki/Program/dai-keiba/data/raw'
NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'
YEARS = range(2020, 2027)
SAMPLES_PER_YEAR = 10

def load_notebook_source(filepath):
    """Extracts code from code cells in a valid notebook."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        source = ""
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                cell_source = "".join(cell['source'])
                # Skip magics
                cell_source = "\n".join([line for line in cell_source.split('\n') if not line.strip().startswith(('!', '%'))])
                source += cell_source + "\n\n"
        return source
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return None

def check_syntax(code, filename):
    """Checks for syntax errors in the provided code."""
    try:
        ast.parse(code)
        print(f"✅ Syntax OK: {filename}")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax Error in {filename}: line {e.lineno}, offset {e.offset}: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Error checking syntax for {filename}: {e}")
        return False

def extract_functions(source_code):
    """
    Extracts function definitions by executing the code in a confined namespace.
    """
    namespace = {}
    
    # Mocking
    mock_code = """
class MockDrive:
    def mount(self, path): pass
drive = MockDrive()
def display(*args): pass
class Javascript:
    def __init__(self, *args): pass
"""
    
    # Pre-execution: standard imports
    pre_imports = """
import sys
from unittest.mock import MagicMock
if 'google.colab' not in sys.modules:
    sys.modules['google.colab'] = MagicMock()
if 'IPython' not in sys.modules:
    sys.modules['IPython'] = MagicMock()
if 'IPython.display' not in sys.modules:
    sys.modules['IPython.display'] = MagicMock()

import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import os
import io
"""
    
    try:
        exec(mock_code, namespace)
        exec(pre_imports, namespace)
        
        lines = source_code.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith(('!', '%')): continue
            if 'drive.mount' in line: continue
            if 'run_basic_scraping()' in line and not line.strip().startswith('def '): continue
            if 'run_details_scraping()' in line and not line.strip().startswith('def '): continue
            if 'function ClickConnect' in line: continue
            if 'console.log' in line: continue
            if 'clean_output' in line: continue
            
            cleaned_lines.append(line)
            
        final_code = "\n".join(cleaned_lines)
        
        try:
            exec(final_code, namespace)
        except SyntaxError as e:
            print(f"⚠️ SyntaxError in extraction: {e}")
            print(f"   Line {e.lineno}: {final_code.split(chr(10))[e.lineno-1]}")
            return None
        except IndentationError as e:
            print(f"⚠️ IndentationError in extraction: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Runtime Error during extraction: {e}")
            return None
            
        return namespace

    except Exception as e:
        print(f"⚠️ Setup failed: {e}")
        return None

def get_sampled_race_ids(is_nar=False):
    """Gets random race IDs from CSV."""
    filename = 'race_ids_nar.csv' if is_nar else 'race_ids.csv'
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return []
        
    try:
        df = pd.read_csv(filepath, dtype=str)
        col = 'race_id'
        if col not in df.columns:
            print(f"❌ Column 'race_id' not found in {filename}")
            return []
            
        df = df[df[col].notna()]
        
        sampled_ids = []
        for year in YEARS:
            year_str = str(year)
            year_df = df[df[col].str.startswith(year_str)]
            
            if len(year_df) >= SAMPLES_PER_YEAR:
                sampled = year_df.sample(n=SAMPLES_PER_YEAR, random_state=42)[col].tolist()
            else:
                sampled = year_df[col].tolist()
            
            sampled_ids.extend(sampled)
            
        return sampled_ids
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")
        return []

def verify_jra_basic(namespace, race_ids):
    print(f"\n🔍 Verifying JRA Basic... ({len(race_ids)} races)")
    if 'scrape_race_basic' not in namespace:
        print("❌ 'scrape_race_basic' function not found.")
        return [], []
    
    success_count = 0
    cols = None
    details_samples = [] # List of (horse_id, date, year)
    
    # Track years to ensure we get samples from different years
    sampled_years = set()
    
    for rid in race_ids:
        try:
            df = namespace['scrape_race_basic'](rid)
            if df is not None and not df.empty:
                success_count += 1
                cols = list(df.columns)
                
                # Sample a horse for details verification (one per year if possible)
                year = str(rid)[:4]
                if year not in sampled_years:
                     # Pick a random row
                     row = df.sample(1).iloc[0]
                     if row['horse_id'] and row['日付']:
                         details_samples.append((row['horse_id'], row['日付'], year))
                         sampled_years.add(year)

                # REFINEMENT CHECKS
                # 1. Check Trainer Name
                if '調教師' in df.columns:
                    trainers = df['調教師'].dropna().tolist()
                    for t in trainers:
                        if "の調教師成績" in t:
                            print(f"  ❌ Trainer name contains suffix: {t}")
                        if "のプロフィール" in t:
                            print(f"  ❌ Trainer name contains suffix: {t}")
                
                # 2. Check Weight Change
                if '増減' in df.columns: # Assuming '増減' is the column for weight change
                    changes = df['増減'].dropna().tolist()
                    for c in changes:
                        if "+" in str(c):
                             print(f"  ❌ Weight change contains '+': {c}")
                
                # 3. Check Removed Column
                if 'コーナー通過順' in df.columns:
                    print("  ❌ 'コーナー通過順' still present in columns")
            else:
                print(f"  ⚠️ No data for {rid}")
        except Exception as e:
            print(f"  ❌ Error scraping {rid}: {e}")
    
    if success_count > 0:
        print(f"  ✅ JRA Basic: {success_count}/{len(race_ids)} races scaped successfully.")
    
    if cols:
        print(f"  ✅ Columns ({len(cols)}): {cols}")
        return cols, details_samples
    return [], []

def verify_nar_basic(namespace, race_ids):
    print(f"\n🔍 Verifying NAR Basic... ({len(race_ids)} races)")
    if 'scrape_race_basic' not in namespace:
        print("❌ 'scrape_race_basic' function not found.")
        return [], []
    
    success_count = 0
    cols = None
    details_samples = []
    sampled_years = set()
    
    for rid in race_ids:
        try:
            df = namespace['scrape_race_basic'](rid)
            if df is not None and not df.empty:
                success_count += 1
                cols = list(df.columns)
                
                year = str(rid)[:4]
                if year not in sampled_years:
                     row = df.sample(1).iloc[0]
                     if row['horse_id'] and row['日付']:
                         details_samples.append((row['horse_id'], row['日付'], year))
                         sampled_years.add(year)
            else:
                print(f"  ⚠️ No data for {rid}")
        except Exception as e:
            print(f"  ❌ Error scraping {rid}: {e}")
            
    if success_count > 0:
        print(f"  ✅ NAR Basic: {success_count}/{len(race_ids)} races scaped successfully.")

    if cols:
        print(f"  ✅ Columns ({len(cols)}): {cols}")
        return cols, details_samples
    return [], []

def verify_details_mode(namespace, horse_id, race_date, mode_name):
    print(f"\n🔍 Verifying {mode_name} Details...")
    if 'get_horse_details' not in namespace:
        print("❌ 'get_horse_details' function not found.")
        return None

    print(f"  Testing Horse ID: {horse_id}, Date: {race_date}")
    try:
        details = namespace['get_horse_details'](horse_id, race_date)
        if details:
            keys = list(details.keys())
            print(f"  ✅ Keys ({len(keys)}): {len(keys)} keys found")
            return keys
        else:
            print("  ⚠️ No details found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    return []

def main():
    # 1. Load Notebooks
    jra_basic_path = os.path.join(NOTEBOOK_DIR, 'Colab_JRA_Basic_v2.ipynb')
    nar_basic_path = os.path.join(NOTEBOOK_DIR, 'Colab_NAR_Basic_v2.ipynb')
    jra_details_path = os.path.join(NOTEBOOK_DIR, 'Colab_JRA_Details_v2.ipynb')
    nar_details_path = os.path.join(NOTEBOOK_DIR, 'Colab_NAR_Details_v2.ipynb')
    
    jra_basic_code = load_notebook_source(jra_basic_path)
    nar_basic_code = load_notebook_source(nar_basic_path)
    jra_details_code = load_notebook_source(jra_details_path)
    nar_details_code = load_notebook_source(nar_details_path)
    
    # 2. Syntax Check
    print("--- SYNTAX CHECK ---")
    check_syntax(jra_basic_code, "Colab_JRA_Basic_v2.ipynb")
    check_syntax(nar_basic_code, "Colab_NAR_Basic_v2.ipynb")
    check_syntax(jra_details_code, "Colab_JRA_Details_v2.ipynb")
    check_syntax(nar_details_code, "Colab_NAR_Details_v2.ipynb")

    # 3. Extract logic
    jra_basic_ns = extract_functions(jra_basic_code)
    nar_basic_ns = extract_functions(nar_basic_code)
    
    # 4. Basic CSV Columns Verification
    jra_ids = get_sampled_race_ids(is_nar=False)
    nar_ids = get_sampled_race_ids(is_nar=True)
    
    jra_cols, jra_samples = verify_jra_basic(jra_basic_ns, jra_ids)
    nar_cols, nar_samples = verify_nar_basic(nar_basic_ns, nar_ids)
    
    print("\n--- BASIC COLUMNS COMPARISON ---")
    if jra_cols and nar_cols:
        if jra_cols == nar_cols:
            print("✅ JRA and NAR Basic Columns MATCH PERFECTLY")
        else:
            print("❌ Columns MISMATCH")
            print(f"JRA only: {set(jra_cols) - set(nar_cols)}")
            print(f"NAR only: {set(nar_cols) - set(jra_cols)}")
            if len(jra_cols) == len(nar_cols):
                 diffs = [(i, a, b) for i, (a, b) in enumerate(zip(jra_cols, nar_cols)) if a != b]
                 if diffs:
                     print("⚠️ Order mismatch at indices:", diffs)
    
    # 5. Details Verification
    jra_details_ns = extract_functions(jra_details_code)
    nar_details_ns = extract_functions(nar_details_code)
    
    jra_details_keys = None
    
    if jra_samples:
        print(f"\n🔍 Verifying JRA Details on {len(jra_samples)} samples (approx 1 per year)...")
        for hid, date, yr in jra_samples:
            keys = verify_details_mode(jra_details_ns, hid, date, f"JRA ({yr})")
            if keys: jra_details_keys = keys
    else:
        print("⚠️ No JRA Basic samples to test Details.")

    nar_details_keys = None
    if nar_samples:
        print(f"\n🔍 Verifying NAR Details on {len(nar_samples)} samples (approx 1 per year)...")
        for hid, date, yr in nar_samples:
            keys = verify_details_mode(nar_details_ns, hid, date, f"NAR ({yr})")
            if keys: nar_details_keys = keys
    else:
        print("⚠️ No NAR Basic samples to test Details.")

    print("\n--- DETAILS COLUMNS COMPARISON ---")
    if jra_details_keys and nar_details_keys:
        s_jra = set(jra_details_keys)
        s_nar = set(nar_details_keys)
        
        if s_jra == s_nar:
             print("✅ JRA and NAR Details Keys MATCH")
        else:
             print("❌ Details Keys MISMATCH")
             print(f"JRA only: {s_jra - s_nar}")
             print(f"NAR only: {s_nar - s_jra}")

if __name__ == "__main__":
    main()
