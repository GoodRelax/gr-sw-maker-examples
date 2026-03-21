"""ELM327Adapter のユニットテスト.

MockSerialPort を使用して ELM327 との通信をシミュレートする。
"""

from __future__ import annotations

import pytest

from src.adapters.elm327_adapter import (
    ELM327Adapter,
    Elm327CommunicationError,
)
from src.entities.ecu import DiagProtocolType, EcuInfo


class MockSerialPort:
    """テスト用のシリアルポートモック.

    送信されたコマンドに対して事前定義された応答を返す。
    """

    def __init__(self) -> None:
        """MockSerialPort を初期化する."""
        self._is_open: bool = False
        self._responses: dict[str, str] = {}
        self._default_response: str = "NO DATA\r\r>"
        self._sent_commands: list[str] = []
        self._call_count: int = 0

    @property
    def is_open(self) -> bool:
        """ポートが開いているかを返す."""
        return self._is_open

    def open(
        self,
        port_name: str,
        baudrate: int = 38400,
        timeout: float = 5.0,
    ) -> None:
        """シリアルポートを開く."""
        self._is_open = True

    def close(self) -> None:
        """シリアルポートを閉じる."""
        self._is_open = False

    def write(self, command: str) -> None:
        """コマンドを送信する."""
        if not self._is_open:
            msg = "Port not open"
            raise ConnectionError(msg)
        self._sent_commands.append(command)

    def read_until_prompt(self) -> str:
        """プロンプトまで読み取る."""
        if not self._is_open:
            msg = "Port not open"
            raise ConnectionError(msg)

        if self._sent_commands:
            last_command = self._sent_commands[-1]
            response = self._responses.get(last_command, self._default_response)
        else:
            response = self._default_response

        self._call_count += 1
        return response

    def set_response(self, command: str, response: str) -> None:
        """コマンドに対する応答を設定する."""
        self._responses[command] = response

    def set_default_response(self, response: str) -> None:
        """デフォルト応答を設定する."""
        self._default_response = response

    @property
    def sent_commands(self) -> list[str]:
        """送信されたコマンド一覧を返す."""
        return list(self._sent_commands)


@pytest.fixture()
def mock_serial() -> MockSerialPort:
    """MockSerialPort フィクスチャ."""
    serial = MockSerialPort()
    serial.open("COM_TEST")
    return serial


@pytest.fixture()
def adapter(mock_serial: MockSerialPort) -> ELM327Adapter:
    """ELM327Adapter フィクスチャ."""
    return ELM327Adapter(mock_serial)


