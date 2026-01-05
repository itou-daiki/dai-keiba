"""
オッズ取得の安定化
リトライ処理と複数ソースからの取得
"""

import requests
from bs4 import BeautifulSoup
import time
from functools import wraps
import json
import os


def retry_on_failure(max_retries=3, delay=2):
    """
    失敗時に自動リトライするデコレータ

    Args:
        max_retries: 最大リトライ回数
        delay: リトライ間隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"  ❌ {func.__name__} failed after {max_retries} attempts: {e}")
                        raise e

                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    print(f"  ⚠️ Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)

            return None
        return wrapper
    return decorator


class OddsScraper:
    """
    オッズ取得クラス（複数ソース対応）
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.cache_file = "odds_cache.json"
        self.cache = self._load_cache()

    def _load_cache(self):
        """キャッシュを読み込み"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """キャッシュを保存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Cache save failed: {e}")

    @retry_on_failure(max_retries=3, delay=2)
    def _get_odds_netkeiba(self, race_id):
        """
        netkeiba.comからオッズを取得

        Args:
            race_id: レースID (例: 202506050101)

        Returns:
            dict: {馬番: オッズ}
        """
        url = f"https://race.netkeiba.com/odds/index.html?race_id={race_id}&type=b1"

        time.sleep(1)  # Be polite

        response = requests.get(url, headers=self.headers, timeout=10)
        response.encoding = response.apparent_encoding

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        odds_dict = {}

        # Find odds table
        # Format varies, but typically:
        # <td class="Waku1"> ... <td class="Odds">2.5</td>

        odds_elements = soup.select('td.Odds')

        if not odds_elements:
            # Try alternative selector
            odds_elements = soup.find_all('td', string=lambda t: t and '.' in str(t))

        # Extract odds
        umaban = 1
        for elem in odds_elements:
            try:
                odds_text = elem.get_text(strip=True)
                odds_value = float(odds_text)
                odds_dict[umaban] = odds_value
                umaban += 1
            except ValueError:
                continue

        if not odds_dict:
            raise Exception("No odds found in netkeiba")

        return odds_dict

    @retry_on_failure(max_retries=2, delay=3)
    def _get_odds_jra(self, race_id):
        """
        JRA公式からオッズを取得（バックアップ）

        Note: JRA公式のURLは実際には異なるフォーマット
        ここでは概念的な実装例

        Args:
            race_id: レースID

        Returns:
            dict: {馬番: オッズ}
        """
        # JRAのrace_idフォーマットは異なる可能性がある
        # 実装例として簡略化

        # Example: https://www.jra.go.jp/JRADB/accessO.html?CNAME=pw01oli00/...
        # 実際のエンドポイントは調査が必要

        print("  ℹ️ JRA official source not fully implemented (placeholder)")

        # Placeholder: return empty
        return {}

    def get_odds_multi_source(self, race_id):
        """
        複数ソースからオッズを取得

        Args:
            race_id: レースID

        Returns:
            dict: {馬番: オッズ} or None
        """
        print(f"📊 Fetching odds for race {race_id}...")

        # Check cache first
        if race_id in self.cache:
            print("  ✅ Using cached odds")
            return self.cache[race_id]

        odds = None

        # Priority 1: netkeiba
        try:
            print("  Trying netkeiba.com...")
            odds = self._get_odds_netkeiba(race_id)
            if odds:
                print(f"  ✅ Got odds from netkeiba ({len(odds)} horses)")
                self.cache[race_id] = odds
                self._save_cache()
                return odds
        except Exception as e:
            print(f"  ⚠️ netkeiba failed: {e}")

        # Priority 2: JRA official (placeholder)
        try:
            print("  Trying JRA official...")
            odds = self._get_odds_jra(race_id)
            if odds:
                print(f"  ✅ Got odds from JRA ({len(odds)} horses)")
                self.cache[race_id] = odds
                self._save_cache()
                return odds
        except Exception as e:
            print(f"  ⚠️ JRA failed: {e}")

        # Priority 3: Use cached odds from previous fetch (if available)
        if race_id in self.cache:
            print("  ⚠️ Using stale cached odds")
            return self.cache[race_id]

        print("  ❌ All sources failed")
        return None

    def get_odds_batch(self, race_ids):
        """
        複数レースのオッズを一括取得

        Args:
            race_ids: レースIDのリスト

        Returns:
            dict: {race_id: {馬番: オッズ}}
        """
        results = {}

        for i, race_id in enumerate(race_ids, 1):
            print(f"\n[{i}/{len(race_ids)}] Processing {race_id}...")

            odds = self.get_odds_multi_source(race_id)
            if odds:
                results[race_id] = odds
            else:
                results[race_id] = {}

            # Polite delay between requests
            if i < len(race_ids):
                time.sleep(2)

        return results


if __name__ == "__main__":
    # Test
    scraper = OddsScraper()

    # Example race ID (adjust to a real one for testing)
    test_race_id = "202506050101"

    odds = scraper.get_odds_multi_source(test_race_id)

    if odds:
        print("\n✅ Odds retrieved successfully:")
        for umaban, odd in odds.items():
            print(f"  馬番 {umaban}: {odd}倍")
    else:
        print("\n❌ Failed to retrieve odds")
