"""TsvFileWriter: TSV ファイルへのデータ書き込み.

ヘッダー行出力、fsync 間隔制御、ディスクフル時のエラーハンドリングを提供する。

traces: FR-09, FR-09c, FR-09f, FR-09g
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import TextIO

logger = logging.getLogger(__name__)

# FR-09f: fsync 間隔 (秒)
_FSYNC_INTERVAL_S: float = 1.0


class TsvFileWriter:
    """TSV ファイルライター.

    タブ区切りデータをファイルに書き込み、定期的に fsync を実行する。

    Attributes:
        _file_handle: 出力ファイルハンドル.
        _file_path: 出力ファイルパス.
        _last_fsync_epoch: 最終 fsync 時刻 (Unix epoch).
        _row_count: 書き込み行数 (ヘッダー除く).
        _closed: ファイルが閉じられたか.
    """

    def __init__(self) -> None:
        """TsvFileWriter を初期化する."""
        self._file_handle: TextIO | None = None
        self._file_path: str = ""
        self._last_fsync_epoch: float = 0.0
        self._row_count: int = 0
        self._closed: bool = True

    @property
    def row_count(self) -> int:
        """書き込み行数を返す (ヘッダー除く)."""
        return self._row_count

    @property
    def is_open(self) -> bool:
        """ファイルが開いているかを返す."""
        return not self._closed and self._file_handle is not None

    def open_file(
        self,
        file_path: str,
        header_columns: list[str],
    ) -> None:
        """TSV ファイルを開き、ヘッダー行を書き込む.

        Args:
            file_path: 出力ファイルパス.
            header_columns: ヘッダーカラム名のリスト.

        Raises:
            OSError: ファイルを開けない場合.

        traces: FR-09c
        """
        # 親ディレクトリの存在確認
        parent_dir = Path(file_path).parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._file_handle = open(  # noqa: SIM115
                file_path,
                "w",
                encoding="utf-8",
                newline="",
            )
        except OSError:
            logger.exception(
                "Failed to open TSV file",
                extra={"file_path": file_path},
            )
            raise

        self._file_path = file_path
        self._row_count = 0
        self._closed = False

        # ヘッダー行を書き込む (FR-09c)
        header_line = "\t".join(header_columns) + "\n"
        self._write_line(header_line)
        self._last_fsync_epoch = time.time()

        logger.info(
            "TSV file opened",
            extra={
                "file_path": file_path,
                "column_count": len(header_columns),
            },
        )

    def write_row(self, values: list[str]) -> None:
        """1 行分のデータを書き込む.

        Args:
            values: カラム値のリスト (ヘッダーと同じ順序).

        Raises:
            OSError: 書き込みに失敗した場合 (ディスクフル等).

        traces: FR-09f, FR-09g
        """
        if self._file_handle is None or self._closed:
            return

        row_line = "\t".join(values) + "\n"
        self._write_line(row_line)
        self._row_count += 1

        # FR-09f: fsync 間隔制御
        now = time.time()
        if now - self._last_fsync_epoch >= _FSYNC_INTERVAL_S:
            self._flush_and_sync()
            self._last_fsync_epoch = now

    def close_file(self) -> None:
        """TSV ファイルをフラッシュして閉じる (冪等).

        traces: FR-09d
        """
        if self._closed:
            return

        self._closed = True

        if self._file_handle is not None:
            try:
                self._flush_and_sync()
                self._file_handle.close()
                logger.info(
                    "TSV file closed",
                    extra={
                        "file_path": self._file_path,
                        "total_rows": self._row_count,
                    },
                )
            except OSError:
                logger.exception(
                    "Error closing TSV file",
                    extra={"file_path": self._file_path},
                )
            finally:
                self._file_handle = None

    def flush_for_emergency(self) -> None:
        """緊急フラッシュ: 通信断等の異常時にデータを保全する.

        traces: FR-02a, FR-09f
        """
        logger.info(
            "Emergency flush triggered",
            extra={
                "file_path": self._file_path,
                "row_count": self._row_count,
            },
        )
        self.close_file()

    def _write_line(self, line: str) -> None:
        """1 行をファイルに書き込む.

        Args:
            line: 書き込む行文字列.

        Raises:
            OSError: 書き込み失敗 (FR-09g).
        """
        if self._file_handle is None or self._closed:
            return

        try:
            self._file_handle.write(line)
        except OSError:
            logger.exception(
                "TSV write failed (disk full or I/O error)",
                extra={
                    "file_path": self._file_path,
                    "row_count": self._row_count,
                },
            )
            self._closed = True
            raise

    def _flush_and_sync(self) -> None:
        """ファイルバッファをフラッシュし、OS レベルの fsync を実行する.

        traces: FR-09f
        """
        if self._file_handle is not None and not self._file_handle.closed:
            try:
                self._file_handle.flush()
                os.fsync(self._file_handle.fileno())
            except OSError:
                logger.exception(
                    "fsync failed",
                    extra={"file_path": self._file_path},
                )
