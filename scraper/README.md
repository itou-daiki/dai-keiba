# 競馬データスクレイピングツール

netkeiba.comから競馬のレース結果データを収集し、機械学習用のCSVデータを生成するツールです。

このプロジェクトは以下のZenn記事を参考に実装されています：
https://zenn.dev/kami/articles/66e400c8a43cd08a5d7f

## 機能

- netkeiba.comからレース検索結果のURL取得
- レース詳細ページのHTML取得
- HTMLを解析してCSVデータに変換
- レース情報と馬の情報を別々のCSVで出力

## 必要な環境

- Python 3.7以上
- Chrome/Chromiumブラウザ
- ChromeDriver（Seleniumで使用）

## セットアップ

### 1. 依存パッケージのインストール

```bash
cd scraper
pip install -r requirements.txt
```

### 2. ChromeDriverのインストール

Seleniumを使用するため、ChromeDriverが必要です。

**Ubuntu/Debian:**
```bash
# Chromiumとドライバーをインストール
sudo apt-get update
sudo apt-get install chromium-browser chromium-chromedriver
```

**macOS (Homebrew):**
```bash
brew install chromedriver
```

**手動インストール:**
https://chromedriver.chromium.org/downloads からダウンロードしてPATHに追加

## 使い方

### ステップ1: レースURLを取得

```bash
python3 1_fetch_race_urls.py
```

スクリプト内の `year` と `month` を編集して、取得する期間を指定します。

```python
year = 2019  # 取得する年
month = 1    # 取得する月
```

取得したURLは `data/urls/` に保存されます。

### ステップ2: HTMLを取得

```bash
python3 2_fetch_html.py
```

ステップ1で取得したURLからHTMLをダウンロードします。
HTMLは `data/html/年/月/` に保存されます。

**注意:** サーバーに負荷をかけないよう、各リクエストの間に5秒の待機時間を設けています。
大量のデータを取得する場合は時間がかかります。

### ステップ3: CSVに変換

```bash
python3 3_parse_to_csv.py
```

ステップ2で取得したHTMLを解析してCSVを生成します。
CSVは `data/csv/` に保存されます。

## 出力データ

### レースデータ (race-YYYY-MM.csv)

| カラム名 | 説明 |
|---------|------|
| race_id | レースID |
| race_round | ラウンド数 |
| race_title | レースタイトル |
| course_info | コース情報 |
| weather | 天候 |
| ground_state | 馬場状態 |
| date | 日時 |
| venue | 競馬場 |
| first_place_horse | 1着馬番 |
| second_place_horse | 2着馬番 |
| third_place_horse | 3着馬番 |

### 馬データ (horse-YYYY-MM.csv)

| カラム名 | 説明 |
|---------|------|
| race_id | レースID |
| rank | 着順 |
| horse_id | 馬ID |
| horse_number | 馬番 |
| waku_number | 枠番 |
| sex_age | 性別年齢 |
| weight_burden | 負担重量 |
| horse_weight | 馬体重 |
| horse_weight_diff | 馬体重差 |
| time | タイム |
| margin | 着差 |
| last_3f | 上がり3F |
| odds | オッズ |
| popularity | 人気 |
| jockey | 騎手 |
| trainer | 調教師 |

## ディレクトリ構造

```
scraper/
├── 1_fetch_race_urls.py    # レースURL取得
├── 2_fetch_html.py          # HTML取得
├── 3_parse_to_csv.py        # CSV生成
├── requirements.txt         # Python依存関係
├── README.md               # このファイル
└── data/
    ├── urls/               # レースURL
    ├── html/               # HTML
    └── csv/                # CSV
```

## 注意事項

### Webスクレイピングに関する注意

1. **サーバーへの負荷**: 各リクエスト間に適切な待機時間（5秒）を設けています
2. **利用規約の確認**: netkeiba.comの利用規約を確認し、遵守してください
3. **個人利用**: 取得したデータは個人的な学習・研究目的でのみ使用してください
4. **商用利用**: 商用利用は禁止されている可能性があります
5. **robots.txt**: サイトのrobots.txtを確認してください

### トラブルシューティング

**ChromeDriverのエラー:**
```
selenium.common.exceptions.WebDriverException: Message: 'chromedriver' executable needs to be in PATH
```
→ ChromeDriverをインストールしてPATHに追加してください

**文字化け:**
→ EUC-JP エンコーディングの問題です。スクリプト内で `response.apparent_encoding` を使用して自動検出しています

**HTMLが取得できない:**
→ サイトの構造が変更された可能性があります。セレクタを更新する必要があるかもしれません

## カスタマイズ

### 取得期間の変更

各スクリプトの `year` と `month` 変数を編集します。

### 取得データの追加

`3_parse_to_csv.py` の `RACE_COLUMNS` と `HORSE_COLUMNS` を編集し、
`parse_race_data()` と `parse_horse_data()` 関数でデータ抽出ロジックを追加します。

### 競馬場の絞り込み

`1_fetch_race_urls.py` の競馬場選択部分を編集します。

例: 東京競馬場のみ
```python
# 中央競馬場をチェック（1〜10）の代わりに
terms = driver.find_element(By.ID, "check_Jyo_05")  # 05 = 東京
terms.click()
```

## ライセンス

MIT License

## 参考資料

- [Zenn記事: データ収集から機械学習まで全て行って競馬の予測をしてみた](https://zenn.dev/kami/articles/66e400c8a43cd08a5d7f)
- [netkeiba.com](https://netkeiba.com/)
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Beautiful Soup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

## 免責事項

このツールは教育目的で作成されています。使用によって生じたいかなる損害についても、作成者は責任を負いません。
Webスクレイピングは対象サイトの利用規約を遵守し、適切に行ってください。
