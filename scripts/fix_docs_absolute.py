import json
import os

NOTEBOOK_DIR = '/Users/itoudaiki/Program/dai-keiba/notebooks'

NEW_DOC_SOURCE_JRA = [
    "# 🏇 JRA 基本情報スクレイピング (Stage 1/2) v2\n",
    "\n",
    "## 📊 取得データ\n",
    "- **32カラム**: 日付、会場、レース番号、レース名、重賞、コースタイプ、距離、回り、天候、馬場状態、着順、枠、馬番、馬名、性齢、斤量、騎手、タイム、着差、人気、単勝オッズ、後3F、corner_1, corner_2, corner_3, corner_4, 厩舎, 調教師, 馬体重, 増減, race_id, horse_id\n",
    "\n",
    "## ✅ 改善点\n",
    "- メタデータ抽出を確実に\n",
    "- カラムズレを完全に防止\n",
    "- データ検証を実装\n",
    "\n",
    "## 🚀 次のステップ\n",
    "Stage 2で馬履歴・血統データを取得"
]

NEW_DOC_SOURCE_NAR = [
    "# 🏇 NAR 基本情報スクレイピング (Stage 1/2) v2\n",
    "\n",
    "## 📊 取得データ\n",
    "- **32カラム**: 日付、会場、レース番号、レース名、重賞、コースタイプ、距離、回り、天候、馬場状態、着順、枠、馬番、馬名、性齢、斤量、騎手、タイム、着差、人気、単勝オッズ、後3F、corner_1, corner_2, corner_3, corner_4, 厩舎, 調教師, 馬体重, 増減, race_id, horse_id\n",
    "\n",
    "## ✅ 改善点\n",
    "- メタデータ抽出を確実に\n",
    "- カラムズレを完全に防止\n",
    "- データ検証を実装\n",
    "\n",
    "## 🚀 次のステップ\n",
    "Stage 2で馬履歴・血統データを取得"
]

def fix_docs_absolute(filename, new_source):
    filepath = os.path.join(NOTEBOOK_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'markdown':
                source_str = "".join(cell['source'])
                # Check for JRA or NAR header
                if "# 🏇 JRA 基本情報スクレイピング" in source_str or "# 🏇 NAR 基本情報スクレイピング" in source_str:
                     cell['source'] = new_source
                     modified = True
                     print(f"  ✅ Replaced Documentation Cell in {filename}")
                     break # Only one such cell expected
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"💾 Saved updated docs for {filename}")
        else:
            print(f"⚠️ Header cell not found in {filename}")
            
    except Exception as e:
        print(f"❌ Error updating {filename}: {e}")

if __name__ == "__main__":
    fix_docs_absolute('Colab_JRA_Basic_v2.ipynb', NEW_DOC_SOURCE_JRA)
    fix_docs_absolute('Colab_NAR_Basic_v2.ipynb', NEW_DOC_SOURCE_NAR)
