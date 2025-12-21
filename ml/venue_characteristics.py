"""
競馬場別のコース特性データ

各競馬場の詳細な特性を定義し、馬の適性判定に使用します。
"""

# ====================================================================
# 中央競馬（JRA）の会場特性
# ====================================================================

JRA_VENUE_CHARACTERISTICS = {
    '東京': {
        'track_type': 'left',  # 左回り
        'turf_straight': 525.9,  # 芝直線距離(m)
        'dirt_straight': 501.6,  # ダート直線距離(m)
        'track_width': 'wide',  # コース幅（wide/medium/narrow）
        'corners': 4,  # コーナー数
        'slope': 'flat',  # 高低差（flat/up-down/steep）
        'turf_surface': 'firm',  # 芝質（firm/soft/mixed）
        'dirt_surface': 'deep',  # ダート質（deep/shallow/mixed）
        'run_style_bias': {  # 脚質有利度（1.0が標準）
            'nige': 0.9,  # 逃げ
            'senko': 1.0,  # 先行
            'sashi': 1.1,  # 差し
            'oikomi': 1.2,  # 追込
        },
        'distance_specialty': {  # 得意距離帯
            'sprint': 0.9,  # 短距離（~1400m）
            'mile': 1.1,  # マイル（1400-1800m）
            'intermediate': 1.2,  # 中距離（1800-2400m）
            'long': 1.0,  # 長距離（2400m~）
        },
        'outer_track_advantage': 1.1,  # 外枠有利度
    },

    '中山': {
        'track_type': 'right',
        'turf_straight': 310.0,
        'dirt_straight': 308.0,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'steep',  # 急坂あり
        'turf_surface': 'firm',
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.2,  # 逃げ有利（直線短い）
            'senko': 1.1,
            'sashi': 0.9,
            'oikomi': 0.8,  # 追込不利
        },
        'distance_specialty': {
            'sprint': 1.1,
            'mile': 1.0,
            'intermediate': 1.0,
            'long': 0.9,
        },
        'outer_track_advantage': 0.9,  # 内枠有利
    },

    '阪神': {
        'track_type': 'right',
        'turf_straight': 473.6,
        'dirt_straight': 352.5,
        'track_width': 'wide',
        'corners': 4,
        'slope': 'up-down',
        'turf_surface': 'firm',
        'dirt_surface': 'deep',
        'run_style_bias': {
            'nige': 0.95,
            'senko': 1.05,
            'sashi': 1.1,
            'oikomi': 1.0,
        },
        'distance_specialty': {
            'sprint': 1.0,
            'mile': 1.1,
            'intermediate': 1.1,
            'long': 0.9,
        },
        'outer_track_advantage': 1.05,
    },

    '京都': {
        'track_type': 'right',
        'turf_straight': 403.7,
        'dirt_straight': 329.2,
        'track_width': 'wide',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': 'firm',
        'dirt_surface': 'mixed',
        'run_style_bias': {
            'nige': 1.0,
            'senko': 1.05,
            'sashi': 1.05,
            'oikomi': 1.0,
        },
        'distance_specialty': {
            'sprint': 1.0,
            'mile': 1.1,
            'intermediate': 1.1,
            'long': 1.0,
        },
        'outer_track_advantage': 1.0,
    },

    '中京': {
        'track_type': 'left',
        'turf_straight': 412.5,
        'dirt_straight': 410.7,
        'track_width': 'medium',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': 'firm',
        'dirt_surface': 'deep',
        'run_style_bias': {
            'nige': 1.05,
            'senko': 1.1,
            'sashi': 1.0,
            'oikomi': 0.95,
        },
        'distance_specialty': {
            'sprint': 1.1,
            'mile': 1.1,
            'intermediate': 1.0,
            'long': 0.9,
        },
        'outer_track_advantage': 1.0,
    },

    '新潟': {
        'track_type': 'left',
        'turf_straight': 658.0,  # 日本最長
        'dirt_straight': 353.9,
        'track_width': 'wide',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': 'soft',
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 0.8,  # 逃げ不利（直線長い）
            'senko': 0.9,
            'sashi': 1.2,
            'oikomi': 1.3,  # 追込有利
        },
        'distance_specialty': {
            'sprint': 0.9,
            'mile': 1.0,
            'intermediate': 1.1,
            'long': 1.2,
        },
        'outer_track_advantage': 1.15,  # 外枠かなり有利
    },

    '札幌': {
        'track_type': 'right',
        'turf_straight': 266.1,
        'dirt_straight': 264.4,
        'track_width': 'medium',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': 'soft',
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.15,
            'senko': 1.1,
            'sashi': 0.95,
            'oikomi': 0.9,
        },
        'distance_specialty': {
            'sprint': 1.1,
            'mile': 1.0,
            'intermediate': 0.95,
            'long': 0.9,
        },
        'outer_track_advantage': 0.95,
    },

    '函館': {
        'track_type': 'right',
        'turf_straight': 262.1,
        'dirt_straight': 260.9,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'up-down',
        'turf_surface': 'soft',
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.2,
            'senko': 1.15,
            'sashi': 0.9,
            'oikomi': 0.85,
        },
        'distance_specialty': {
            'sprint': 1.15,
            'mile': 1.05,
            'intermediate': 0.9,
            'long': 0.8,
        },
        'outer_track_advantage': 0.9,
    },

    '福島': {
        'track_type': 'right',
        'turf_straight': 292.0,
        'dirt_straight': 295.7,
        'track_width': 'medium',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': 'firm',
        'dirt_surface': 'mixed',
        'run_style_bias': {
            'nige': 1.1,
            'senko': 1.05,
            'sashi': 0.95,
            'oikomi': 0.9,
        },
        'distance_specialty': {
            'sprint': 1.1,
            'mile': 1.05,
            'intermediate': 0.95,
            'long': 0.9,
        },
        'outer_track_advantage': 1.0,
    },

    '小倉': {
        'track_type': 'right',
        'turf_straight': 293.0,
        'dirt_straight': 291.7,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': 'soft',
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.15,
            'senko': 1.1,
            'sashi': 0.95,
            'oikomi': 0.9,
        },
        'distance_specialty': {
            'sprint': 1.15,
            'mile': 1.1,
            'intermediate': 0.95,
            'long': 0.85,
        },
        'outer_track_advantage': 0.95,
    },
}

