#!/usr/bin/env python3
"""
NAR コーナー通過順の正しい順位計算
括弧内の同着を考慮
"""

import re

def parse_nar_corner_with_ties(corner_text):
    """
    NARのコーナー通過順を括弧(同着)を考慮してパース
    
    Args:
        corner_text: '3,(2,1),4' のような文字列
    
    Returns:
        dict: {馬番: 順位}
        例: '3,(2,1),4' → {'3': 1, '2': 2, '1': 2, '4': 4}
    """
    positions = {}
    
    if not corner_text:
        return positions
    
    # ハイフンをカンマに変換
    corner_text = corner_text.replace('-', ',')
    
    # 括弧で囲まれたグループと単独の馬を分離
    # '3,(2,1),4' → ['3', '(2,1)', '4']
    parts = []
    current = ''
    paren_depth = 0
    
    for char in corner_text:
        if char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            if current.strip():
                parts.append(current.strip())
            current = ''
        else:
            current += char
    
    if current.strip():
        parts.append(current.strip())
    
    # 各パートを処理
    current_position = 1
    
    for part in parts:
        if part.startswith('(') and part.endswith(')'):
            # 括弧内の馬(同着)
            horses_in_group = part[1:-1].split(',')
            for horse_num in horses_in_group:
                horse_num = horse_num.strip()
                if horse_num:
                    positions[horse_num] = str(current_position)
            # 次の順位は括弧内の馬数分進める
            current_position += len([h for h in horses_in_group if h.strip()])
        else:
            # 単独の馬
            horse_num = part.strip()
            if horse_num:
                positions[horse_num] = str(current_position)
                current_position += 1
    
    return positions

# テスト
if __name__ == "__main__":
    print("🧪 NAR コーナー通過順(同着考慮)テスト\n")
    print(f"{'='*80}\n")
    
    test_cases = [
        ("1,2,3,4", "通常"),
        ("3,(2,1),4", "2位同着"),
        ("(8,2),7,6,(5,3),1,4", "複数同着"),
        ("1-2-3-4", "ハイフン区切り"),
    ]
    
    for corner_text, description in test_cases:
        print(f"📊 {description}: '{corner_text}'")
        positions = parse_nar_corner_with_ties(corner_text)
        print(f"  結果: {positions}")
        
        # 順位順にソート
        sorted_horses = sorted(positions.items(), key=lambda x: int(x[1]))
        print(f"  順位順:")
        for horse, pos in sorted_horses:
            print(f"    馬番{horse}: {pos}位")
        print()
    
    print(f"{'='*80}")
    print("✅ テスト完了")
    
    # 具体例の検証
    print(f"\n📊 ユーザー指定の例:")
    print(f"  1コーナー: '1,2,3,4'")
    pos1 = parse_nar_corner_with_ties("1,2,3,4")
    print(f"    馬番4: {pos1.get('4', '?')}位 (期待値: 4位)")
    
    print(f"  2コーナー: '3,(2,1),4'")
    pos2 = parse_nar_corner_with_ties("3,(2,1),4")
    print(f"    馬番4: {pos2.get('4', '?')}位 (期待値: 4位)")
    print(f"    馬番2: {pos2.get('2', '?')}位 (期待値: 2位)")
    print(f"    馬番1: {pos2.get('1', '?')}位 (期待値: 2位)")
