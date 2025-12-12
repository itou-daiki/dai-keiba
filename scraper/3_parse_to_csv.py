#!/usr/bin/env python3
"""
HTMLを解析してCSVを作成するスクリプト
Zennの記事に基づいて実装: https://zenn.dev/kami/articles/66e400c8a43cd08a5d7f
"""

import os
import pandas as pd
from bs4 import BeautifulSoup

# レース詳細のカラム
RACE_COLUMNS = [
    'race_id',          # レースID
    'race_round',       # ラウンド数
    'race_title',       # レースタイトル
    'course_info',      # コース情報
    'weather',          # 天候
    'ground_state',     # 馬場状態
    'date',             # 日時
    'venue',            # 競馬場
    'first_place_horse',  # 1着馬番
    'second_place_horse', # 2着馬番
    'third_place_horse',  # 3着馬番
]

# 馬詳細のカラム
HORSE_COLUMNS = [
    'race_id',          # レースID
    'rank',             # 着順
    'horse_id',         # 馬ID
    'horse_number',     # 馬番
    'waku_number',      # 枠番
    'sex_age',          # 性別年齢
    'weight_burden',    # 負担重量
    'horse_weight',     # 馬体重
    'horse_weight_diff',# 馬体重差
    'time',             # タイム
    'margin',           # 着差
    'last_3f',          # 上がり3F
    'odds',             # オッズ
    'popularity',       # 人気
    'jockey',           # 騎手
    'trainer',          # 調教師
]

def parse_race_data(race_id, html):
    """HTMLからレースデータを抽出"""
    soup = BeautifulSoup(html, 'html.parser')

    race_data = {'race_id': race_id}

    try:
        # レース情報を取得
        race_title_elem = soup.select_one('.RaceName')
        if race_title_elem:
            race_data['race_title'] = race_title_elem.text.strip()

        race_data01 = soup.select_one('.RaceData01')
        if race_data01:
            race_data['course_info'] = race_data01.text.strip()

        race_data02 = soup.select_one('.RaceData02')
        if race_data02:
            spans = race_data02.find_all('span')
            if len(spans) >= 1:
                race_data['weather'] = spans[0].text.strip()
            if len(spans) >= 2:
                race_data['ground_state'] = spans[1].text.strip()

        # 日付情報
        race_date_elem = soup.select_one('dd.Active')
        if race_date_elem:
            race_data['date'] = race_date_elem.text.strip()

    except Exception as e:
        print(f"  警告: レース情報の一部を取得できませんでした ({race_id}): {e}")

    return race_data

def parse_horse_data(race_id, html):
    """HTMLから馬データを抽出"""
    soup = BeautifulSoup(html, 'html.parser')

    horses = []

    try:
        # 結果テーブルを取得
        result_table = soup.select_one('.Race_Result_Table, .race_table_01')
        if not result_table:
            print(f"  警告: 結果テーブルが見つかりません ({race_id})")
            return horses

        rows = result_table.select('tbody tr')

        for row in rows:
            try:
                horse_data = {'race_id': race_id}

                cells = row.find_all('td')
                if len(cells) < 10:
                    continue

                # 着順
                horse_data['rank'] = cells[0].text.strip()

                # 枠番
                horse_data['waku_number'] = cells[1].text.strip()

                # 馬番
                horse_data['horse_number'] = cells[2].text.strip()

                # 馬名とID
                horse_link = cells[3].select_one('a')
                if horse_link:
                    href = horse_link.get('href', '')
                    if '/horse/' in href:
                        horse_data['horse_id'] = href.split('/horse/')[1].split('/')[0]

                # 性別年齢
                horse_data['sex_age'] = cells[4].text.strip()

                # 負担重量
                horse_data['weight_burden'] = cells[5].text.strip()

                # 騎手
                jockey_elem = cells[6].select_one('a')
                if jockey_elem:
                    horse_data['jockey'] = jockey_elem.text.strip()

                # タイム
                horse_data['time'] = cells[7].text.strip()

                # 着差
                horse_data['margin'] = cells[8].text.strip()

                # 上がり3F (last 3 furlong)
                if len(cells) > 11:
                    horse_data['last_3f'] = cells[11].text.strip()

                # オッズ
                if len(cells) > 12:
                    horse_data['odds'] = cells[12].text.strip()

                # 人気
                if len(cells) > 13:
                    horse_data['popularity'] = cells[13].text.strip()

                # 馬体重
                if len(cells) > 14:
                    weight_text = cells[14].text.strip()
                    if '(' in weight_text:
                        weight_parts = weight_text.replace(')', '').split('(')
                        horse_data['horse_weight'] = weight_parts[0].strip()
                        if len(weight_parts) > 1:
                            horse_data['horse_weight_diff'] = weight_parts[1].strip()
                    else:
                        horse_data['horse_weight'] = weight_text

                horses.append(horse_data)

            except Exception as e:
                print(f"  警告: 馬データの行を処理できませんでした: {e}")
                continue

    except Exception as e:
        print(f"  エラー: 馬データの取得に失敗しました ({race_id}): {e}")

    return horses

