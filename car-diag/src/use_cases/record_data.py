"""RecordDataUseCase: TSV ファイルへのデータ記録.

traces: FR-09, FR-09a-g, NFR-02b
"""

from __future__ import annotations

import logging
import os
import time
from typing import IO, TextIO

from src.entities.vehicle_parameter import VehicleParameter

logger = logging.getLogger(__name__)

# FR-09b: 目標記録間隔
TARGET_RECORDING_INTERVAL_S: float = 0.5

# FR-09f: fsync 間隔
FSYNC_INTERVAL_S: float = 1.0


class RecordDataUseCase:
    """データ記録ユースケース.

    TSV ファイルにタイムスタンプ付きでパラメータ値を記録する。

    Attributes:
        _file_handle: 出力ファイルハンドル.
        _header_columns: ヘッダーカラム名のリスト.
        _last_fsync_epoch: 最終 fsync 時刻.
        _row_count: 記録行数.
        _recording_active: 記録実行中フラグ.
    """

    def __init__(self) -> None:
        """RecordDataUseCase を初期化する."""
        self._file_handle: TextIO | None = None
        self._header_columns: list[str] = []
        self._last_fsync_epoch: float = 0.0
        self._row_count: int = 0
        self._recording_active: bool = False

    @property
    def is_recording(self) -> bool:
        """記録中かを返す."""
        return self._recording_active

    @property
    def row_count(self) -> int:
        """記録行数を返す."""
        return self._row_count

    def start_recording(
        self,
        file_path: str,
        parameter_names: list[str],
    ) -> None:
        """記録を開始し、TSV ファイルのヘッダー行を書き込む.

        Args:
            file_path: 出力 TSV ファイルパス.
            parameter_names: パラメータ名のリスト.

        Raises:
            OSError: ファイルを開けない場合.
        """
        self._header_columns = ["timestamp"] + parameter_names

        try:
            self._file_handle = open(file_path, "w", encoding="utf-8")  # noqa: SIM115
        except OSError:
            logger.exception(
                "Failed to open recording file",
                extra={"file_path": file_path},
            )
            raise

        # FR-09c: ヘッダー行を出力
        header_line = "\t".join(self._header_columns)
        self._file_handle.write(header_line + "\n")
        self._last_fsync_epoch = time.time()
        self._row_count = 0
        self._recording_active = True

        logger.info(
            "Data recording started",
            extra={
                "file_path": file_path,
                "parameter_count": len(parameter_names),
            },
        )

    def write_row(
        self,
        timestamp_iso: str,
        parameters: list[VehicleParameter],
    ) -> None:
        """1 行分のデータを TSV ファイルに書き込む.

        Args:
            timestamp_iso: ISO 8601 形式のタイムスタンプ文字列.
            parameters: パラメータ読取結果のリスト.

        Raises:
            OSError: 書き込みに失敗した場合（FR-09g: ディスクフル等）.
        """
        if self._file_handle is None or not self._recording_active:
            return

        # パラメータ名→値のマッピングを構築
        param_by_identifier: dict[str, str] = {}
        for param in parameters:
            if param.physical_value is not None:
                param_by_identifier[param.parameter_identifier] = str(
                    param.physical_value,
                )
            else:
                param_by_identifier[param.parameter_identifier] = param.raw_hex

        # ヘッダーカラム順にデータを並べる
        row_values = [timestamp_iso]
        for col_name in self._header_columns[1:]:
            row_values.append(param_by_identifier.get(col_name, ""))

        row_line = "\t".join(row_values)

        try:
            self._file_handle.write(row_line + "\n")
            self._row_count += 1
        except OSError:
            # FR-09g: 書き込み失敗時は記録を停止
            logger.exception(
                "TSV write failed, stopping recording",
                extra={"row_count": self._row_count},
            )
            self.stop_recording()
            raise

        # FR-09f: 1 秒間隔で fsync
        now = time.time()
        if now - self._last_fsync_epoch >= FSYNC_INTERVAL_S:
            self._flush_and_sync()
            self._last_fsync_epoch = now

    def stop_recording(self) -> None:
        """記録を停止し、TSV ファイルを閉じる.

        traces: FR-09d
        """
        self._recording_active = False

        if self._file_handle is not None:
            try:
                self._flush_and_sync()
                self._file_handle.close()
            except OSError:
                logger.exception("Error closing TSV file")
            finally:
                self._file_handle = None

        logger.info(
            "Data recording stopped",
            extra={"total_rows": self._row_count},
        )

    def flush_for_comm_loss(self) -> None:
        """通信断時に TSV ファイルをフラッシュして閉じる.

        FR-02a, FR-09f: 通信断ハンドリングの一部として、
        データ損失を最大 1 秒分に抑える。
        """
        logger.info(
            "Flushing TSV file due to communication loss",
            extra={"row_count": self._row_count},
        )
        self.stop_recording()

    def _flush_and_sync(self) -> None:
        """ファイルバッファをフラッシュし、OS レベルの fsync を実行する."""
        if self._file_handle is not None and not self._file_handle.closed:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
