
import json

def diagnose():
    nb_path = 'notebooks/NAR_Scraper.ipynb'
    try:
        with open(nb_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        return

    for i, cell in enumerate(nb['cells']):
        source = cell['source']
        # Check if it matches the user's report
        full_text = "".join(source)
        if "5. 血統データの補完" in full_text:
            print(f"=== Found Cell {i} ===")
            print(f"Cell Type: {cell['cell_type']}")
            print("Raw Source List:")
            print(source)
            print("---")
            print("String Repr:")
            for line in source:
                print(repr(line))
            break

if __name__ == "__main__":
    diagnose()
