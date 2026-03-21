"""EcuInfo と DiagProtocolType のテスト."""

from __future__ import annotations

import pytest

from src.entities.ecu import DiagProtocolType, EcuInfo


class TestDiagProtocolType:
    """DiagProtocolType 列挙のテスト."""

    def test_protocol_count(self) -> None:
        """3 つのプロトコルが定義されている."""
        assert len(DiagProtocolType) == 3

    def test_protocol_values(self) -> None:
        """プロトコル値の確認."""
        assert DiagProtocolType.LEGACY_OBD == "LEGACY_OBD"
        assert DiagProtocolType.UDS == "UDS"
        assert DiagProtocolType.KWP2000 == "KWP2000"


class TestEcuInfo:
    """EcuInfo データクラスのテスト."""

    def test_can_ecu_creation(self) -> None:
        """CAN ECU の生成."""
        ecu = EcuInfo(
            ecu_identifier="7E0",
            ecu_display_name="Engine",
            protocol_type=DiagProtocolType.UDS,
            response_id="7E8",
        )
        assert ecu.ecu_identifier == "7E0"
        assert ecu.ecu_display_name == "Engine"
        assert ecu.protocol_type == DiagProtocolType.UDS
        assert ecu.response_id == "7E8"

    def test_kwp_ecu_creation(self) -> None:
        """KWP2000 ECU の生成."""
        ecu = EcuInfo(
            ecu_identifier="10",
            ecu_display_name="ABS",
            protocol_type=DiagProtocolType.KWP2000,
            response_id="10",
        )
        assert ecu.protocol_type == DiagProtocolType.KWP2000

    def test_ecu_is_frozen(self) -> None:
        """EcuInfo は不変."""
        ecu = EcuInfo("7E0", "Engine", DiagProtocolType.UDS, "7E8")
        with pytest.raises(AttributeError):
            ecu.ecu_identifier = "7E1"  # type: ignore[misc]

    def test_ecu_equality(self) -> None:
        """同一属性の ECU は等価."""
        ecu1 = EcuInfo("7E0", "Engine", DiagProtocolType.UDS, "7E8")
        ecu2 = EcuInfo("7E0", "Engine", DiagProtocolType.UDS, "7E8")
        assert ecu1 == ecu2
