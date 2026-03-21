"""PidDefinition エンティティのテスト.

PID 定義と物理値変換の正確性を検証する。
"""

from __future__ import annotations

import pytest

from src.entities.pid import STANDARD_PIDS, PidDefinition


class TestPidConversion:
    """PID 物理値変換のテスト."""

    def test_engine_rpm_conversion(self) -> None:
        """PID 0C (Engine RPM): (A*256+B)/4.

        例: A=0x1A, B=0xF8 -> (26*256+248)/4 = 6904/4 = 1726.0 rpm
        """
        pid = STANDARD_PIDS["0C"]
        result = pid.convert_raw_bytes([0x1A, 0xF8])
        assert result == pytest.approx(1726.0)

    def test_engine_rpm_zero(self) -> None:
        """PID 0C (Engine RPM): zero rpm."""
        pid = STANDARD_PIDS["0C"]
        result = pid.convert_raw_bytes([0x00, 0x00])
        assert result == pytest.approx(0.0)

    def test_vehicle_speed_conversion(self) -> None:
        """PID 0D (Vehicle Speed): A km/h."""
        pid = STANDARD_PIDS["0D"]
        result = pid.convert_raw_bytes([120])
        assert result == pytest.approx(120.0)

    def test_coolant_temperature_conversion(self) -> None:
        """PID 05 (Coolant Temp): A-40 degC.

        例: A=0x6E (110) -> 110-40 = 70 degC
        """
        pid = STANDARD_PIDS["05"]
        result = pid.convert_raw_bytes([0x6E])
        assert result == pytest.approx(70.0)

    def test_coolant_temperature_below_zero(self) -> None:
        """PID 05: 氷点下の場合 (A=20 -> 20-40 = -20 degC)."""
        pid = STANDARD_PIDS["05"]
        result = pid.convert_raw_bytes([20])
        assert result == pytest.approx(-20.0)

    def test_calculated_engine_load(self) -> None:
        """PID 04 (Calculated Engine Load): A*100/255 %."""
        pid = STANDARD_PIDS["04"]
        result = pid.convert_raw_bytes([0xFF])
        assert result == pytest.approx(100.0)

    def test_throttle_position(self) -> None:
        """PID 11 (Throttle Position): A*100/255 %."""
        pid = STANDARD_PIDS["11"]
        result = pid.convert_raw_bytes([0x80])  # 128
        assert result == pytest.approx(128 * 100 / 255)

    def test_maf_air_flow_rate(self) -> None:
        """PID 10 (MAF): (A*256+B)/100 g/s."""
        pid = STANDARD_PIDS["10"]
        result = pid.convert_raw_bytes([0x01, 0x00])  # 256/100 = 2.56
        assert result == pytest.approx(2.56)

    def test_control_module_voltage(self) -> None:
        """PID 42 (Control Module Voltage): (A*256+B)/1000 V."""
        pid = STANDARD_PIDS["42"]
        result = pid.convert_raw_bytes([0x37, 0x58])  # 14168/1000 = 14.168 V
        assert result == pytest.approx(14.168)

    def test_wrong_byte_count_raises_value_error(self) -> None:
        """バイト数不一致で ValueError."""
        pid = STANDARD_PIDS["0C"]  # expects 2 bytes
        with pytest.raises(ValueError, match="expects 2 bytes"):
            pid.convert_raw_bytes([0x1A])  # only 1 byte


class TestPidDefinition:
    """PidDefinition データクラスのテスト."""

    def test_standard_pids_count(self) -> None:
        """標準 PID 定義が 12 個以上ある."""
        assert len(STANDARD_PIDS) >= 12

    def test_pid_attributes(self) -> None:
        """PID 属性の確認."""
        pid = STANDARD_PIDS["0C"]
        assert pid.pid_id == "0C"
        assert pid.display_name == "Engine RPM"
        assert pid.unit == "rpm"
        assert pid.byte_count == 2

    def test_pid_is_frozen(self) -> None:
        """PidDefinition は不変."""
        pid = STANDARD_PIDS["0C"]
        with pytest.raises(AttributeError):
            pid.pid_id = "FF"  # type: ignore[misc]
