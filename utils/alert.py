"""
リアルタイム監視・アラート機能
期待値の高いレースを自動検出
"""

import json
import os
from datetime import datetime


class RaceAlert:
    """
    レースアラートクラス
    """

    def __init__(self):
        self.alert_threshold = 0.3  # EV > 0.3 をアラート対象に

    def check_high_ev_races(self, race_predictions):
        """
        期待値の高いレースをチェック

        Args:
            race_predictions: レース予測結果のリスト
                [
                    {
                        'race_id': '202506050101',
                        'race_name': '2歳未勝利',
                        'venue': '中山',
                        'horses': [
                            {'horse_name': 'xxx', 'ai_prob': 0.75, 'ev': 0.5},
                            ...
                        ]
                    },
                    ...
                ]

        Returns:
            list: アラート対象のレース
        """
        alerts = []

        for race in race_predictions:
            # 期待値の高い馬をカウント
            high_ev_horses = [
                h for h in race.get('horses', [])
                if h.get('ev', -1) > self.alert_threshold
            ]

            if len(high_ev_horses) >= 2:
                # 2頭以上いる場合はアラート
                alerts.append({
                    'race_id': race['race_id'],
                    'race_name': race.get('race_name', ''),
                    'venue': race.get('venue', ''),
                    'high_ev_count': len(high_ev_horses),
                    'high_ev_horses': high_ev_horses,
                    'timestamp': datetime.now().isoformat()
                })

        return alerts

    def format_alert_message(self, alerts):
        """
        アラートメッセージをフォーマット

        Args:
            alerts: アラートのリスト

        Returns:
            str: フォーマットされたメッセージ
        """
        if not alerts:
            return "本日は注目レースがありません。"

        messages = []
        messages.append("🔥 注目レース検出！\n")

        for alert in alerts:
            msg = f"【{alert['venue']}】{alert['race_name']}\n"
            msg += f"  期待値の高い馬: {alert['high_ev_count']}頭\n"

            for i, horse in enumerate(alert['high_ev_horses'][:3], 1):
                horse_name = horse.get('horse_name', '不明')
                ai_prob = horse.get('ai_prob', 0) * 100
                ev = horse.get('ev', 0)
                msg += f"  {i}. {horse_name} (AI: {ai_prob:.0f}%, EV: {ev:+.2f})\n"

            messages.append(msg)

        return "\n".join(messages)

    def save_alerts(self, alerts, filepath='alerts.json'):
        """
        アラートをファイルに保存

        Args:
            alerts: アラートのリスト
            filepath: 保存先ファイルパス
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(alerts, f, ensure_ascii=False, indent=2)
            print(f"✅ Alerts saved to {filepath}")
        except Exception as e:
            print(f"❌ Failed to save alerts: {e}")

    def load_alerts(self, filepath='alerts.json'):
        """
        保存されたアラートを読み込み

        Args:
            filepath: ファイルパス

        Returns:
            list: アラートのリスト
        """
        if not os.path.exists(filepath):
            return []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load alerts: {e}")
            return []


def send_line_notify(message, token):
    """
    LINE Notifyで通知を送信

    Args:
        message: メッセージ
        token: LINE Notify トークン

    Returns:
        bool: 成功したかどうか
    """
    try:
        import requests

        url = "https://notify-api.line.me/api/notify"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        data = {
            "message": message
        }

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            print("✅ LINE通知送信成功")
            return True
        else:
            print(f"❌ LINE通知送信失敗: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ LINE通知エラー: {e}")
        return False


def send_slack_notification(message, webhook_url):
    """
    Slackに通知を送信

    Args:
        message: メッセージ
        webhook_url: Slack Incoming Webhook URL

    Returns:
        bool: 成功したかどうか
    """
    try:
        import requests

        payload = {
            "text": message
        }

        response = requests.post(webhook_url, json=payload)

        if response.status_code == 200:
            print("✅ Slack通知送信成功")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Slack通知エラー: {e}")
        return False


if __name__ == "__main__":
    # Test
    alert_system = RaceAlert()

    # Sample data
    sample_predictions = [
        {
            'race_id': '202506050101',
            'race_name': '2歳未勝利',
            'venue': '中山',
            'horses': [
                {'horse_name': 'ビップムーラン', 'ai_prob': 0.75, 'ev': 0.5},
                {'horse_name': 'アンバサダネージュ', 'ai_prob': 0.65, 'ev': 0.35},
                {'horse_name': 'コウユーニポポニコ', 'ai_prob': 0.45, 'ev': 0.1},
            ]
        },
        {
            'race_id': '202506050102',
            'race_name': '1勝クラス',
            'venue': '中山',
            'horses': [
                {'horse_name': 'テストホース1', 'ai_prob': 0.50, 'ev': 0.05},
                {'horse_name': 'テストホース2', 'ai_prob': 0.40, 'ev': -0.1},
            ]
        }
    ]

    # Check for high EV races
    alerts = alert_system.check_high_ev_races(sample_predictions)

    # Format message
    message = alert_system.format_alert_message(alerts)

    print(message)

    # Save alerts
    alert_system.save_alerts(alerts)

    # Note: LINE/Slack notification requires tokens/webhooks
    # Uncomment and add tokens to use:
    # send_line_notify(message, "YOUR_LINE_TOKEN")
    # send_slack_notification(message, "YOUR_SLACK_WEBHOOK_URL")
