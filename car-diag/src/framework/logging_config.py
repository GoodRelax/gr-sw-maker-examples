"""ログ設定: 構造化 JSON ログフォーマッタとハンドラ構成.

構造化 JSON 形式のログを提供する。
- ファイルハンドラ: ~/.car-diag/logs/ に日次ローテーション
- コンソールハンドラ: 開発用テキスト出力

traces: NFR-05, FR-02d
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# デフォルトのログディレクトリ
_DEFAULT_LOG_DIR = Path.home() / ".car-diag" / "logs"

# ログファイル名
_LOG_FILE_NAME = "car-diag.log"


class StructuredJsonFormatter(logging.Formatter):
    """構造化 JSON ログフォーマッタ.

    ログレコードを JSON 形式で出力する。
    extra パラメータの内容をフラットに展開する。
    """

    def format(self, record: logging.LogRecord) -> str:
        """ログレコードを JSON 文字列にフォーマットする.

        Args:
            record: ログレコード.

        Returns:
            JSON 形式のログ文字列.
        """
        log_entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # extra フィールドを展開
        # logging モジュールの内部属性を除外
        _excluded_attrs = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "pathname", "filename", "module", "levelno", "levelname",
            "msecs", "thread", "threadName", "process", "processName",
            "message", "taskName",
        }
        for attr_name, attr_value in record.__dict__.items():
            if attr_name not in _excluded_attrs and not attr_name.startswith("_"):
                try:
                    json.dumps(attr_value)
                    log_entry[attr_name] = attr_value
                except (TypeError, ValueError):
                    log_entry[attr_name] = str(attr_value)

        # 例外情報
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """コンソール用のテキストフォーマッタ.

    開発時の可読性を重視したフォーマット。
    """

    FORMAT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"

    def __init__(self) -> None:
        """ConsoleFormatter を初期化する."""
        super().__init__(fmt=self.FORMAT, datefmt="%Y-%m-%d %H:%M:%S")


def configure_logging(
    log_level: int = logging.INFO,
    log_dir: Path | None = None,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """アプリケーションのログ設定を初期化する.

    Args:
        log_level: ログレベル (logging.DEBUG, INFO, WARNING, ERROR).
        log_dir: ログ出力ディレクトリ。None の場合はデフォルト.
        enable_console: コンソールハンドラを有効にするか.
        enable_file: ファイルハンドラを有効にするか.
    """
    resolved_log_dir = log_dir or _DEFAULT_LOG_DIR

    # ルートロガーを設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 既存のハンドラをクリア
    root_logger.handlers.clear()

    # コンソールハンドラ
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(ConsoleFormatter())
        root_logger.addHandler(console_handler)

    # ファイルハンドラ (日次ローテーション)
    if enable_file:
        try:
            resolved_log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = resolved_log_dir / _LOG_FILE_NAME

            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(log_file_path),
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(StructuredJsonFormatter())
            root_logger.addHandler(file_handler)

        except OSError:
            # ファイルハンドラの設定に失敗しても、コンソールログは継続
            if enable_console:
                root_logger.warning(
                    "Failed to configure file logging",
                    extra={"log_dir": str(resolved_log_dir)},
                )

    # src パッケージのロガーレベルを明示的に設定
    src_logger = logging.getLogger("src")
    src_logger.setLevel(log_level)
