"""ReadDtcsUseCase のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.entities.dtc import DTC
from src.entities.ecu import DiagProtocolType, EcuInfo
from src.use_cases.read_dtcs import ReadDtcsUseCase


def _make_ecu(
    identifier: str = "7E0",
    protocol: DiagProtocolType = DiagProtocolType.UDS,
) -> EcuInfo:
    """テスト用 ECU を生成する."""
    return EcuInfo(identifier, "TestECU", protocol, identifier.replace("E0", "E8"))


class TestReadDtcsUseCase:
    """ReadDtcsUseCase のテスト."""

    def test_read_dtcs_with_description(self) -> None:
        """DTC 読取結果に説明文が付与される."""
        diag_protocol = MagicMock()
        dtc_provider = MagicMock()

        raw_dtc = DTC("P0143", 0x08, "", "7E0", "UDS")
        diag_protocol.read_dtcs.return_value = [raw_dtc]
        dtc_provider.lookup.return_value = "O2 Sensor Circuit Low Voltage"

        ecu = _make_ecu()
        use_case = ReadDtcsUseCase(diag_protocol, dtc_provider)
        result = use_case.execute([ecu])

        assert "7E0" in result
        assert len(result["7E0"]) == 1
        assert result["7E0"][0].description == "O2 Sensor Circuit Low Voltage"

    def test_read_dtcs_no_dtcs_found(self) -> None:
        """DTC が 0 件の場合は空リスト."""
        diag_protocol = MagicMock()
        dtc_provider = MagicMock()
        diag_protocol.read_dtcs.return_value = []

        ecu = _make_ecu()
        use_case = ReadDtcsUseCase(diag_protocol, dtc_provider)
        result = use_case.execute([ecu])

        assert result["7E0"] == []

    def test_read_dtcs_multiple_ecus(self) -> None:
        """複数 ECU からの DTC 読取."""
        diag_protocol = MagicMock()
        dtc_provider = MagicMock()
        dtc_provider.lookup.return_value = "Unknown"

        ecu1 = _make_ecu("7E0")
        ecu2 = _make_ecu("7E2")

        diag_protocol.read_dtcs.side_effect = [
            [DTC("P0143", 0x08, "", "7E0", "UDS")],
            [DTC("P0300", 0x01, "", "7E2", "UDS"),
             DTC("P0420", 0x02, "", "7E2", "UDS")],
        ]

        use_case = ReadDtcsUseCase(diag_protocol, dtc_provider)
        result = use_case.execute([ecu1, ecu2])

        assert len(result["7E0"]) == 1
        assert len(result["7E2"]) == 2

    def test_read_dtcs_ecu_failure_returns_empty(self) -> None:
        """ECU からの読取失敗時は空リスト."""
        diag_protocol = MagicMock()
        dtc_provider = MagicMock()
        diag_protocol.read_dtcs.side_effect = ConnectionError("Comm loss")

        ecu = _make_ecu()
        use_case = ReadDtcsUseCase(diag_protocol, dtc_provider)
        result = use_case.execute([ecu])

        assert result["7E0"] == []

    def test_unknown_dtc_description(self) -> None:
        """説明文がない DTC は 'Unknown' が付与される."""
        diag_protocol = MagicMock()
        dtc_provider = MagicMock()
        dtc_provider.lookup.return_value = "Unknown"

        raw_dtc = DTC("P1234", 0x08, "", "7E0", "UDS")
        diag_protocol.read_dtcs.return_value = [raw_dtc]

        ecu = _make_ecu()
        use_case = ReadDtcsUseCase(diag_protocol, dtc_provider)
        result = use_case.execute([ecu])

        assert result["7E0"][0].description == "Unknown"
