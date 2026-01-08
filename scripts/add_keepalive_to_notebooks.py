#!/usr/bin/env python3
"""
すべてのColabノートブックにKeep-Alive(アイドルタイムアウト回避)セルを追加
"""

import json
from pathlib import Path

def add_keepalive_cell(notebook_path: str):
    """
    ノートブックの最初にKeep-Aliveセルを追加
    """
    print(f"\n{'='*80}")
    print(f"🔧 Adding Keep-Alive to: {Path(notebook_path).name}")
    print(f"{'='*80}\n")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Keep-Aliveセルの内容
    keepalive_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 🛡️ Keep-Alive (アイドルタイムアウト回避)\n",
            "from IPython.display import display, Javascript\n",
            "\n",
            "display(Javascript('''\n",
            "function ClickConnect(){\n",
            "    console.log(\"Keep-alive: Working\");\n",
            "    var buttons = document.querySelectorAll(\"colab-connect-button\");\n",
            "    buttons.forEach(function(btn){\n",
            "        btn.click();\n",
            "    });\n",
            "}\n",
            "setInterval(ClickConnect, 60000);\n",
            "console.log(\"Keep-alive script started - clicks every 60 seconds\");\n",
            "'''))\n",
            "\n",
            "print(\"✅ Keep-alive activated (auto-clicks every 60 seconds)\")\n",
            "print(\"💡 This prevents idle timeout during long scraping sessions\")"
        ]
    }
    
    # 既にKeep-Aliveセルがあるかチェック
    has_keepalive = False
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if 'Keep-Alive' in source or 'ClickConnect' in source:
                has_keepalive = True
                print("  ℹ️  Keep-Alive cell already exists")
                break
    
    if not has_keepalive:
        # Drive Mountセルの後に挿入(通常はセル1)
        insert_position = 1
        
        # Drive Mountセルを探す
        for i, cell in enumerate(nb['cells']):
            if cell['cell_type'] == 'code':
                source = ''.join(cell['source'])
                if 'drive.mount' in source:
                    insert_position = i + 1
                    break
        
        # セルを挿入
        nb['cells'].insert(insert_position, keepalive_cell)
        print(f"  ✅ Keep-Alive cell inserted at position {insert_position}")
        
        # 保存
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        
        print(f"  ✅ Saved: {notebook_path}")
        return True
    
    return False

if __name__ == "__main__":
    print("🛡️ Adding Keep-Alive to all Colab notebooks...\n")
    
    notebooks = [
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_ID_Fetcher.ipynb",
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Basic.ipynb",
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Scraping.ipynb",
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Basic.ipynb",
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Scraping.ipynb"
    ]
    
    modified_count = 0
    for nb_path in notebooks:
        if Path(nb_path).exists():
            if add_keepalive_cell(nb_path):
                modified_count += 1
        else:
            print(f"⚠️  Not found: {nb_path}")
    
    print(f"\n{'='*80}")
    print(f"✅ Complete: {modified_count}/{len(notebooks)} notebooks modified")
    print(f"{'='*80}\n")
    
    print("📝 Usage:")
    print("  1. Open any Colab notebook")
    print("  2. Run the Keep-Alive cell (first code cell)")
    print("  3. Run the rest of the notebook normally")
    print("  4. The script will auto-click every 60 seconds to prevent idle timeout")
    print("\n💡 You can now safely leave the notebook running for hours!")
