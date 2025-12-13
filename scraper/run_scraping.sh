#!/bin/bash

# プロジェクトディレクトリへ移動 (絶対パス推奨だが、ユーザー環境依存するため相対で設定しcron登録時に注意書き残す)
# ここではユーザーのパスがわかってるので絶対パスで書くのもありだが、汎用性のため $HOME を使う
cd "$HOME/Program/dai-keiba/scraper"

# 仮想環境やパスの設定が必要な場合はここに記述
# 例: source .venv/bin/activate
# 今回はシステムPythonを使う想定

# 実行
python3 auto_scraper.py >> scraping.log 2>&1

echo "Scraping finished at $(date)" >> scraping.log
