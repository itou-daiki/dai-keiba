import json
import ast
import os
import sys

NOTEBOOKS = [
    'notebooks/Colab_JRA_Basic_v2.ipynb',
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Basic_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def check_syntax(filepath):
    print(f"🔍 Checking {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON Error: {e}")
        return False
    
    code_content = ""
    for cell in nb.get('cells', []):
        if cell['cell_type'] == 'code':
            # Join lines and ensure newline
            source = "".join(cell['source'])
            code_content += source + "\n"
    
    try:
        ast.parse(code_content)
        print("  ✅ Syntax OK")
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax Error: {e}")
        print(f"     Line {e.lineno}: {e.text.strip() if e.text else ''}")
        return False
    except Exception as e:
        print(f"  ❌ Unknown Error: {e}")
        return False

if __name__ == "__main__":
    success = True
    for nb in NOTEBOOKS:
        if os.path.exists(nb):
            if not check_syntax(nb):
                success = False
        else:
            print(f"⚠️ File not found: {nb}")
    
    if not success:
        sys.exit(1)
