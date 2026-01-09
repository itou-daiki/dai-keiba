#!/usr/bin/env python3
"""
コーナー通過順の抽出・加工関数
LightGBM学習用に各コーナーの順位を個別カラムとして抽出
"""

import re

def extract_corner_positions(corner_text):
    """
    コーナー通過順テキストから各コーナーの順位を抽出
    
    Args:
        corner_text: "6-5-5-3" のような文字列
    
    Returns:
        dict: {
            'corner_1': '6',
            'corner_2': '5',
            'corner_3': '5',
            'corner_4': '3'
        }
        コーナーがない場合は空文字列
    """
    result = {
        'corner_1': '',
        'corner_2': '',
        'corner_3': '',
        'corner_4': ''
    }
    
    if not corner_text or not isinstance(corner_text, str):
        return result
    
    # ハイフンで分割
    positions = corner_text.strip().split('-')
    
    # 各コーナーの順位を設定
    for i, pos in enumerate(positions[:4], 1):  # 最大4コーナー
        result[f'corner_{i}'] = pos.strip()
    
    return result

# テスト
if __name__ == "__main__":
    print("🧪 コーナー通過順抽出テスト\n")
    print(f"{'='*80}\n")
    
    test_cases = [
        ("6-5-5-3", "4コーナー(芝2500m)"),
        ("3-3-2", "3コーナー(芝1600m)"),
        ("1-1", "2コーナー(ダート1000m)"),
        ("", "データなし"),
        (None, "None"),
    ]
    
    for corner_text, description in test_cases:
        print(f"📊 {description}")
        print(f"  入力: '{corner_text}'")
        
        result = extract_corner_positions(corner_text)
        
        print(f"  出力:")
        for key, value in result.items():
            status = "✅" if value else "⚠️"
            print(f"    {status} {key}: '{value}'")
        print()
    
    print(f"{'='*80}")
    print("✅ テスト完了")
