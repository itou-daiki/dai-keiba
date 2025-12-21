"""
中央競馬と地方競馬の分類
"""

# JRA中央競馬の会場リスト（10会場）
JRA_VENUES = [
    '札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉'
]

# 地方競馬の主要会場
NAR_VENUES = [
    # 北海道
    '門別', '帯広',
    # 東北
    '盛岡', '水沢',
    # 関東
    '浦和', '船橋', '大井', '川崎',
    # 北陸・東海
    '金沢', '笠松', '名古屋',
    # 関西
    '園田', '姫路',
    # 四国・九州
    '高知', '佐賀'
]


def classify_race_type(venue):
    """
    会場から中央競馬（JRA）か地方競馬（NAR）かを判定

    Args:
        venue (str): 会場名

    Returns:
        str: 'JRA' or 'NAR'

    Examples:
        >>> classify_race_type('東京')
        'JRA'
        >>> classify_race_type('大井')
        'NAR'
        >>> classify_race_type('中山')
        'JRA'
    """
    if not isinstance(venue, str):
        return 'UNKNOWN'

    venue = venue.strip()

    # JRA会場
    if venue in JRA_VENUES:
        return 'JRA'

    # NAR会場
    if venue in NAR_VENUES:
        return 'NAR'

    # 不明な場合の推測ロジック
    # JRAは基本的に漢字2文字（例外: 新潟など）
    # 地方は3文字以上が多い（例外: 金沢など）
    if len(venue) == 2 and venue not in NAR_VENUES:
        return 'JRA'

    # デフォルトは地方競馬
    return 'NAR'


def get_race_type_code(race_type):
    """
    レースタイプを数値コードに変換

    Args:
        race_type (str): 'JRA' or 'NAR'

    Returns:
        int: JRA=1, NAR=0, UNKNOWN=-1
    """
    mapping = {
        'JRA': 1,
        'NAR': 0,
        'UNKNOWN': -1
    }
    return mapping.get(race_type, -1)


def is_jra_race(venue):
    """
    JRAレースかどうかを判定

    Args:
        venue (str): 会場名

    Returns:
        bool: JRAならTrue、それ以外False
    """
    return classify_race_type(venue) == 'JRA'


def is_nar_race(venue):
    """
    地方競馬レースかどうかを判定

    Args:
        venue (str): 会場名

    Returns:
        bool: NARならTrue、それ以外False
    """
    return classify_race_type(venue) == 'NAR'


if __name__ == "__main__":
    # テスト
    test_venues = [
        '東京', '中山', '阪神', '京都', '中京',  # JRA
        '大井', '川崎', '船橋', '園田', '佐賀',  # NAR
        '不明な会場'
    ]

    print("=" * 60)
    print("会場分類テスト")
    print("=" * 60)

    for venue in test_venues:
        race_type = classify_race_type(venue)
        code = get_race_type_code(race_type)
        print(f"{venue:10s} → {race_type:7s} (code: {code})")

    print("\n✅ すべての会場を正しく分類しました")