class TestInitialize:
    """ELM327 初期化シーケンスのテスト."""

    def test_initialize_success(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """正常な初期化シーケンスでバージョン文字列を返す."""
        mock_serial.set_response("ATZ", "\r\rELM327 v1.5\r\r>")
        mock_serial.set_response("ATE0", "OK\r\r>")
        mock_serial.set_response("ATL0", "OK\r\r>")
        mock_serial.set_response("ATS1", "OK\r\r>")
        mock_serial.set_response("ATH1", "OK\r\r>")
        mock_serial.set_response("ATSP0", "OK\r\r>")

        version = adapter.initialize()
        assert "ELM327" in version

    def test_initialize_no_elm327_response(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """ATZ 応答に ELM327 が含まれない場合はエラー."""
        mock_serial.set_response("ATZ", "\r\rGARBAGE\r\r>")

        with pytest.raises(Elm327CommunicationError):
            adapter.initialize()

    def test_initialize_ate0_fails(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """ATE0 が失敗した場合はエラー."""
        mock_serial.set_response("ATZ", "\r\rELM327 v1.5\r\r>")
        mock_serial.set_response("ATE0", "?\r\r>")

        with pytest.raises(Elm327CommunicationError):
            adapter.initialize()


class TestSendCommand:
    """コマンド送信のテスト."""

    def test_send_command_returns_response(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """コマンド送信で応答を返す."""
        mock_serial.set_response("ATRV", "12.6V\r\r>")
        response = adapter.send_command("ATRV")
        assert "12.6V" in response

    def test_send_command_retry_on_invalid_response(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """不正応答でリトライする."""
        # 全リトライが失敗するケース
        mock_serial.set_default_response("")

        with pytest.raises(Elm327CommunicationError):
            adapter.send_command("TEST")


class TestDetectSupportedPids:
    """PID 自動検出のテスト."""

    def test_detect_pids_basic(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """PID ビットマスクのデコードが正しい."""
        # 0100 応答: 41 00 BE 3F A8 13
        # BE = 10111110 -> PIDs 01,03,04,05,06,07
        # 3F = 00111111 -> PIDs 0B,0C,0D,0E,0F,10
        # A8 = 10101000 -> PIDs 11,13,15
        # 13 = 00010011 -> PIDs 1C,1F,20
        mock_serial.set_response("0100", "41 00 BE 3F A8 13\r\r>")
        # PID 20 がサポートされているので次のグループもチェック
        mock_serial.set_response("0120", "NO DATA\r\r>")

        pids = adapter.detect_supported_pids()
        assert "01" in pids
        assert "0C" in pids
        assert "0D" in pids
        assert len(pids) > 5


class TestReadDtcs:
    """DTC 読取のテスト."""

    def test_read_dtcs_legacy_obd(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """Legacy OBD Mode 03 で DTC を読み取る."""
        # Mode 03 応答: 43 01 01 43 00 00
        # DTC: 0x01 0x43 -> P0143
        mock_serial.set_response("03", "43 01 01 43 00 00\r\r>")
        mock_serial.set_response("07", "NO DATA\r\r>")

        ecu = EcuInfo(
            ecu_identifier="7E0",
            ecu_display_name="Engine",
            protocol_type=DiagProtocolType.LEGACY_OBD,
            response_id="7E8",
        )

        dtcs = adapter.read_dtcs(ecu)
        assert len(dtcs) >= 1
        assert dtcs[0].dtc_code == "P0143"
        assert dtcs[0].protocol_type == "LEGACY_OBD"

    def test_read_dtcs_no_data(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """DTC が無い場合は空リストを返す."""
        mock_serial.set_response("03", "NO DATA\r\r>")
        mock_serial.set_response("07", "NO DATA\r\r>")

        ecu = EcuInfo(
            ecu_identifier="7E0",
            ecu_display_name="Engine",
            protocol_type=DiagProtocolType.LEGACY_OBD,
            response_id="7E8",
        )

        dtcs = adapter.read_dtcs(ecu)
        assert len(dtcs) == 0


class TestClearDtcs:
    """DTC 消去のテスト."""

    def test_clear_dtcs_legacy_success(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """Legacy OBD Mode 04 で DTC 消去成功."""
        mock_serial.set_response("04", "44\r\r>")

        ecu = EcuInfo(
            ecu_identifier="7E0",
            ecu_display_name="Engine",
            protocol_type=DiagProtocolType.LEGACY_OBD,
            response_id="7E8",
        )

        result = adapter.clear_dtcs(ecu)
        assert result is True


class TestSwitchProtocol:
    """プロトコル切替のテスト."""

    def test_switch_protocol(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """プロトコル切替が正常に動作する."""
        mock_serial.set_response("ATSP5", "OK\r\r>")

        adapter.switch_protocol(5)
        assert "ATSP5" in mock_serial.sent_commands

    def test_switch_protocol_no_op_if_same(
        self,
        mock_serial: MockSerialPort,
        adapter: ELM327Adapter,
    ) -> None:
        """同じプロトコルへの切替はスキップされる."""
        # _current_protocol は初期値 0
        adapter.switch_protocol(0)
        assert "ATSP0" not in mock_serial.sent_commands


class TestResponseValidation:
    """応答バリデーションのテスト."""

    def test_error_response_detection(self) -> None:
        """エラー応答を正しく検出する."""
        assert ELM327Adapter._is_error_response("NO DATA\r\r>") is True
        assert ELM327Adapter._is_error_response("UNABLE TO CONNECT\r\r>") is True
        assert ELM327Adapter._is_error_response("?\r\r>") is True
        assert ELM327Adapter._is_error_response("41 00 BE 3F A8 13\r\r>") is False

    def test_clean_response(self) -> None:
        """応答クリーニングが正しく動作する."""
        assert ELM327Adapter._clean_response("41 00 BE 3F\r\r>") == "4100BE3F"
        assert ELM327Adapter._clean_response("  OK \r\n >") == "OK"

    def test_hex_string_to_bytes(self) -> None:
        """hex 文字列のバイト変換が正しい."""
        result = ELM327Adapter._hex_string_to_bytes("4100BE3F")
        assert result == [0x41, 0x00, 0xBE, 0x3F]

    def test_hex_string_to_bytes_empty(self) -> None:
        """空文字列は空リストを返す."""
        assert ELM327Adapter._hex_string_to_bytes("") == []