# ====================================================================
# 地方競馬（NAR）の会場特性
# ====================================================================

NAR_VENUE_CHARACTERISTICS = {
    '大井': {
        'track_type': 'right',
        'turf_straight': 0,  # ダートのみ
        'dirt_straight': 450.0,
        'track_width': 'wide',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'deep',
        'run_style_bias': {
            'nige': 1.1,
            'senko': 1.1,
            'sashi': 1.0,
            'oikomi': 0.9,
        },
        'distance_specialty': {
            'sprint': 1.1,
            'mile': 1.1,
            'intermediate': 1.0,
            'long': 0.9,
        },
        'outer_track_advantage': 1.0,
        'night_race': True,  # ナイター開催
    },

    '川崎': {
        'track_type': 'left',
        'turf_straight': 0,
        'dirt_straight': 340.0,
        'track_width': 'medium',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.2,
            'senko': 1.15,
            'sashi': 0.9,
            'oikomi': 0.85,
        },
        'distance_specialty': {
            'sprint': 1.15,
            'mile': 1.1,
            'intermediate': 0.95,
            'long': 0.9,
        },
        'outer_track_advantage': 0.95,
        'night_race': True,
    },

    '船橋': {
        'track_type': 'left',
        'turf_straight': 0,
        'dirt_straight': 380.0,
        'track_width': 'medium',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'mixed',
        'run_style_bias': {
            'nige': 1.15,
            'senko': 1.1,
            'sashi': 0.95,
            'oikomi': 0.9,
        },
        'distance_specialty': {
            'sprint': 1.1,
            'mile': 1.1,
            'intermediate': 1.0,
            'long': 0.9,
        },
        'outer_track_advantage': 1.0,
        'night_race': True,
    },

    '浦和': {
        'track_type': 'left',
        'turf_straight': 0,
        'dirt_straight': 340.0,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.2,
            'senko': 1.15,
            'sashi': 0.9,
            'oikomi': 0.85,
        },
        'distance_specialty': {
            'sprint': 1.15,
            'mile': 1.1,
            'intermediate': 0.95,
            'long': 0.85,
        },
        'outer_track_advantage': 0.9,
        'night_race': True,
    },

    '門別': {
        'track_type': 'right',
        'turf_straight': 0,
        'dirt_straight': 350.0,
        'track_width': 'medium',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'deep',
        'run_style_bias': {
            'nige': 1.1,
            'senko': 1.05,
            'sashi': 1.0,
            'oikomi': 0.95,
        },
        'distance_specialty': {
            'sprint': 1.0,
            'mile': 1.1,
            'intermediate': 1.0,
            'long': 0.95,
        },
        'outer_track_advantage': 1.0,
        'night_race': False,
    },

    '盛岡': {
        'track_type': 'left',
        'turf_straight': 0,
        'dirt_straight': 333.0,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.2,
            'senko': 1.1,
            'sashi': 0.95,
            'oikomi': 0.9,
        },
        'distance_specialty': {
            'sprint': 1.1,
            'mile': 1.05,
            'intermediate': 0.95,
            'long': 0.9,
        },
        'outer_track_advantage': 0.95,
        'night_race': False,
    },

    '園田': {
        'track_type': 'right',
        'turf_straight': 0,
        'dirt_straight': 291.0,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.25,
            'senko': 1.15,
            'sashi': 0.9,
            'oikomi': 0.85,
        },
        'distance_specialty': {
            'sprint': 1.2,
            'mile': 1.1,
            'intermediate': 0.9,
            'long': 0.8,
        },
        'outer_track_advantage': 0.9,
        'night_race': True,
    },

    '佐賀': {
        'track_type': 'right',
        'turf_straight': 0,
        'dirt_straight': 295.0,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.2,
            'senko': 1.1,
            'sashi': 0.95,
            'oikomi': 0.9,
        },
        'distance_specialty': {
            'sprint': 1.15,
            'mile': 1.1,
            'intermediate': 0.95,
            'long': 0.85,
        },
        'outer_track_advantage': 0.95,
        'night_race': True,
    },

    '高知': {
        'track_type': 'right',
        'turf_straight': 0,
        'dirt_straight': 250.0,
        'track_width': 'narrow',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': None,
        'dirt_surface': 'shallow',
        'run_style_bias': {
            'nige': 1.3,  # 非常に逃げ有利
            'senko': 1.2,
            'sashi': 0.85,
            'oikomi': 0.8,
        },
        'distance_specialty': {
            'sprint': 1.2,
            'mile': 1.05,
            'intermediate': 0.85,
            'long': 0.75,
        },
        'outer_track_advantage': 0.9,
        'night_race': True,
    },
}

