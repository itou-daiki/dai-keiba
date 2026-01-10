import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Basic_v2.ipynb',
    'notebooks/Colab_NAR_Basic_v2.ipynb',
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def update_headers(filepath):
    print(f"📝 Updating Header for {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        # New Definitions
        # Basic: 32 columns
        # Details: 70 vars (History + Pedigree)
        
        is_basic = "Basic" in filepath
        is_jra = "JRA" in filepath
        
        header_text = ""
        if is_basic:
            system_name = "JRA" if is_jra else "NAR"
            header_text = f"# {system_name} Basic Scraper v2\n\n- **取得対象**: {system_name}のレース結果基本テーブル\n- **カラム数**: 32カラム\n  - 日付, 会場, レース番号, レース名, 重賞, コースタイプ, 距離, 回り, 天候, 馬場状態, 着順, 枠, 馬番, 馬名, 性齢, 斤量, 騎手, タイム, 着差, 人気, 単勝オッズ, 後3F, corner_1, corner_2, corner_3, corner_4, 厩舎, 調教師, 馬体重, 増減, race_id, horse_id\n"
        else:
            system_name = "JRA Details" if is_jra else "NAR Details"
            header_text = f"# {system_name} Scraper v2\n\n- **取得対象**: 競走馬の詳細データ（過去走、血統）\n- **主な変更点**:\n  - `/horse/result/` (戦績) と `/horse/ped/` (血統) のDual URL取得\n  - 過去5走のデータ (日付, 着順, タイム... コース, 天候, オッズ)\n  - 馬体重の分割 (`_horse_weight`, `_weight_change`)\n  - 騎手名のフルネーム化\n  - 血統情報 (`father`, `mother`, `bms`)\n- **取得変数**: 計70個\n"

        for cell in nb['cells']:
            if cell['cell_type'] == 'markdown':
                # Assuming the first markdown cell is the header
                # We can check content to be sure "Scraper v2"
                source_str = "".join(cell['source'])
                if "Scraper" in source_str or "# " in source_str:
                    # Replace it
                    cell['source'] = [header_text]
                    modified = True
                    print(f"  Updated header in {filepath}")
                    break # Only update the first one

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved Header Update for {filepath}")
        else:
            print(f"⚠️ Header not found/updated for {filepath}")

    except Exception as e:
        print(f"❌ Error updating {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        update_headers(nb)
