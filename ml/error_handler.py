"""
エラーハンドリングユーティリティ

統一されたエラー処理とロギングを提供します。
"""

import logging
import traceback
import sys
from functools import wraps
from typing import Optional, Callable, Any

# ロガーの設定
logger = logging.getLogger(__name__)

class KeibaError(Exception):
    """競馬予測システムの基底例外クラス"""
    pass

class DataError(KeibaError):
    """データ関連のエラー"""
    pass

class ModelError(KeibaError):
    """モデル関連のエラー"""
    pass

class ScrapingError(KeibaError):
    """スクレイピング関連のエラー"""
    pass

class ValidationError(KeibaError):
    """バリデーション関連のエラー"""
    pass


def safe_execute(
    func: Callable,
    default_return: Any = None,
    error_message: Optional[str] = None,
    log_traceback: bool = True,
    raise_exception: bool = False
) -> Any:
    """
    関数を安全に実行し、エラーハンドリングを統一します。

    Args:
        func: 実行する関数
        default_return: エラー時のデフォルト戻り値
        error_message: カスタムエラーメッセージ
        log_traceback: トレースバックをログに記録するか
        raise_exception: 例外を再発生させるか

    Returns:
        関数の戻り値、またはエラー時はdefault_return

    Example:
        result = safe_execute(
            lambda: risky_function(),
            default_return=0,
            error_message="計算に失敗しました"
        )
    """
    try:
        return func()
    except Exception as e:
        msg = error_message or f"Error in {func.__name__ if hasattr(func, '__name__') else 'function'}: {e}"
        logger.error(msg)

        if log_traceback:
            logger.debug(traceback.format_exc())

        if raise_exception:
            raise

        return default_return


def handle_errors(
    default_return: Any = None,
    error_message: Optional[str] = None,
    log_traceback: bool = True
):
    """
    デコレータ：関数のエラーハンドリングを自動化

    Args:
        default_return: エラー時のデフォルト戻り値
        error_message: カスタムエラーメッセージ
        log_traceback: トレースバックをログに記録するか

    Example:
        @handle_errors(default_return=pd.DataFrame(), error_message="データ処理失敗")
        def process_data(df):
            # 処理
            return df
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                msg = error_message or f"Error in {func.__name__}: {e}"
                logger.error(msg)

                if log_traceback:
                    logger.debug(traceback.format_exc())

                return default_return
        return wrapper
    return decorator


def validate_dataframe(df, required_columns: list, min_rows: int = 1) -> None:
    """
    DataFrameのバリデーション

    Args:
        df: 検証するDataFrame
        required_columns: 必須カラムのリスト
        min_rows: 最小行数

    Raises:
        ValidationError: バリデーション失敗時
    """
    if df is None:
        raise ValidationError("DataFrameがNoneです")

    if len(df) < min_rows:
        raise ValidationError(f"データが不足しています（{len(df)}行 < {min_rows}行）")

    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"必須カラムが見つかりません: {missing_cols}")


def validate_model(model, required_methods: list = None) -> None:
    """
    モデルのバリデーション

    Args:
        model: 検証するモデル
        required_methods: 必須メソッドのリスト

    Raises:
        ValidationError: バリデーション失敗時
    """
    if model is None:
        raise ValidationError("モデルがNoneです")

    if required_methods is None:
        required_methods = ['predict']

    missing_methods = [method for method in required_methods
                      if not hasattr(model, method)]
    if missing_methods:
        raise ValidationError(f"モデルに必須メソッドがありません: {missing_methods}")


def log_error(message: str, exception: Optional[Exception] = None,
              include_traceback: bool = True) -> None:
    """
    エラーをログに記録

    Args:
        message: エラーメッセージ
        exception: 例外オブジェクト（オプション）
        include_traceback: トレースバックを含めるか
    """
    if exception:
        logger.error(f"{message}: {exception}")
    else:
        logger.error(message)

    if include_traceback:
        logger.debug(traceback.format_exc())


def setup_logger(name: str, level: int = logging.INFO,
                log_file: Optional[str] = None) -> logging.Logger:
    """
    ロガーのセットアップ

    Args:
        name: ロガー名
        level: ログレベル
        log_file: ログファイルパス（オプション）

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラー（オプション）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 使用例
if __name__ == "__main__":
    # ロガーのセットアップ
    test_logger = setup_logger(__name__, logging.DEBUG)

    # デコレータの使用例
    @handle_errors(default_return=0, error_message="計算エラー")
    def risky_division(a, b):
        return a / b

    print(f"正常: {risky_division(10, 2)}")  # 5.0
    print(f"エラー: {risky_division(10, 0)}")  # 0（エラーログ出力）

    # バリデーションの使用例
    import pandas as pd
    df = pd.DataFrame({'a': [1, 2, 3]})

    try:
        validate_dataframe(df, required_columns=['a', 'b'])
    except ValidationError as e:
        print(f"バリデーションエラー: {e}")

    print("✅ エラーハンドラーモジュール正常")
