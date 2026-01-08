import json
import ast
import sys

def check_notebook(path):
    print(f"Checking {path}...")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        return False

    all_valid = True
    cells = nb.get('cells', [])
    for i, cell in enumerate(cells):
        if cell.get('cell_type') == 'code':
            source_lines = cell.get('source', [])
            source_code = "".join(source_lines)
            
            # Skip empty cells
            if not source_code.strip():
                continue
                
            # Skip cells starting with %% (magic commands) as they might fail standard python syntax check
            # But we can try to skip the magic line
            clean_lines = []
            for line in source_lines:
                if line.strip().startswith('%%') or line.strip().startswith('!'):
                    clean_lines.append(f"# {line}") # Comment out magic
                else:
                    clean_lines.append(line)
            
            clean_code = "".join(clean_lines)

            try:
                ast.parse(clean_code)
            except SyntaxError as e:
                print(f"❌ Syntax Error in Cell {i+1}:")
                print(f"  Line {e.lineno}: {e.text.strip() if e.text else ''}")
                print(f"  Msg: {e.msg}")
                all_valid = False
            except Exception as e:
                print(f"❌ Error checking Cell {i+1}: {e}")
                all_valid = False
    
    if all_valid:
        print(f"✅ {path}: No syntax errors found.")
        return True
    else:
        print(f"⚠️ {path}: Issues found.")
        return False

if __name__ == "__main__":
    files = [
        'notebooks/Colab_JRA_Scraping.ipynb',
        'notebooks/Colab_NAR_Scraping.ipynb'
    ]
    for f in files:
        check_notebook(f)
