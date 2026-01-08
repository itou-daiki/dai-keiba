#!/usr/bin/env python3
"""
一括スクレイピングノートブックの最適化ヘルパーセルのコメントを解除
"""

import json
from pathlib import Path

def uncomment_optimization_helpers(notebook_path):
    """
    最適化ヘルパーセルのコメントを解除
    """
    print(f"\n{'='*80}")
    print(f"🔧 修正: {Path(notebook_path).name}")
    print(f"{'='*80}\n")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    modified = False
    
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        
        source = ''.join(cell['source'])
        
        # 最適化ヘルパーセルを探す
        if '# --- Optimization Helpers' in source or 'deduplicate_in_chunks' in source:
            print(f"✅ セル{i}: 最適化ヘルパーセルを発見")
            
            # 全行がコメントアウトされているかチェック
            lines = source.split('\n')
            commented_lines = [l for l in lines if l.strip().startswith('#')]
            
            if len(commented_lines) > len(lines) * 0.8:  # 80%以上がコメント
                print(f"  ⚠️  ほぼ全てがコメントアウトされています")
                print(f"  🔧 コメントを解除中...")
                
                # コメントを解除
                new_lines = []
                for line in lines:
                    # "# " で始まる行のコメントを解除(ただしコメント行は保持)
                    if line.strip().startswith('# ') and not line.strip().startswith('# ---'):
                        # 実際のコードのコメントアウトを解除
                        if any(keyword in line for keyword in ['def ', 'import ', 'class ', 'return ', 'if ', 'for ', 'while ']):
                            new_lines.append(line.replace('# ', '', 1))
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                
                new_source = '\n'.join(new_lines)
                cell['source'] = [line + '\n' for line in new_source.split('\n')]
                if cell['source'] and cell['source'][-1] == '\n':
                    cell['source'][-1] = cell['source'][-1].rstrip('\n')
                
                modified = True
                print(f"  ✅ コメント解除完了")
            else:
                print(f"  ℹ️  既にアクティブです")
    
    if modified:
        # 保存
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        print(f"\n✅ 保存完了: {notebook_path}")
    else:
        print(f"\n✅ 修正不要")
    
    return modified

if __name__ == "__main__":
    print("🔧 最適化ヘルパーセルのコメント解除\n")
    
    notebooks = [
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_JRA_Scraping.ipynb",
        "/Users/itoudaiki/Program/dai-keiba/notebooks/Colab_NAR_Scraping.ipynb"
    ]
    
    modified_count = 0
    for nb_path in notebooks:
        if Path(nb_path).exists():
            if uncomment_optimization_helpers(nb_path):
                modified_count += 1
    
    print(f"\n{'='*80}")
    print(f"✅ 完了: {modified_count}/{len(notebooks)} ノートブックを修正")
    print(f"{'='*80}\n")
    
    if modified_count > 0:
        print("📝 次のステップ:")
        print("  1. Colabでノートブックを開く")
        print("  2. 最適化ヘルパーセルが実行可能になっていることを確認")
        print("  3. スクレイピング開始")
