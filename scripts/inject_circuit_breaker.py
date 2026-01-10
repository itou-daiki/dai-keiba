import json
import os

NOTEBOOKS = [
    'notebooks/Colab_JRA_Details_v2.ipynb',
    'notebooks/Colab_NAR_Details_v2.ipynb'
]

def inject_circuit_breaker(filepath):
    print(f"🔧 Injecting Circuit Breaker into {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = json.load(f)
        
        modified = False
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'code':
                new_source = []
                for line in cell['source']:
                    # Target the chunk saving block
                    if "if len(buffer) >= chunk_size or (i == len(df_target) - 1 and buffer):" in line:
                         # Insert Circuit Breaker Logic
                         block = [
                             "        # --- Circuit Breaker (Safety Stop) ---\n",
                             "        if len(buffer) >= 10:\n",
                             "             valid_count = sum(1 for d in buffer if d.get('father', '').strip() != '')\n",
                             "             success_rate = valid_count / len(buffer)\n",
                             "             if success_rate < 0.2:\n",
                             "                 print(f\"\\n⚠️ CIRCUIT BREAKER TRIGGERED: Success rate {success_rate:.1%} is below threshold.\")\n",
                             "                 print(\"⛔ Stopping execution to prevent empty data accumulation (likely IP Ban).\")\n",
                             "                 # Save what we have so far (optional, but maybe risky if all empty)\n",
                             "                 # Raise exception to stop loop\n",
                             "                 raise RuntimeError(\"Circuit Breaker: High failure rate detected.\")\n",
                             "        # -------------------------------------\n",
                             "\n"
                         ]
                         new_source.extend(block)
                         new_source.append(line)
                         modified = True
                    else:
                        new_source.append(line)
                
                if len(new_source) != len(cell['source']):
                    cell['source'] = new_source
                    modified = True

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"🛡️  Circuit Breaker Injected into {filepath}")
        else:
            print(f"⚠️ Insertion point not found in {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

if __name__ == "__main__":
    for nb in NOTEBOOKS:
        inject_circuit_breaker(nb)