def parse_html_to_csv(year, month):
    """HTMLファイルを解析してCSVを作成"""
    html_dir = f"data/html/{year}/{str(month).zfill(2)}"
    csv_dir = "data/csv"
    os.makedirs(csv_dir, exist_ok=True)

    if not os.path.isdir(html_dir):
        print(f"✗ HTMLディレクトリが見つかりません: {html_dir}")
        print("先に2_fetch_html.pyを実行してください")
        return

    race_csv = os.path.join(csv_dir, f"race-{year}-{str(month).zfill(2)}.csv")
    horse_csv = os.path.join(csv_dir, f"horse-{year}-{str(month).zfill(2)}.csv")

    race_df = pd.DataFrame(columns=RACE_COLUMNS)
    horse_df = pd.DataFrame(columns=HORSE_COLUMNS)

    file_list = [f for f in os.listdir(html_dir) if f.endswith('.html')]

    print(f"CSV生成を開始します: {len(file_list)}ファイル")
    print("=" * 50)

    for i, file_name in enumerate(file_list, 1):
        try:
            file_path = os.path.join(html_dir, file_name)
            race_id = file_name.replace('.html', '')

            with open(file_path, 'r', encoding='utf-8') as f:
                html = f.read()

            # レースデータを抽出
            race_data = parse_race_data(race_id, html)
            race_df = pd.concat([race_df, pd.DataFrame([race_data])], ignore_index=True)

            # 馬データを抽出
            horses = parse_horse_data(race_id, html)
            if horses:
                horse_df = pd.concat([horse_df, pd.DataFrame(horses)], ignore_index=True)

            print(f"[{i}/{len(file_list)}] ✓ {race_id} (馬: {len(horses)}頭)")

        except Exception as e:
            print(f"[{i}/{len(file_list)}] ✗ {file_name}: {e}")
            continue

    # CSVに保存
    race_df.to_csv(race_csv, index=False, encoding='utf-8')
    horse_df.to_csv(horse_csv, index=False, encoding='utf-8')

    print("\n" + "=" * 50)
    print(f"✓ レースデータ: {len(race_df)}件 → {race_csv}")
    print(f"✓ 馬データ: {len(horse_df)}件 → {horse_csv}")

def main():
    """メイン処理"""
    # 環境変数から年月を取得、デフォルトは現在の年月
    import datetime

    year = int(os.environ.get('SCRAPE_YEAR', datetime.datetime.now().year))
    month = int(os.environ.get('SCRAPE_MONTH', datetime.datetime.now().month))

    print(f"CSV生成を開始します: {year}年{month}月")
    print("=" * 50)

    parse_html_to_csv(year, month)

if __name__ == "__main__":
    main()
