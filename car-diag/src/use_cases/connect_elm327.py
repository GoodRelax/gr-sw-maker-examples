"""ConnectElm327UseCase: ELM327 初期化シーケンスの実行と PID 自動検出.

traces: FR-01b, FR-01c, FR-02, HWR-03, HWR-04, HWR-05
"""

from __future__ import annotations

import logging
import time

from src.entities.connection_state import ConnectionState, is_valid_transition
from src.use_cases.protocols import DiagProtocol, SerialPort

logger = logging.getLogger(__name__)


class ConnectElm327UseCase:
    """ELM327 接続ユースケース.

    ELM327 初期化シーケンス（ATZ, ATE0, ATL0, ATS1, ATH1, ATSP0）を実行し、
    PID 自動検出を行う。

    Attributes:
        _serial_port: シリアルポート抽象インターフェース.
        _diag_protocol: 診断プロトコル抽象インターフェース.
        _current_state: 現在の接続状態.
    """

    def __init__(
        self,
        serial_port: SerialPort,
        diag_protocol: DiagProtocol,
    ) -> None:
        """ConnectElm327UseCase を初期化する.

        Args:
            serial_port: シリアルポート抽象インターフェース.
            diag_protocol: 診断プロトコル抽象インターフェース.
        """
        self._serial_port = serial_port
        self._diag_protocol = diag_protocol
        self._current_state = ConnectionState.S_DISCONNECTED

    @property
    def current_state(self) -> ConnectionState:
        """現在の接続状態を返す."""
        return self._current_state

    def _transition_to(self, next_state: ConnectionState) -> None:
        """状態を遷移させる.

        Args:
            next_state: 遷移先の状態.

        Raises:
            RuntimeError: 無効な状態遷移の場合.
        """
        if not is_valid_transition(self._current_state, next_state):
            msg = (
                f"Invalid state transition: "
                f"{self._current_state} -> {next_state}"
            )
            raise RuntimeError(msg)

        previous_state = self._current_state
        self._current_state = next_state
        logger.info(
            "State transition",
            extra={
                "previous_state": previous_state,
                "next_state": next_state,
            },
        )

    def connect(
        self,
        port_name: str,
        baudrate: int = 38400,
        timeout: float = 5.0,
    ) -> list[str]:
        """ELM327 に接続し、PID 自動検出を行う.

        Args:
            port_name: COM ポート名（例: "COM3"）.
            baudrate: ボーレート.
            timeout: タイムアウト秒数.

        Returns:
            検出された PID の hex 文字列リスト.

        Raises:
            ConnectionError: 接続に失敗した場合.
            TimeoutError: 初期化シーケンスがタイムアウトした場合.
            RuntimeError: ELM327 が正しく応答しない場合.
        """
        self._transition_to(ConnectionState.S_CONNECTING)
        start_time = time.monotonic()

        try:
            # シリアルポートを開く
            self._serial_port.open(port_name, baudrate, timeout)
            logger.info(
                "Serial port opened",
                extra={"port_name": port_name, "baudrate": baudrate},
            )

            # ELM327 初期化シーケンス実行
            elm_version = self._diag_protocol.initialize()
            logger.info(
                "ELM327 initialized",
                extra={"elm_version": elm_version},
            )

            # PID 自動検出（FR-01c）
            supported_pids = self._diag_protocol.detect_supported_pids()
            logger.info(
                "Supported PIDs detected",
                extra={
                    "pid_count": len(supported_pids),
                    "pids": supported_pids,
                },
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            if elapsed_ms > 10000:
                logger.warning(
                    "Connection took longer than 10s",
                    extra={"elapsed_ms": elapsed_ms},
                )

            self._transition_to(ConnectionState.S_CONNECTED)
            return supported_pids

        except Exception:
            logger.exception(
                "Connection failed",
                extra={"port_name": port_name},
            )
            self._safe_close()
            self._transition_to(ConnectionState.S_ERROR)
            raise

    def disconnect(self) -> None:
        """ELM327 から切断する.

        traces: FR-01d
        """
        self._safe_close()
        # S_CONNECTED -> S_DISCONNECTED or S_ERROR -> S_DISCONNECTED
        if self._current_state != ConnectionState.S_DISCONNECTED:
            self._transition_to(ConnectionState.S_DISCONNECTED)

    def _safe_close(self) -> None:
        """シリアルポートを安全に閉じる."""
        try:
            self._serial_port.close()
        except Exception:
            logger.exception("Error closing serial port")
