"""PidDefinition: OBD-II 標準 PID の定義と物理値変換.

traces: FR-01c, FR-08b, NFR-05b
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PidDefinition:
    """Legacy OBD-II PID の定義.

    Attributes:
        pid_id: PID 番号の hex 文字列（例: "0C"）.
        display_name: パラメータの表示名（例: "Engine RPM"）.
        unit: 物理値の単位（例: "rpm", "km/h"）.
        byte_count: 応答データのバイト数.
        convert: 生データバイト列から物理値への変換関数.
            引数はバイト値のリスト [A, B, ...]。
    """

    pid_id: str
    display_name: str
    unit: str
    byte_count: int
    convert: Callable[[list[int]], float]

    def convert_raw_bytes(self, raw_bytes: list[int]) -> float:
        """生データバイト列を物理値に変換する.

        Args:
            raw_bytes: ECU からの応答データバイト列.

        Returns:
            変換後の物理値.

        Raises:
            ValueError: raw_bytes の長さが byte_count と一致しない場合.
        """
        if len(raw_bytes) != self.byte_count:
            msg = (
                f"PID {self.pid_id} expects {self.byte_count} bytes, "
                f"got {len(raw_bytes)}"
            )
            raise ValueError(msg)
        return self.convert(raw_bytes)


# OBD-II 標準 PID 定義
# 変換式は SAE J1979 に基づく
STANDARD_PIDS: dict[str, PidDefinition] = {
    "04": PidDefinition(
        pid_id="04",
        display_name="Calculated Engine Load",
        unit="%",
        byte_count=1,
        convert=lambda ab: ab[0] * 100 / 255,
    ),
    "05": PidDefinition(
        pid_id="05",
        display_name="Engine Coolant Temperature",
        unit="degC",
        byte_count=1,
        convert=lambda ab: ab[0] - 40,
    ),
    "0C": PidDefinition(
        pid_id="0C",
        display_name="Engine RPM",
        unit="rpm",
        byte_count=2,
        convert=lambda ab: (ab[0] * 256 + ab[1]) / 4,
    ),
    "0D": PidDefinition(
        pid_id="0D",
        display_name="Vehicle Speed",
        unit="km/h",
        byte_count=1,
        convert=lambda ab: float(ab[0]),
    ),
    "0E": PidDefinition(
        pid_id="0E",
        display_name="Timing Advance",
        unit="deg",
        byte_count=1,
        convert=lambda ab: ab[0] / 2 - 64,
    ),
    "0F": PidDefinition(
        pid_id="0F",
        display_name="Intake Air Temperature",
        unit="degC",
        byte_count=1,
        convert=lambda ab: ab[0] - 40,
    ),
    "10": PidDefinition(
        pid_id="10",
        display_name="MAF Air Flow Rate",
        unit="g/s",
        byte_count=2,
        convert=lambda ab: (ab[0] * 256 + ab[1]) / 100,
    ),
    "11": PidDefinition(
        pid_id="11",
        display_name="Throttle Position",
        unit="%",
        byte_count=1,
        convert=lambda ab: ab[0] * 100 / 255,
    ),
    "1F": PidDefinition(
        pid_id="1F",
        display_name="Run Time Since Engine Start",
        unit="s",
        byte_count=2,
        convert=lambda ab: float(ab[0] * 256 + ab[1]),
    ),
    "2F": PidDefinition(
        pid_id="2F",
        display_name="Fuel Tank Level Input",
        unit="%",
        byte_count=1,
        convert=lambda ab: ab[0] * 100 / 255,
    ),
    "42": PidDefinition(
        pid_id="42",
        display_name="Control Module Voltage",
        unit="V",
        byte_count=2,
        convert=lambda ab: (ab[0] * 256 + ab[1]) / 1000,
    ),
    "46": PidDefinition(
        pid_id="46",
        display_name="Ambient Air Temperature",
        unit="degC",
        byte_count=1,
        convert=lambda ab: ab[0] - 40,
    ),
}
