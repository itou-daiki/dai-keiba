import pandas as pd
import os

def fix_database():
    target_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw', 'database.csv')
    
    if not os.path.exists(target_file):
        print(f"Error: {target_file} not found.")
        return

    print(f"Reading {target_file}...")
    try:
        # Read the file
        df = pd.read_csv(target_file)
        
        # Check for duplicated columns (with spaces)
        # Check for duplicated columns (with spaces)
        columns_to_fix = {
            'コーナー通過順': 'コーナー 通過順',
            '馬体重(増減)': '馬体重 (増減)'
        }
        
        changed = False
        for bad_col, good_col in columns_to_fix.items():
            if bad_col in df.columns:
                print(f"Found '{bad_col}', merging into '{good_col}'...")
                # If good_col doesn't exist, create it.
                if good_col not in df.columns:
                    df[good_col] = df[bad_col]
                else:
                    # If good_col is empty/null, calculate fill
                    if df[good_col].isna().all():
                        df[good_col] = df[bad_col]
                    else:
                        # If good_col has data, assume it's main, but fillna with bad_col
                        df[good_col] = df[good_col].fillna(df[bad_col])
                
                # Drop the bad column
                df.drop(columns=[bad_col], inplace=True)
                changed = True
        
        if changed:
            print(f"Saving fixed data to {target_file}...")
            df.to_csv(target_file, index=False)
            print("Done.")
        else:
            print("No column fixes needed.")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    fix_database()
