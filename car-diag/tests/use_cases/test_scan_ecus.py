"""ScanEcusUseCase のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.entities.ecu import DiagProtocolType, EcuInfo
from src.use_cases.scan_ecus import ScanEcusUseCase


class TestScanEcusUseCase:
    """ScanEcusUseCase のテスト."""

    def test_successful_scan_returns_ecus(self) -> None:
        """ECU が検出された場合のテスト."""
        diag_protocol = MagicMock()
        expected_ecus = [
            EcuInfo("7E0", "Engine", DiagProtocolType.UDS, "7E8"),
            EcuInfo("7E2", "Transmission", DiagProtocolType.UDS, "7EA"),
        ]
        diag_protocol.scan_ecus.return_value = expected_ecus

        use_case = ScanEcusUseCase(diag_protocol)
        result = use_case.execute()

        assert result == expected_ecus
        assert len(result) == 2

    def test_no_ecus_detected_raises_runtime_error(self) -> None:
        """FR-03f: ECU が 0 台の場合 RuntimeError."""
        diag_protocol = MagicMock()
        diag_protocol.scan_ecus.return_value = []

        use_case = ScanEcusUseCase(diag_protocol)

        with pytest.raises(RuntimeError, match="ECU が検出されませんでした"):
            use_case.execute()

    def test_progress_callback_is_passed(self) -> None:
        """進捗コールバックが DiagProtocol に渡される."""
        diag_protocol = MagicMock()
        diag_protocol.scan_ecus.return_value = [
            EcuInfo("7E0", "Engine", DiagProtocolType.UDS, "7E8"),
        ]

        progress_fn = MagicMock()
        use_case = ScanEcusUseCase(diag_protocol)
        use_case.execute(on_progress=progress_fn)

        diag_protocol.scan_ecus.assert_called_once_with(
            on_progress=progress_fn,
        )

    def test_mixed_protocol_ecus(self) -> None:
        """CAN + KWP の混合 ECU リスト."""
        diag_protocol = MagicMock()
        diag_protocol.scan_ecus.return_value = [
            EcuInfo("7E0", "Engine", DiagProtocolType.UDS, "7E8"),
            EcuInfo("10", "ABS", DiagProtocolType.KWP2000, "10"),
        ]

        use_case = ScanEcusUseCase(diag_protocol)
        result = use_case.execute()

        assert result[0].protocol_type == DiagProtocolType.UDS
        assert result[1].protocol_type == DiagProtocolType.KWP2000
