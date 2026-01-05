"""
馬の脚質（走法タイプ）分析

コーナー通過順や過去の成績から、馬の脚質を判定します。
- 逃げ (nige): 先頭で逃げる
- 先行 (senko): 前の方で競馬
- 差し (sashi): 中団から差す
- 追込 (oikomi): 後方から追い込む
"""

import numpy as np
import pandas as pd


def parse_corner_position(corner_str):
    """
    コーナー通過順から位置を抽出

    Args:
        corner_str (str): "1-1-1-1" or "10-10-8-5" など

    Returns:
        list: [1, 1, 1, 1] or [10, 10, 8, 5] など
    """
    if not isinstance(corner_str, str):
        return []

    try:
        positions = [int(p) for p in corner_str.split('-')]
        return positions
    except:
        return []


def classify_run_style_from_position(avg_position, total_horses=18):
    """
    平均通過順位から脚質を判定

    Args:
        avg_position (float): 平均通過順位
        total_horses (int): 出走頭数（デフォルト18頭）

    Returns:
        str: 'nige', 'senko', 'sashi', 'oikomi'
    """
    if avg_position <= 2:
        return 'nige'  # 逃げ
    elif avg_position <= total_horses * 0.3:
        return 'senko'  # 先行
    elif avg_position <= total_horses * 0.7:
        return 'sashi'  # 差し
    else:
        return 'oikomi'  # 追込


def get_run_style_from_corners(corner_str, total_horses=18):
    """
    単一レースのコーナー通過順から脚質を判定

    Args:
        corner_str (str): "1-1-1-1" など
        total_horses (int): 出走頭数

    Returns:
        str: 'nige', 'senko', 'sashi', 'oikomi'
    """
    positions = parse_corner_position(corner_str)

    if not positions:
        return 'unknown'

    # 最初のコーナー位置を重視（序盤の位置取りが重要）
    avg_position = np.mean(positions[:2]) if len(positions) >= 2 else positions[0]

    return classify_run_style_from_position(avg_position, total_horses)


def analyze_horse_run_style(past_corners, past_total_horses=None):
    """
    過去複数レースのコーナー通過順から、馬の主な脚質を判定

    Args:
        past_corners (list): ['1-1-1-1', '2-2-2-1', ...] 過去のコーナー通過順リスト
        past_total_horses (list): [18, 16, ...] 各レースの出走頭数（オプション）

    Returns:
        dict: {
            'primary_style': 'senko',  # 主な脚質
            'style_distribution': {'nige': 0.2, 'senko': 0.6, 'sashi': 0.2, 'oikomi': 0.0},
            'avg_early_position': 3.5,  # 平均序盤位置
            'avg_late_position': 2.8,  # 平均終盤位置
            'position_change': -0.7,  # 位置変化（マイナスは前に行く）
        }
    """
    if not past_corners:
        return {
            'primary_style': 'unknown',
            'style_distribution': {},
            'avg_early_position': np.nan,
            'avg_late_position': np.nan,
            'position_change': np.nan,
        }

    # デフォルトの出走頭数
    if past_total_horses is None:
        past_total_horses = [18] * len(past_corners)

    # 各レースの脚質を判定
    styles = []
    early_positions = []
    late_positions = []

    for corner_str, total_horses in zip(past_corners, past_total_horses):
        positions = parse_corner_position(corner_str)

        if positions:
            # 序盤位置（最初のコーナー）
            early_pos = positions[0]
            early_positions.append(early_pos)

            # 終盤位置（最後のコーナー）
            late_pos = positions[-1]
            late_positions.append(late_pos)

            # 脚質判定
            style = get_run_style_from_corners(corner_str, total_horses)
            styles.append(style)

    # 脚質の分布を計算
    style_counts = {}
    for style in styles:
        style_counts[style] = style_counts.get(style, 0) + 1

    total = len(styles)
    style_distribution = {s: count / total for s, count in style_counts.items()}

    # 最も多い脚質を主な脚質とする
    primary_style = max(style_counts, key=style_counts.get) if style_counts else 'unknown'

    # 平均位置
    avg_early = np.mean(early_positions) if early_positions else np.nan
    avg_late = np.mean(late_positions) if late_positions else np.nan

    # 位置変化（マイナスは前に行く、プラスは下がる）
    position_change = avg_late - avg_early if not np.isnan(avg_early) and not np.isnan(avg_late) else np.nan

    return {
        'primary_style': primary_style,
        'style_distribution': style_distribution,
        'avg_early_position': avg_early,
        'avg_late_position': avg_late,
        'position_change': position_change,
    }


def get_run_style_code(run_style):
    """
    脚質を数値コードに変換

    Args:
        run_style (str): 'nige', 'senko', 'sashi', 'oikomi'

    Returns:
        int: 1=逃げ, 2=先行, 3=差し, 4=追込, 0=不明
    """
    mapping = {
        'nige': 1,
        'senko': 2,
        'sashi': 3,
        'oikomi': 4,
        'unknown': 0,
    }
    return mapping.get(run_style, 0)


def calculate_run_style_consistency(past_corners):
    """
    脚質の一貫性を計算

    Args:
        past_corners (list): 過去のコーナー通過順リスト

    Returns:
        float: 0.0-1.0 の一貫性スコア（1.0が完全に一貫）
    """
    analysis = analyze_horse_run_style(past_corners)

    if not analysis['style_distribution']:
        return 0.0

    # 最も多い脚質の割合を一貫性とする
    return max(analysis['style_distribution'].values())


def is_versatile_horse(past_corners):
    """
    器用な馬（複数の脚質に対応できる）かどうかを判定

    Args:
        past_corners (list): 過去のコーナー通過順リスト

    Returns:
        bool: True なら器用な馬
    """
    analysis = analyze_horse_run_style(past_corners)

    if not analysis['style_distribution']:
        return False

    # 2つ以上の脚質が30%以上あれば器用
    significant_styles = [s for s, ratio in analysis['style_distribution'].items() if ratio >= 0.3]

    return len(significant_styles) >= 2


if __name__ == "__main__":
    # テスト
    print("=" * 60)
    print("脚質分析テスト")
    print("=" * 60)

    # テストデータ
    test_cases = [
        {
            'name': '逃げ馬',
            'corners': ['1-1-1-1', '1-1-2-3', '2-1-1-1'],
        },
        {
            'name': '先行馬',
            'corners': ['3-3-2-1', '4-4-3-2', '3-3-3-3'],
        },
        {
            'name': '差し馬',
            'corners': ['8-8-6-3', '10-9-7-4', '9-8-5-2'],
        },
        {
            'name': '追込馬',
            'corners': ['15-15-12-5', '14-14-10-3', '16-15-11-6'],
        },
    ]

    for case in test_cases:
        print(f"\n【{case['name']}】")
        result = analyze_horse_run_style(case['corners'])

        print(f"  主な脚質: {result['primary_style']}")
        print(f"  脚質分布: {result['style_distribution']}")
        print(f"  序盤平均位置: {result['avg_early_position']:.1f}")
        print(f"  終盤平均位置: {result['avg_late_position']:.1f}")
        print(f"  位置変化: {result['position_change']:+.1f}")
        print(f"  一貫性: {calculate_run_style_consistency(case['corners']):.2f}")
        print(f"  器用: {is_versatile_horse(case['corners'])}")

    print("\n✅ 脚質判定ロジックの実装完了")
