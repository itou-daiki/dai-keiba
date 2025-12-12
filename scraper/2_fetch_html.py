#!/usr/bin/env python3
"""
取得したURLからHTMLを取得して保存するスクリプト
Zennの記事に基づいて実装: https://zenn.dev/kami/articles/66e400c8a43cd08a5d7f
"""

import os
import time
import requests
from pathlib import Path

def fetch_html_from_url(url, save_dir):
    """URLからHTMLを取得して保存"""
    try:
        # URLからレースIDを抽出
        url_parts = url.split("/")
        race_id = url_parts[-2] if len(url_parts) > 2 else None

        if not race_id:
            print(f"✗ URLからレースIDを抽出できません: {url}")
            return False

        save_file_path = os.path.join(save_dir, f"{race_id}.html")

        # すでに取得済みの場合はスキップ
        if os.path.exists(save_file_path):
            print(f"スキップ (既存): {race_id}")
            return True

        # HTMLを取得
        response = requests.get(url)
        # 文字コードを自動検出して設定
        response.encoding = response.apparent_encoding
        html = response.text

        # サーバーに負荷をかけないように待機
        time.sleep(5)

        # HTMLを保存
        with open(save_file_path, 'w', encoding='utf-8') as file:
            file.write(html)

        print(f"✓ 取得: {race_id}")
        return True

    except Exception as e:
        print(f"✗ エラー ({url}): {e}")
        return False

def fetch_all_html(year, month):
    """指定した年月のすべてのレースのHTMLを取得"""
    # URLファイルのパス
    url_file = f"data/urls/{year}-{str(month).zfill(2)}.txt"

    if not os.path.exists(url_file):
        print(f"✗ URLファイルが見つかりません: {url_file}")
        print("先に1_fetch_race_urls.pyを実行してください")
        return

    # 保存先ディレクトリ
    save_dir = f"data/html/{year}/{str(month).zfill(2)}"
    os.makedirs(save_dir, exist_ok=True)

    # URLファイルを読み込み
    with open(url_file, "r", encoding='utf-8') as f:
        urls = f.read().splitlines()

    print(f"HTMLダウンロードを開始します: {len(urls)}件")
    print("=" * 50)

    success_count = 0
    fail_count = 0

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] ", end="")
        if fetch_html_from_url(url, save_dir):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 50)
    print(f"✓ 完了: {success_count}件")
    print(f"✗ 失敗: {fail_count}件")
    print(f"保存先: {save_dir}")

def main():
    """メイン処理"""
    # 環境変数から年月を取得、デフォルトは現在の年月
    import datetime

    year = int(os.environ.get('SCRAPE_YEAR', datetime.datetime.now().year))
    month = int(os.environ.get('SCRAPE_MONTH', datetime.datetime.now().month))

    print(f"HTMLダウンロードを開始します: {year}年{month}月")
    print("=" * 50)

    fetch_all_html(year, month)

if __name__ == "__main__":
    main()
