#!/usr/bin/env python3
"""
馬履歴・血統データ取得関数のテスト
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime

def get_horse_pedigree(horse_id):
    """
    馬の血統情報を取得
    
    Returns:
        dict: {'father': '', 'mother': '', 'bms': ''}
    """
    url = f"https://db.netkeiba.com/horse/{horse_id}/"
    
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        pedigree = {'father': '', 'mother': '', 'bms': ''}
        
        # 血統テーブルから抽出
        ped_table = soup.select_one('table.blood_table')
        if ped_table:
            rows = ped_table.find_all('tr')
            if len(rows) >= 1:
                # 父
                father_cell = rows[0].find_all('td')
                if father_cell:
                    pedigree['father'] = father_cell[0].text.strip()
                
                # 母
                if len(rows) >= 2:
                    mother_cell = rows[1].find_all('td')
                    if mother_cell:
                        pedigree['mother'] = mother_cell[0].text.strip()
                
                # 母父(BMS)
                if len(rows) >= 3:
                    bms_cell = rows[2].find_all('td')
                    if bms_cell:
                        pedigree['bms'] = bms_cell[0].text.strip()
        
        return pedigree
    
    except Exception as e:
        print(f"  ⚠️ 血統取得エラー({horse_id}): {e}")
        return {'father': '', 'mother': '', 'bms': ''}

def get_horse_history(horse_id, race_date, n_samples=5):
    """
    馬の過去走データを取得(race_date以前の最新5走)
    
    Returns:
        list of dict: 過去5走のデータ
    """
    url = f"https://db.netkeiba.com/horse/{horse_id}/"
    
    try:
        time.sleep(0.5)
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'EUC-JP'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # レース結果テーブル
        result_table = soup.select_one('table.db_h_race_results')
        if not result_table:
            return []
        
        rows = result_table.find_all('tr')[1:]  # ヘッダー除く
        
        # race_dateをdatetimeに変換
        if isinstance(race_date, str):
            race_date_obj = pd.to_datetime(race_date)
        else:
            race_date_obj = race_date
        
        past_races = []
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 10:
                continue
            
            # 日付を取得
            date_text = cells[0].text.strip()
            try:
                race_date_past = pd.to_datetime(date_text)
                
                # race_date以前のレースのみ
                if race_date_past >= race_date_obj:
                    continue
                
                # データ抽出
                race_data = {
                    'date': date_text,
                    'rank': cells[11].text.strip() if len(cells) > 11 else '',
                    'time': cells[17].text.strip() if len(cells) > 17 else '',
                    'run_style': '',  # 後で計算
                    'race_name': cells[4].text.strip() if len(cells) > 4 else '',
                    'last_3f': cells[22].text.strip() if len(cells) > 22 else '',
                    'horse_weight': cells[23].text.strip() if len(cells) > 23 else '',
                    'jockey': cells[12].text.strip() if len(cells) > 12 else '',
                    'condition': cells[15].text.strip() if len(cells) > 15 else '',
                    'odds': cells[13].text.strip() if len(cells) > 13 else '',
                    'weather': cells[2].text.strip() if len(cells) > 2 else '',
                    'distance': '',
                    'course_type': ''
                }
                
                # 距離・コースタイプ
                distance_text = cells[14].text.strip() if len(cells) > 14 else ''
                dist_match = re.search(r'(芝|ダ|障)(\d+)', distance_text)
                if dist_match:
                    course_type = dist_match.group(1)
                    if course_type == '芝':
                        race_data['course_type'] = '芝'
                    elif course_type == 'ダ':
                        race_data['course_type'] = 'ダート'
                    elif course_type == '障':
                        race_data['course_type'] = '障害'
                    race_data['distance'] = dist_match.group(2)
                
                past_races.append(race_data)
                
                if len(past_races) >= n_samples:
                    break
            
            except:
                continue
        
        return past_races
    
    except Exception as e:
        print(f"  ⚠️ 履歴取得エラー({horse_id}): {e}")
        return []

# テスト実行
if __name__ == "__main__":
    # テスト用horse_id(ウインルーア - 前回のテストで使用)
    test_horse_id = "2018101626"
    test_race_date = "2020/07/25"
    
    print(f"🧪 馬データ取得テスト")
    print(f"{'='*80}\n")
    print(f"Horse ID: {test_horse_id}")
    print(f"Race Date: {test_race_date}\n")
    
    # 血統テスト
    print("📊 血統データ:")
    pedigree = get_horse_pedigree(test_horse_id)
    for key, value in pedigree.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    # 履歴テスト
    print(f"\n📊 過去走データ(最新5走):")
    history = get_horse_history(test_horse_id, test_race_date, n_samples=5)
    
    if history:
        print(f"  取得件数: {len(history)}/5")
        for i, race in enumerate(history, 1):
            print(f"\n  Past {i}:")
            for key, value in race.items():
                status = "✅" if value else "❌"
                print(f"    {status} {key}: {value}")
    else:
        print(f"  ❌ データなし")
    
    # 統計
    print(f"\n{'='*80}")
    print("📊 統計:")
    pedigree_filled = sum(1 for v in pedigree.values() if v)
    print(f"  血統: {pedigree_filled}/3 ({pedigree_filled/3*100:.0f}%)")
    
    if history:
        total_fields = len(history[0])
        avg_filled = sum(sum(1 for v in race.values() if v) for race in history) / len(history)
        print(f"  履歴(平均): {avg_filled:.1f}/{total_fields} ({avg_filled/total_fields*100:.0f}%)")
