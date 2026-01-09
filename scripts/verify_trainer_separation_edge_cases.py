
# Verification Script for Trainer Separation Logic

def split_stable_trainer_logic(text):
    if not text: return "", ""
    text = text.strip()
    
    # Logic extracted from auto_scraper.py / refactor_notebooks.py
    
    # 1. Newline Check (JRA style)
    if '\n' in text:
        parts = [p for p in text.replace('\n', ' ').split() if p.strip()]
        if len(parts) >= 2:
            return parts[0], parts[-1]
        elif len(parts) == 1:
            text = parts[0] # Fallthrough to next check
    
    # 2. Affiliates List Check (NAR/Combined style)
    affiliates = ["北海道", "岩手", "水沢", "盛岡", "浦和", "船橋", "大井", "川崎", 
                  "金沢", "笠松", "愛知", "名古屋", "兵庫", "園田", "姫路", "高知", "佐賀",
                  "美浦", "栗東", "JRA", "地方", "海外", "仏国", "米国", "英", "香港", "豪州"]
    
    stable_part = ""
    trainer_part = text
    
    for aff in affiliates:
        if text.startswith(aff):
            stable_part = aff
            trainer_part = text[len(aff):].strip()
            return stable_part, trainer_part
            
    # 3. Fallback: No affiliation found
    # Current Default: All goes to Trainer, Stable is empty
    return "", text

def run_tests():
    test_cases = [
        ("美浦\n\n青木", "JRA Standard (Newline)"),
        ("北海道田中淳司", "NAR Standard (Prefix)"),
        ("田中淳司", "No Stable (Only Name)"),
        ("仏国ファーブル", "Foreign (Prefix)"),
        ("米国B.バファート", "Foreign (Prefix)"),
        ("謎国正体不明", "Unknown Stable"),
        ("", "Empty"),
        ("栗東", "Only Stable?"),
    ]
    
    print(f"{'Input':<20} | {'Stable':<10} | {'Trainer':<15} | {'Note'}")
    print("-" * 60)
    
    for inp, note in test_cases:
        formatted_inp = inp.replace('\n', '\\n')
        s, t = split_stable_trainer_logic(inp)
        print(f"{formatted_inp:<20} | {s:<10} | {t:<15} | {note}")

if __name__ == "__main__":
    run_tests()
