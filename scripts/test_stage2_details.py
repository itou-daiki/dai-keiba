#!/usr/bin/env python3
"""
Stage 2 Details 修正版テスト
正しいURLで馬履歴・血統データを取得
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import io

def get_horse_pedigree(horse_id):
    """血統情報を取得"""
    url = f"https://db.netkeiba.com/horse/ped/{horse_id}/"
    
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        pedigree = {'father': '', 'mother': '', 'bms': ''}
        
        # 血統テーブルから抽出(簡易版)
        # 実際にはテーブル構造を解析して抽出
        text = soup.text
        
        # ページ内に父・母・母父の情報があるはず
        print(f"  血統ページ取得成功")
        
        return pedigree
    except Exception as e:
        print(f"  ⚠️ 血統取得エラー: {e}")
        return {'father': '', 'mother': '', 'bms': ''}

def get_horse_history(horse_id, race_date):
    """レース履歴を取得(race_date以前の最新5走)"""
    url = f"https://db.netkeiba.com/horse/result/{horse_id}/"
    
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # テーブル取得
        tables = soup.find_all('table')
        if not tables:
            print(f"  ❌ テーブルなし")
            return []
        
        # DataFrameに変換
        df = pd.read_html(io.StringIO(str(tables[0])))[0]
        df = df.dropna(how='all')
        
        print(f"  📋 総レース数: {len(df)}")
        
        # カラム名を正規化
        df.columns = df.columns.astype(str).str.replace(r'\s+', '', regex=True)
        print(f"  📋 カラム: {list(df.columns)[:10]}")
        
        # 日付フィルタリング
        if '日付' in df.columns:
            df['date_obj'] = pd.to_datetime(df['日付'], format='%Y/%m/%d', errors='coerce')
            df = df.dropna(subset=['date_obj'])
            
            # race_date以前のレースのみ
            current_date = pd.to_datetime(race_date)
            df = df[df['date_obj'] < current_date]
            df = df.sort_values('date_obj', ascending=False)
            df = df.head(5)
            
            print(f"  📋 {race_date}以前の最新5走: {len(df)}件")
            
            # データ抽出
            past_races = []
            for i, row in enumerate(df.itertuples(), 1):
                race_data = {
                    'date': getattr(row, '日付', ''),
                    'rank': str(getattr(row, '着順', '')),
                    'time': str(getattr(row, 'タイム', '')),
                    'race_name': str(getattr(row, 'レース名', '')),
                    'last_3f': str(getattr(row, '上り', '')),
                    'horse_weight': str(getattr(row, '馬体重', '')),
                    'jockey': str(getattr(row, '騎手', '')),
                    'condition': str(getattr(row, '馬場', '')),
                    'odds': str(getattr(row, '単勝', '') or getattr(row, 'オッズ', '')),
                    'weather': str(getattr(row, '天気', '')),
                    'distance': '',
                    'course_type': '',
                    'run_style': '3'
                }
                
                # 距離・コースタイプ
                dist_text = str(getattr(row, '距離', ''))
                dist_match = re.search(r'(芝|ダ|障)(\d+)', dist_text)
                if dist_match:
                    course_type = dist_match.group(1)
                    race_data['course_type'] = '芝' if course_type == '芝' else 'ダート' if course_type == 'ダ' else '障害'
                    race_data['distance'] = dist_match.group(2)
                
                past_races.append(race_data)
                
                print(f"    Past {i}: {race_data['date']} {race_data['race_name'][:20]} {race_data['rank']}着")
            
            return past_races
        else:
            print(f"  ❌ '日付'カラムなし")
            return []
    
    except Exception as e:
        print(f"  ❌ 履歴取得エラー: {e}")
        import traceback
        traceback.print_exc()
        return []

# テスト実行
if __name__ == "__main__":
    print("🧪 Stage 2 Details 修正版テスト\n")
    print(f"{'='*80}\n")
    
    # テストケース
    test_cases = [
        ("2021105898", "2024/12/22", "レガレイラ"),
        ("2018105165", "2024/12/22", "シャフリヤール"),
    ]
    
    for horse_id, race_date, horse_name in test_cases:
        print(f"🐴 {horse_name} (ID: {horse_id})")
        print(f"{'-'*80}")
        
        # 血統
        print(f"\n📊 血統情報:")
        pedigree = get_horse_pedigree(horse_id)
        
        # 履歴
        print(f"\n📊 レース履歴:")
        history = get_horse_history(horse_id, race_date)
        
        # 統計
        print(f"\n📈 統計:")
        print(f"  血統フィールド: {sum(1 for v in pedigree.values() if v)}/3")
        if history:
            avg_filled = sum(sum(1 for v in race.values() if v) for race in history) / len(history)
            print(f"  履歴フィールド(平均): {avg_filled:.1f}/13")
            print(f"  取得レース数: {len(history)}/5")
        else:
            print(f"  履歴: 0件")
        
        print(f"\n{'='*80}\n")
