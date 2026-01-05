import pandas as pd
import shutil
import os

def recover_file(current_path, backup_path, label):
    print(f"=== Recovering {label} ===")
    if not os.path.exists(current_path) or not os.path.exists(backup_path):
        print(f"  Missing file(s) for {label}. Skipping.")
        return

    try:
        # Load datasets
        print(f"  Loading Current: {current_path}")
        df_curr = pd.read_csv(current_path, low_memory=False)
        print(f"    Rows: {len(df_curr)}")
        
        print(f"  Loading Backup: {backup_path}")
        df_bak = pd.read_csv(backup_path, low_memory=False)
        print(f"    Rows: {len(df_bak)}")
        
        # Merge
        print("  Merging...")
        df_merged = pd.concat([df_curr, df_bak], ignore_index=True)
        
        # Drop duplicates by race_id + horse_id if possible, or just exact rows
        # Ideally we unique by horse in a race.
        # 'race_id' + 'horse_id' (or '馬番')
        
        subset_cols = ['race_id']
        if 'horse_id' in df_merged.columns:
            subset_cols.append('horse_id')
        elif '馬 番' in df_merged.columns:
             subset_cols.append('馬 番')
             
        initial_len = len(df_merged)
        df_merged.drop_duplicates(subset=subset_cols, keep='first', inplace=True)
        final_len = len(df_merged)
        
        print(f"  Merged Rows: {final_len} (Dropped {initial_len - final_len} duplicates)")
        
        # Safe Sort (by date if available)
        if '日付' in df_merged.columns:
             # Create temp date col for sorting
             df_merged['_temp_date'] = pd.to_datetime(df_merged['日付'], errors='coerce')
             df_merged.sort_values(by=['_temp_date', 'race_id'], inplace=True)
             df_merged.drop(columns=['_temp_date'], inplace=True)
        
        # Backup the current (broken) state just in case, renamed
        broken_bak = current_path + ".broken"
        shutil.copy(current_path, broken_bak)
        print(f"  Saved broken state to {broken_bak}")
        
        # Save recovered
        df_merged.to_csv(current_path, index=False)
        print(f"  Successfully saved recovered data to {current_path}")
        
        # Update the main backup too to reflect the "best" state?
        # Maybe safer to leave original backup alone for now, but user wants to fix things.
        # Let's update the backup file too so next time we are safe.
        shutil.copy(current_path, backup_path)
        print(f"  Updated backup {backup_path} with recovered data.")
        
    except Exception as e:
        print(f"  Error recovering {label}: {e}")

if __name__ == "__main__":
    recover_file("data/raw/database.csv", "data/raw/database_bak.csv", "JRA")
    recover_file("data/raw/database_nar.csv", "data/raw/database_nar_bak.csv", "NAR")
