#!/usr/bin/env python3
"""
レース検索画面からレースURLを取得するスクリプト
Zennの記事に基づいて実装: https://zenn.dev/kami/articles/66e400c8a43cd08a5d7f
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def setup_driver():
    """Seleniumドライバーのセットアップ"""
    options = Options()
    options.add_argument('--headless')  # ヘッドレスモード
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    return driver, wait

def fetch_race_urls(year, month, driver, wait):
    """指定した年月のレースURLを取得"""
    URL = "https://db.netkeiba.com/?pid=race_search_detail"
    driver.get(URL)
    time.sleep(1)
    wait.until(EC.presence_of_all_elements_located)

    # 期間を選択
    start_year_element = driver.find_element(By.NAME, 'start_year')
    start_year_select = Select(start_year_element)
    start_year_select.select_by_value(str(year))

    start_mon_element = driver.find_element(By.NAME, 'start_mon')
    start_mon_select = Select(start_mon_element)
    start_mon_select.select_by_value(str(month))

    end_year_element = driver.find_element(By.NAME, 'end_year')
    end_year_select = Select(end_year_element)
    end_year_select.select_by_value(str(year))

    end_mon_element = driver.find_element(By.NAME, 'end_mon')
    end_mon_select = Select(end_mon_element)
    end_mon_select.select_by_value(str(month))

    # 中央競馬場をチェック（1〜10: 札幌、函館、福島、新潟、中山、東京、中京、京都、阪神、小倉）
    for i in range(1, 11):
        terms = driver.find_element(By.ID, f"check_Jyo_{str(i).zfill(2)}")
        terms.click()

    # 表示件数を選択（最大の100へ）
    list_element = driver.find_element(By.NAME, 'list')
    list_select = Select(list_element)
    list_select.select_by_value("100")

    # フォームを送信
    frm = driver.find_element(By.CSS_SELECTOR, "#db_search_detail_form > form")
    frm.submit()
    time.sleep(5)
    wait.until(EC.presence_of_all_elements_located)

    # URLを保存するファイル
    save_dir = "data/urls"
    os.makedirs(save_dir, exist_ok=True)
    save_file = os.path.join(save_dir, f"{year}-{str(month).zfill(2)}.txt")

    urls = []

    # ページ送りをしながらURLを取得
    with open(save_file, mode='w', encoding='utf-8') as f:
        while True:
            time.sleep(5)
            wait.until(EC.presence_of_all_elements_located)

            all_rows = driver.find_element(By.CLASS_NAME, 'race_table_01').find_elements(By.TAG_NAME, "tr")

            for row in range(1, len(all_rows)):
                try:
                    race_href = all_rows[row].find_elements(By.TAG_NAME, "td")[4].find_element(By.TAG_NAME, "a").get_attribute("href")
                    f.write(race_href + "\n")
                    urls.append(race_href)
                    print(f"取得: {race_href}")
                except Exception as e:
                    print(f"行 {row} でエラー: {e}")
                    continue

            try:
                # 次のページへ
                target = driver.find_elements(By.LINK_TEXT, "次")[0]
                # JavaScriptでクリック処理（ElementClickInterceptedException回避）
                driver.execute_script("arguments[0].click();", target)
            except IndexError:
                # 最後のページ
                print("最後のページに到達しました")
                break
            except Exception as e:
                print(f"ページ遷移エラー: {e}")
                break

    print(f"\n{len(urls)}件のレースURLを取得しました")
    print(f"保存先: {save_file}")

    return urls

def main():
    """メイン処理"""
    # 環境変数または引数から年月を取得、デフォルトは現在の年月
    import datetime

    year = int(os.environ.get('SCRAPE_YEAR', datetime.datetime.now().year))
    month = int(os.environ.get('SCRAPE_MONTH', datetime.datetime.now().month))

    print(f"レースURL取得を開始します: {year}年{month}月")
    print("=" * 50)

    driver, wait = setup_driver()

    try:
        urls = fetch_race_urls(year, month, driver, wait)
        print(f"\n✓ 完了しました！{len(urls)}件のURLを取得")
    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
