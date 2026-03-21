"""ConnectElm327UseCase のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.entities.connection_state import ConnectionState
from src.use_cases.connect_elm327 import ConnectElm327UseCase


def _make_mocks() -> tuple[MagicMock, MagicMock]:
    """テスト用モックを生成する."""
    serial_port = MagicMock()
    serial_port.is_open = False
    diag_protocol = MagicMock()
    diag_protocol.initialize.return_value = "ELM327 v1.5"
    diag_protocol.detect_supported_pids.return_value = ["0C", "0D", "05"]
    return serial_port, diag_protocol


class TestConnectElm327UseCase:
    """ConnectElm327UseCase のテスト."""

    def test_successful_connection(self) -> None:
        """正常接続: S_DISCONNECTED -> S_CONNECTING -> S_CONNECTED."""
        serial_port, diag_protocol = _make_mocks()
        use_case = ConnectElm327UseCase(serial_port, diag_protocol)

        pids = use_case.connect("COM3")

        assert use_case.current_state == ConnectionState.S_CONNECTED
        serial_port.open.assert_called_once_with("COM3", 38400, 5.0)
        diag_protocol.initialize.assert_called_once()
        diag_protocol.detect_supported_pids.assert_called_once()
        assert pids == ["0C", "0D", "05"]

    def test_connection_failure_transitions_to_error(self) -> None:
        """接続失敗時: S_ERROR に遷移."""
        serial_port, diag_protocol = _make_mocks()
        serial_port.open.side_effect = ConnectionError("Port not found")
        use_case = ConnectElm327UseCase(serial_port, diag_protocol)

        with pytest.raises(ConnectionError):
            use_case.connect("COM99")

        assert use_case.current_state == ConnectionState.S_ERROR

    def test_initialization_failure_transitions_to_error(self) -> None:
        """初期化シーケンス失敗時: S_ERROR に遷移."""
        serial_port, diag_protocol = _make_mocks()
        diag_protocol.initialize.side_effect = RuntimeError("No ELM327")
        use_case = ConnectElm327UseCase(serial_port, diag_protocol)

        with pytest.raises(RuntimeError):
            use_case.connect("COM3")

        assert use_case.current_state == ConnectionState.S_ERROR
        serial_port.close.assert_called_once()

    def test_disconnect(self) -> None:
        """切断: S_CONNECTED -> S_DISCONNECTED."""
        serial_port, diag_protocol = _make_mocks()
        use_case = ConnectElm327UseCase(serial_port, diag_protocol)
        use_case.connect("COM3")

        use_case.disconnect()

        assert use_case.current_state == ConnectionState.S_DISCONNECTED
        serial_port.close.assert_called()

    def test_initial_state_is_disconnected(self) -> None:
        """初期状態は S_DISCONNECTED."""
        serial_port, diag_protocol = _make_mocks()
        use_case = ConnectElm327UseCase(serial_port, diag_protocol)
        assert use_case.current_state == ConnectionState.S_DISCONNECTED
