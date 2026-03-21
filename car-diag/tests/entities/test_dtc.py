"""DTC エンティティのテスト.

DTC デコード関数と DTC データクラスの動作を検証する。
"""

from __future__ import annotations

import pytest

from src.entities.dtc import DTC, DtcCategory, decode_obd2_dtc, decode_uds_dtc


class TestDecodeObd2Dtc:
    """OBD-II 2バイト DTC デコードのテスト."""

    def test_powertrain_generic_code(self) -> None:
        """P0143 のデコード: high=0x01, low=0x43."""
        result = decode_obd2_dtc(0x01, 0x43)
        assert result == "P0143"

    def test_chassis_code(self) -> None:
        """C0300 のデコード: category=01 (Chassis), high=0x43, low=0x00."""
        # C0300: category bits = 01, second_digit = 00, third = 3, fourth = 0, fifth = 0
        # high byte: 01_00_0011 = 0x43, low byte: 0000_0000 = 0x00
        result = decode_obd2_dtc(0x43, 0x00)
        assert result == "C0300"

    def test_body_code(self) -> None:
        """B0100 のデコード: category=10 (Body)."""
        # B0100: category bits = 10, second_digit = 00, third = 1, fourth = 0, fifth = 0
        # high byte: 10_00_0001 = 0x81, low byte: 0000_0000 = 0x00
        result = decode_obd2_dtc(0x81, 0x00)
        assert result == "B0100"

    def test_network_code(self) -> None:
        """U0073 のデコード: category=11 (Network)."""
        # U0073: category bits = 11, second_digit = 00, third = 0, fourth = 7, fifth = 3
        # high byte: 11_00_0000 = 0xC0, low byte: 0111_0011 = 0x73
        result = decode_obd2_dtc(0xC0, 0x73)
        assert result == "U0073"

    def test_manufacturer_specific_code(self) -> None:
        """P1234 のデコード: manufacturer-specific code."""
        # P1234: category bits = 00, second_digit = 01, third = 2, fourth = 3, fifth = 4
        # high byte: 00_01_0010 = 0x12, low byte: 0011_0100 = 0x34
        result = decode_obd2_dtc(0x12, 0x34)
        assert result == "P1234"

    def test_zero_dtc(self) -> None:
        """P0000 のデコード: all zeros."""
        result = decode_obd2_dtc(0x00, 0x00)
        assert result == "P0000"

    def test_invalid_high_byte_raises_value_error(self) -> None:
        """high_byte が範囲外の場合 ValueError."""
        with pytest.raises(ValueError, match="high_byte"):
            decode_obd2_dtc(0x100, 0x00)

    def test_invalid_low_byte_raises_value_error(self) -> None:
        """low_byte が範囲外の場合 ValueError."""
        with pytest.raises(ValueError, match="low_byte"):
            decode_obd2_dtc(0x00, -1)


class TestDecodeUdsDtc:
    """UDS 3バイト DTC デコードのテスト."""

    def test_uds_dtc_with_failure_type(self) -> None:
        """UDS 3バイト DTC のデコード: P0143-07."""
        result = decode_uds_dtc(0x01, 0x43, 0x07)
        assert result == "P0143-07"

    def test_uds_dtc_failure_type_zero(self) -> None:
        """Failure Type が 0x00 の場合."""
        result = decode_uds_dtc(0x01, 0x43, 0x00)
        assert result == "P0143-00"

    def test_uds_dtc_failure_type_max(self) -> None:
        """Failure Type が 0xFF の場合."""
        result = decode_uds_dtc(0xC0, 0x73, 0xFF)
        assert result == "U0073-FF"

    def test_uds_dtc_invalid_byte3_raises_value_error(self) -> None:
        """byte3 が範囲外の場合 ValueError."""
        with pytest.raises(ValueError, match="byte3"):
            decode_uds_dtc(0x01, 0x43, 0x100)


class TestDtcCategory:
    """DtcCategory 列挙のテスト."""

    def test_category_values(self) -> None:
        """全カテゴリ値の確認."""
        assert DtcCategory.POWERTRAIN == "P"
        assert DtcCategory.CHASSIS == "C"
        assert DtcCategory.BODY == "B"
        assert DtcCategory.NETWORK == "U"

    def test_category_count(self) -> None:
        """カテゴリは 4 つ."""
        assert len(DtcCategory) == 4


class TestDtcDataclass:
    """DTC データクラスのテスト."""

    def test_dtc_creation(self) -> None:
        """DTC の生成と属性アクセス."""
        dtc = DTC(
            dtc_code="P0143",
            status_byte=0x08,
            description="O2 Sensor Circuit Low Voltage",
            ecu_identifier="7E8",
            protocol_type="LEGACY_OBD",
        )
        assert dtc.dtc_code == "P0143"
        assert dtc.status_byte == 0x08
        assert dtc.description == "O2 Sensor Circuit Low Voltage"

    def test_dtc_is_frozen(self) -> None:
        """DTC は不変（frozen）."""
        dtc = DTC(
            dtc_code="P0143",
            status_byte=0x08,
            description="Test",
            ecu_identifier="7E8",
            protocol_type="LEGACY_OBD",
        )
        with pytest.raises(AttributeError):
            dtc.dtc_code = "P0200"  # type: ignore[misc]

    def test_dtc_equality(self) -> None:
        """同一属性の DTC は等価."""
        dtc1 = DTC("P0143", 0x08, "Test", "7E8", "LEGACY_OBD")
        dtc2 = DTC("P0143", 0x08, "Test", "7E8", "LEGACY_OBD")
        assert dtc1 == dtc2
