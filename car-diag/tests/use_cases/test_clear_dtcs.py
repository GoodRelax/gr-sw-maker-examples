"""ClearDtcsUseCase のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.entities.ecu import DiagProtocolType, EcuInfo
from src.use_cases.clear_dtcs import ClearDtcsUseCase


def _make_ecu(
    identifier: str = "7E0",
    protocol: DiagProtocolType = DiagProtocolType.UDS,
) -> EcuInfo:
    """テスト用 ECU を生成する."""
    return EcuInfo(identifier, "TestECU", protocol, "7E8")


class TestClearDtcsUseCase:
    """ClearDtcsUseCase のテスト."""

    def test_successful_clear(self) -> None:
        """DTC 消去成功."""
        diag_protocol = MagicMock()
        diag_protocol.clear_dtcs.return_value = True

        ecu = _make_ecu()
        use_case = ClearDtcsUseCase(diag_protocol)
        result = use_case.execute([ecu])

        assert result["7E0"] is True

    def test_clear_failure(self) -> None:
        """DTC 消去が否定応答を返した場合."""
        diag_protocol = MagicMock()
        diag_protocol.clear_dtcs.return_value = False

        ecu = _make_ecu()
        use_case = ClearDtcsUseCase(diag_protocol)
        result = use_case.execute([ecu])

        assert result["7E0"] is False

    def test_clear_exception_returns_false(self) -> None:
        """DTC 消去で例外が発生した場合は False."""
        diag_protocol = MagicMock()
        diag_protocol.clear_dtcs.side_effect = ConnectionError("Comm loss")

        ecu = _make_ecu()
        use_case = ClearDtcsUseCase(diag_protocol)
        result = use_case.execute([ecu])

        assert result["7E0"] is False

    def test_clear_multiple_ecus(self) -> None:
        """複数 ECU の DTC 消去."""
        diag_protocol = MagicMock()
        diag_protocol.clear_dtcs.side_effect = [True, False]

        ecu1 = _make_ecu("7E0")
        ecu2 = _make_ecu("7E2")
        use_case = ClearDtcsUseCase(diag_protocol)
        result = use_case.execute([ecu1, ecu2])

        assert result["7E0"] is True
        assert result["7E2"] is False