# 全会場をマージ
ALL_VENUE_CHARACTERISTICS = {**JRA_VENUE_CHARACTERISTICS, **NAR_VENUE_CHARACTERISTICS}


def get_venue_characteristics(venue):
    """
    会場の特性を取得

    Args:
        venue (str): 会場名

    Returns:
        dict: 会場特性、見つからない場合はデフォルト値
    """
    default = {
        'track_type': 'right',
        'turf_straight': 300.0,
        'dirt_straight': 300.0,
        'track_width': 'medium',
        'corners': 4,
        'slope': 'flat',
        'turf_surface': 'firm',
        'dirt_surface': 'mixed',
        'run_style_bias': {'nige': 1.0, 'senko': 1.0, 'sashi': 1.0, 'oikomi': 1.0},
        'distance_specialty': {'sprint': 1.0, 'mile': 1.0, 'intermediate': 1.0, 'long': 1.0},
        'outer_track_advantage': 1.0,
        'night_race': False,
    }

    return ALL_VENUE_CHARACTERISTICS.get(venue, default)


def get_distance_category(distance):
    """
    距離をカテゴリに分類

    Args:
        distance (int): 距離(m)

    Returns:
        str: 'sprint', 'mile', 'intermediate', 'long'
    """
    if distance < 1400:
        return 'sprint'
    elif distance < 1800:
        return 'mile'
    elif distance < 2400:
        return 'intermediate'
    else:
        return 'long'


def get_run_style_bias(venue, run_style):
    """
    会場における脚質の有利度を取得

    Args:
        venue (str): 会場名
        run_style (str): 'nige', 'senko', 'sashi', 'oikomi'

    Returns:
        float: 有利度（1.0が標準）
    """
    characteristics = get_venue_characteristics(venue)
    return characteristics['run_style_bias'].get(run_style, 1.0)


def get_distance_bias(venue, distance):
    """
    会場における距離適性を取得

    Args:
        venue (str): 会場名
        distance (int): 距離(m)

    Returns:
        float: 適性度（1.0が標準）
    """
    characteristics = get_venue_characteristics(venue)
    category = get_distance_category(distance)
    return characteristics['distance_specialty'].get(category, 1.0)


if __name__ == "__main__":
    # テスト
    print("=" * 60)
    print("会場特性テスト")
    print("=" * 60)

    test_venues = ['東京', '中山', '新潟', '大井', '川崎']

    for venue in test_venues:
        char = get_venue_characteristics(venue)
        print(f"\n{venue}競馬場:")
        print(f"  直線: 芝{char.get('turf_straight', 'N/A')}m / ダ{char['dirt_straight']}m")
        print(f"  回り: {char['track_type']}")
        print(f"  脚質: 逃げ{char['run_style_bias']['nige']:.2f} "
              f"先行{char['run_style_bias']['senko']:.2f} "
              f"差し{char['run_style_bias']['sashi']:.2f} "
              f"追込{char['run_style_bias']['oikomi']:.2f}")

    print("\n✅ 会場特性データの定義完了")
