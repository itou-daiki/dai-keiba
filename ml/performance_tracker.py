"""
パフォーマンストラッキング - 予測vs実結果の記録・分析

予測精度の経時変化を追跡し、モデルの劣化を検出
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceTracker:
    """モデルの予測と実結果を追跡するクラス"""

    def __init__(self, tracking_file='ml/performance_tracking.jsonl'):
        """
        Args:
            tracking_file: 追跡データを保存するJSONLファイルパス
        """
        self.tracking_file = tracking_file
        os.makedirs(os.path.dirname(tracking_file), exist_ok=True)

    def log_prediction(self, race_id, horse_id, horse_name, ai_prob, actual_rank=None, metadata=None):
        """
        予測を記録

        Args:
            race_id: レースID
            horse_id: 馬ID
            horse_name: 馬名
            ai_prob: AI予測確率
            actual_rank: 実際の着順（レース後に更新）
            metadata: その他のメタデータ（オッズなど）
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'race_id': race_id,
            'horse_id': horse_id,
            'horse_name': horse_name,
            'ai_prob': float(ai_prob),
            'predicted_win': bool(ai_prob > 0.5),
            'actual_rank': actual_rank,
            'actual_win': bool(actual_rank == 1) if actual_rank is not None else None,
            'metadata': metadata or {}
        }

        # JSONL形式で追記
        with open(self.tracking_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        logger.debug(f"Logged prediction for {horse_name} in race {race_id}")

    def update_actual_result(self, race_id, results_dict):
        """
        実際の結果を更新

        Args:
            race_id: レースID
            results_dict: {horse_id: actual_rank} の辞書
        """
        # 全レコードを読み込み
        records = self._load_records()

        # 該当レースの結果を更新
        updated_count = 0
        for record in records:
            if record['race_id'] == race_id and record['horse_id'] in results_dict:
                record['actual_rank'] = results_dict[record['horse_id']]
                record['actual_win'] = (results_dict[record['horse_id']] == 1)
                record['updated_at'] = datetime.now().isoformat()
                updated_count += 1

        # ファイルに書き戻し
        self._save_records(records)

        logger.info(f"Updated {updated_count} predictions for race {race_id}")

    def _load_records(self):
        """全レコードを読み込み"""
        if not os.path.exists(self.tracking_file):
            return []

        records = []
        with open(self.tracking_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def _save_records(self, records):
        """全レコードを保存"""
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def calculate_accuracy(self, start_date=None, end_date=None):
        """
        予測精度を計算

        Args:
            start_date: 開始日（ISO形式文字列）
            end_date: 終了日（ISO形式文字列）

        Returns:
            dict: 精度メトリクス
        """
        records = self._load_records()

        # 実結果が記録されているもののみフィルタ
        evaluated = [r for r in records if r['actual_rank'] is not None]

        if not evaluated:
            logger.warning("No evaluated predictions found")
            return {}

        # 日付フィルタ
        if start_date:
            evaluated = [r for r in evaluated if r['timestamp'] >= start_date]
        if end_date:
            evaluated = [r for r in evaluated if r['timestamp'] <= end_date]

        df = pd.DataFrame(evaluated)

        # メトリクス計算
        total = len(df)
        correct_predictions = sum(df['predicted_win'] == df['actual_win'])
        accuracy = correct_predictions / total if total > 0 else 0

        # 1着的中率
        predicted_wins = df[df['predicted_win'] == True]
        win_hit_rate = sum(predicted_wins['actual_win']) / len(predicted_wins) if len(predicted_wins) > 0 else 0

        # Brier Score（確率予測の精度）
        brier_score = np.mean((df['ai_prob'] - df['actual_win'].astype(float)) ** 2)

        # 実際の1着馬の平均AI確率
        actual_winners = df[df['actual_win'] == True]
        avg_prob_of_winners = actual_winners['ai_prob'].mean() if len(actual_winners) > 0 else 0

        metrics = {
            'total_predictions': total,
            'accuracy': accuracy,
            'win_hit_rate': win_hit_rate,
            'brier_score': brier_score,
            'avg_prob_of_winners': avg_prob_of_winners,
            'period': {
                'start': start_date,
                'end': end_date
            }
        }

        logger.info(f"\n=== Performance Metrics ===")
        logger.info(f"Total predictions: {total}")
        logger.info(f"Accuracy: {accuracy:.2%}")
        logger.info(f"Win hit rate: {win_hit_rate:.2%}")
        logger.info(f"Brier Score: {brier_score:.4f}")
        logger.info(f"Avg prob of winners: {avg_prob_of_winners:.2%}")

        return metrics

    def get_performance_over_time(self, interval='1W'):
        """
        時系列での性能推移を取得

        Args:
            interval: 集計間隔（'1D'=日次、'1W'=週次、'1M'=月次）

        Returns:
            DataFrame: 時系列の性能指標
        """
        records = self._load_records()
        evaluated = [r for r in records if r['actual_rank'] is not None]

        if not evaluated:
            logger.warning("No evaluated predictions found")
            return pd.DataFrame()

        df = pd.DataFrame(evaluated)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        # 期間ごとに集計
        resampled = df.resample(interval).apply(lambda x: pd.Series({
            'total': len(x),
            'accuracy': (x['predicted_win'] == x['actual_win']).mean() if len(x) > 0 else 0,
            'brier_score': np.mean((x['ai_prob'] - x['actual_win'].astype(float)) ** 2) if len(x) > 0 else 0,
            'avg_prob': x['ai_prob'].mean() if len(x) > 0 else 0
        }))

        return resampled

    def export_to_csv(self, output_path='ml/performance_tracking.csv'):
        """
        追跡データをCSVにエクスポート

        Args:
            output_path: 出力CSVパス
        """
        records = self._load_records()
        if not records:
            logger.warning("No records to export")
            return

        df = pd.DataFrame(records)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        logger.info(f"Exported {len(records)} records to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='パフォーマンストラッキング')
    parser.add_argument('--action', choices=['accuracy', 'export', 'trend'], default='accuracy',
                       help='実行するアクション')
    parser.add_argument('--start-date', help='開始日（YYYY-MM-DD）')
    parser.add_argument('--end-date', help='終了日（YYYY-MM-DD）')
    parser.add_argument('--interval', default='1W', help='集計間隔（trend用: 1D/1W/1M）')

    args = parser.parse_args()

    tracker = PerformanceTracker()

    if args.action == 'accuracy':
        metrics = tracker.calculate_accuracy(
            start_date=args.start_date,
            end_date=args.end_date
        )
        print(json.dumps(metrics, indent=2, ensure_ascii=False))

    elif args.action == 'export':
        tracker.export_to_csv()
        print("✅ Exported to ml/performance_tracking.csv")

    elif args.action == 'trend':
        trend_df = tracker.get_performance_over_time(interval=args.interval)
        print(trend_df)
        print(f"\n✅ Performance trend ({args.interval} intervals)")
