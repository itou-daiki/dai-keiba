#!/usr/bin/env python3
"""
最終コーナーから逆順に抽出するロジックのテスト
"""

def extract_corners_reverse(corner_text, is_jra=True):
    """
    コーナー通過順を最終から逆順に抽出
    
    Args:
        corner_text: JRA='6-5-5-3', NAR='8,2,7,6-5,3,1,4'など
        is_jra: JRAかNARか
    
    Returns:
        dict: {
            'corner_1': 最終コーナー,
            'corner_2': 最終-1コーナー,
            'corner_3': 最終-2コーナー,
            'corner_4': 最終-3コーナー
        }
    """
    result = {
        'corner_1': '',  # 最終コーナー
        'corner_2': '',  # 最終-1
        'corner_3': '',  # 最終-2
        'corner_4': '',  # 最終-3
    }
    
    if not corner_text:
        return result
    
    if is_jra:
        # JRA: ハイフン区切り
        positions = corner_text.split('-')
        # 逆順に格納
        for i, pos in enumerate(reversed(positions)):
            if i < 4:
                result[f'corner_{i+1}'] = pos.strip()
    
    return result

# テスト
if __name__ == "__main__":
    print("🧪 逆順コーナー抽出テスト\n")
    print(f"{'='*80}\n")
    
    test_cases = [
        ("6-5-5-3", "4コーナーレース(芝2500m)"),
        ("3-3-2", "3コーナーレース(芝1600m)"),
        ("1-1", "2コーナーレース(ダート1000m)"),
    ]
    
    for corner_text, description in test_cases:
        print(f"📊 {description}")
        print(f"  入力: '{corner_text}'")
        
        result = extract_corners_reverse(corner_text, is_jra=True)
        
        print(f"  出力(逆順):")
        for key, value in result.items():
            status = "✅" if value else "⚠️"
            meaning = {
                'corner_1': '最終コーナー',
                'corner_2': '最終-1',
                'corner_3': '最終-2',
                'corner_4': '最終-3'
            }[key]
            print(f"    {status} {key} ({meaning}): '{value}'")
        print()
    
    print(f"{'='*80}")
    print("✅ テスト完了")
    
    print(f"\n📊 検証:")
    print("  4コーナーレース: corner_1=4コーナー, corner_2=3コーナー, corner_3=2コーナー, corner_4=1コーナー")
    print("  3コーナーレース: corner_1=3コーナー, corner_2=2コーナー, corner_3=1コーナー, corner_4=(空)")
    print("  2コーナーレース: corner_1=2コーナー, corner_2=1コーナー, corner_3=(空), corner_4=(空)")
    print("\n✅ corner_1は常に最終コーナー(ゴール直前)を表す")
