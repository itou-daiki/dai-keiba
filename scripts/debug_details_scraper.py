import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
import datetime

# Mock Horses
JRA_HORSE_ID = "2019105219" # Equinox
JRA_RACE_DATE = "2023/11/26" # Japan Cup

NAR_HORSE_ID = "2020100412" 
NAR_RACE_DATE = "2020/07/30"

def debug_jra_details():
    print(f"\n🔍 DEBUGGING JRA DETAILS (Logic Check with MOCK HTML)")
    
    # MOCK HTML mimicking Netkeiba structure
    mock_html = """
    <html>
    <body>
    <table class="db_h_race_results nk_tb_common">
        <thead>
            <tr>
                <th>日付</th><th>開催</th><th>天気</th><th>R</th><th>レース名</th><th>映像</th>
                <th>頭数</th><th>枠番</th><th>馬番</th><th>オッズ</th><th>人気</th><th>着順</th>
                <th>騎手</th><th>斤量</th><th>距離</th><th>馬場</th><th>タイム</th><th>着差</th>
                <th>通過</th><th>ペース</th><th>上り</th><th>馬体重</th><th>勝ち馬(2着馬)</th><th>賞金</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>2023/11/26</td><td>5東京8</td><td>晴</td><td>12</td><td>ジャパンC(G1)</td><td></td>
                <td>18</td><td>1</td><td>2</td><td>1.3</td><td>1</td><td>1</td>
                <td>ルメール</td><td>58</td><td>芝2400</td><td>良</td><td>2:21.8</td><td>-0.7</td>
                <td>2-2-2-2</td><td>34.5-34.8</td><td>33.5</td><td>498(0)</td><td>(リバティアイランド)</td><td>50,000.0</td>
            </tr>
            <tr>
                <td>2022/12/25</td><td>5中山9</td><td>晴</td><td>11</td><td>有馬記念(G1)</td><td></td>
                <td>16</td><td>5</td><td>9</td><td>2.3</td><td>1</td><td>1</td>
                <td>ルメール</td><td>55</td><td>芝2500</td><td>良</td><td>2:32.4</td><td>-0.4</td>
                <td>9-9-6-4</td><td>35.0-35.2</td><td>35.4</td><td>498(+2)</td><td>(ボルドグフーシュ)</td><td>40,000.0</td>
            </tr>
        </tbody>
    </table>
    </body>
    </html>
    """
    
    try:
        soup = BeautifulSoup(mock_html, 'html.parser')
        
        # 1. Find Table
        table = soup.select_one("table.db_h_race_results")
        if not table:
             print("  ❌ 'table.db_h_race_results' NOT FOUND in Mock.")
             return
             
        # 2. Parse DF
        df = pd.read_html(io.StringIO(str(table)))[0]
        df = df.dropna(how='all')
        print(f"  Raw DF Shape: {df.shape}")
        
        # 3. Clean Columns
        # Verify logic: df.columns.astype(str).str.replace(r'\s+', '', regex=True)
        # Note: In HTML, '賞金' might have spaces or newlines?
        original_cols = df.columns.tolist()
        df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)
        print(f"  Cleaned Columns: {df.columns.tolist()}")
        
        if '日付' not in df.columns:
            print("  ❌ '日付' column extraction FAILED. Check column cleaning logic.")
            return

        # 4. Filter Logic
        # Notebook: df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
        df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
        
        print("\n  --- Checking Specific Logic ---")
        row = df.iloc[0] # Japan Cup Row
        
        # JRA Details Logic Checks
        # Distance parsing: re.search(r'(芝|ダ|障)(\d+)', dist_text)
        dist_text = str(getattr(row, '距離', ''))
        print(f"  Distance Raw: '{dist_text}'")
        match = re.search(r'(芝|ダ|障)(\d+)', dist_text)
        if match:
             print(f"  ✅ Distance Parsed: {match.group(1)} / {match.group(2)}")
        else:
             print(f"  ❌ Distance Parse Failed for '{dist_text}'")
             
        # Weight parsing: Just mapped to 'horse_weight'
        # Notebook: details[f'{prefix}_horse_weight'] = str(getattr(row, '馬体重', ''))
        # It does NOT split into weight/change in DETAILS (only Basic does that?).
        # Let's check spec.
        # Spec says "horse_weight" (7. horse_weight). 
        # If the user wants clean weight, Details might be just raw string.
        # But wait, looking at Colab_JRA_Details, it just takes raw.
        print(f"  Weight Raw: '{getattr(row, '馬体重', '')}'")
        
        # Jockey
        print(f"  Jockey Raw: '{getattr(row, '騎手', '')}'")

    except Exception as e:
        print(f"  ❌ Parsing Error: {e}")

def debug_nar_details():
    print(f"\n🔍 DEBUGGING NAR DETAILS (Logic Check with MOCK HTML)")
    # NAR Mock - similar
    mock_html_nar = """
    <html>
    <body>
    <table class="db_h_race_results nk_tb_common">
        <thead>
            <tr>
                <th>日付</th><th>開催</th><th>天気</th><th>R</th><th>レース名</th><th>映像</th>
                <th>頭数</th><th>枠番</th><th>馬番</th><th>オッズ</th><th>人気</th><th>着順</th>
                <th>騎手</th><th>斤量</th><th>距離</th><th>馬場</th><th>タイム</th><th>着差</th>
                <th>通過</th><th>ペース</th><th>上り</th><th>馬体重</th><th>勝ち馬(2着馬)</th><th>賞金</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>2020/07/30</td><td>5大井8</td><td>曇</td><td>11</td><td>ジャパンダート(G1)</td><td></td>
                <td>13</td><td>6</td><td>8</td><td>1.3</td><td>1</td><td>1</td>
                <td>御神本</td><td>57</td><td>ダ2000</td><td>重</td><td>2:05.9</td><td>-0.2</td>
                <td>2-2-2-1</td><td>36.5-37.0</td><td>38.0</td><td>510(+4)</td><td>(ダノンファラオ)</td><td>45,000.0</td>
            </tr>
        </tbody>
    </table>
    </body>
    </html>
    """
    
    try:
         soup = BeautifulSoup(mock_html_nar, 'html.parser')
         table = soup.select_one("table.db_h_race_results")
         
         if not table: 
             print("  ❌ NAR Table Not Found (Mock)")
             return
             
         df = pd.read_html(io.StringIO(str(table)))[0]
         df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)
         
         # Logic Check
         if '距離' in df.columns:
             row = df.iloc[0]
             dist_text = str(getattr(row, '距離', ''))
             match = re.search(r'(芝|ダ|障)(\d+)', dist_text)
             if match:
                 print(f"  ✅ NAR Distance Parsed: {match.group(1)} / {match.group(2)}")
             else:
                 print(f"  ❌ NAR Distance Parse Failed for '{dist_text}'")

    except Exception as e:
        print(f"  ❌ NAR Error: {e}")


if __name__ == "__main__":
    debug_jra_details()
    debug_nar_details()
