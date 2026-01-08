#!/usr/bin/env python3
"""
NetkeibaのAPIエンドポイントを調査
"""

import requests
import json

def test_jra_digest_api(date_str="20250105"):
    """JRA Digest APIをテスト"""
    print(f"🔍 Testing JRA Digest API: {date_str}\n")
    
    api_url = "https://race.netkeiba.com/api/api_get_jra_digest2.html"
    
    params = {
        'kaisai_date': date_str,
        'input': 'UTF-8',
        'output': 'json',  # jsonpではなくjsonで試す
        'rf': 'race_list'
    }
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        print(f"📡 Calling: {api_url}")
        print(f"📋 Params: {params}\n")
        
        resp = session.get(api_url, params=params, headers=headers, timeout=10)
        print(f"✅ Status Code: {resp.status_code}")
        print(f"📄 Content Type: {resp.headers.get('Content-Type')}")
        print(f"📏 Content Length: {len(resp.text)} chars\n")
        
        # レスポンスを表示
        print("=" * 60)
        print("Response (first 2000 chars):")
        print("=" * 60)
        print(resp.text[:2000])
        print("\n")
        
        # JSONとしてパース試行
        try:
            # JSONPの場合、関数呼び出しを除去
            text = resp.text
            if text.startswith('callback(') or text.startswith('jsonp'):
                # JSONPをJSONに変換
                import re
                match = re.search(r'\((.*)\)', text, re.DOTALL)
                if match:
                    text = match.group(1)
            
            data = json.loads(text)
            print("=" * 60)
            print("Parsed JSON Structure:")
            print("=" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
            
            # race_idを探す
            def find_race_ids(obj, path=""):
                """再帰的にrace_idを探す"""
                race_ids = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == 'race_id':
                            race_ids.append((path + "." + key, value))
                        else:
                            race_ids.extend(find_race_ids(value, path + "." + key))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        race_ids.extend(find_race_ids(item, path + f"[{i}]"))
                return race_ids
            
            race_ids = find_race_ids(data)
            if race_ids:
                print("\n" + "=" * 60)
                print(f"Found {len(race_ids)} race_id entries:")
                print("=" * 60)
                for path, rid in race_ids[:20]:
                    print(f"  {path}: {rid}")
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Not valid JSON: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_nar_api(date_str="20251201"):
    """NAR APIをテスト(もしあれば)"""
    print(f"\n\n🔍 Testing NAR API: {date_str}\n")
    
    # NARも同様のAPIがあるか確認
    api_url = "https://nar.netkeiba.com/api/api_get_jra_digest2.html"
    
    params = {
        'kaisai_date': date_str,
        'input': 'UTF-8',
        'output': 'json',
        'rf': 'race_list'
    }
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = session.get(api_url, params=params, headers=headers, timeout=10)
        print(f"✅ Status Code: {resp.status_code}")
        print(f"📄 Response (first 1000 chars):")
        print(resp.text[:1000])
    except Exception as e:
        print(f"⚠️  NAR API not found or different endpoint: {e}")


if __name__ == "__main__":
    test_jra_digest_api("20250105")
    test_nar_api("20251201")
