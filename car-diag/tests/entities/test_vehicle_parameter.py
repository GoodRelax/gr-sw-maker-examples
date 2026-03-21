"""VehicleParameter のテスト."""

from __future__ import annotations

import pytest

from src.entities.vehicle_parameter import VehicleParameter


class TestVehicleParameter:
    """VehicleParameter データクラスのテスト."""

    def test_parameter_with_physical_value(self) -> None:
        """物理値ありのパラメータ."""
        param = VehicleParameter(
            parameter_identifier="0C",
            raw_hex="1A F8",
            physical_value=1726.0,
            unit="rpm",
            ecu_identifier="7E8",
            timestamp_epoch=1711000000.0,
        )
        assert param.physical_value == 1726.0
        assert param.unit == "rpm"

    def test_parameter_without_physical_value(self) -> None:
        """物理値なし（DID 生データ）のパラメータ."""
        param = VehicleParameter(
            parameter_identifier="F400",
            raw_hex="48 65 6C 6C 6F",
            physical_value=None,
            unit=None,
            ecu_identifier="7E0",
            timestamp_epoch=1711000000.0,
        )
        assert param.physical_value is None
        assert param.unit is None
        assert param.raw_hex == "48 65 6C 6C 6F"

    def test_parameter_is_frozen(self) -> None:
        """VehicleParameter は不変."""
        param = VehicleParameter("0C", "00 00", 0.0, "rpm", "7E8", 0.0)
        with pytest.raises(AttributeError):
            param.physical_value = 100.0  # type: ignore[misc]

    def test_parameter_equality(self) -> None:
        """同一属性のパラメータは等価."""
        p1 = VehicleParameter("0D", "78", 120.0, "km/h", "7E8", 1.0)
        p2 = VehicleParameter("0D", "78", 120.0, "km/h", "7E8", 1.0)
        assert p1 == p2
