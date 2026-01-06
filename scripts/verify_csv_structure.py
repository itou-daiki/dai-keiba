import csv
import sys

filename = 'data/raw/database_nar.csv'
expected_cols = 95
error_count = 0
row_count = 0

print(f"Checking {filename} for structure...")

try:
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        if len(header) != expected_cols:
            print(f"CRITICAL: Header has {len(header)} columns, expected {expected_cols}")
            sys.exit(1)
            
        print(f"Header OK: {len(header)} columns.")
        print(f"Last column name: '{header[-1]}'")

        for i, row in enumerate(reader, start=1):
            row_count += 1
            if len(row) != expected_cols:
                error_count += 1
                if error_count <= 10: # limit output
                    print(f"Row {i} ERROR: Found {len(row)} columns. Content: {row}")
            
            # content check (simple heuristic)
            # Last column 'bms' should be a name (string).
            # If it looks like a date (YYYY/MM/DD) or small float (odds), it's likely a shift.
            last_val = row[-1]
            # Check for pure numbers (odds/weight) or dates
            if len(last_val) > 0:
                # Is it a date? 202X/
                if '/' in last_val and last_val[:4].isdigit():
                     print(f"Row {i} WARNING: Last column looks like a date: '{last_val}'. Possible shift.")
                     error_count += 1
                # Is it a small number? (Odds usually < 1000)
                elif last_val.replace('.','').isdigit():
                     try:
                         val = float(last_val)
                         # Horse names can be numbers (e.g. "Ten Points"), but rare. 
                         # Verify if it really looks like a metric.
                         if val < 500: # Arbitrary threshold, BMS names unlikely to be "4.5" or "12"
                             print(f"Row {i} WARNING: Last column looks like a number: '{last_val}'. Possible shift.")
                             error_count += 1
                     except: pass

    print("-" * 30)
    print(f"Scan Complete.")
    print(f"Total Rows: {row_count}")
    print(f"Misaligned/Suspicious Rows: {error_count}")
    
    if error_count == 0:
        print("✅ ALL ROWS ALIGNED. Last column ('bms') appears valid.")
    else:
        print("❌ STRUCTURAL ERRORS OR SUSPICIOUS CONTENT FOUND.")

except Exception as e:
    print(f"File Error: {e}")
