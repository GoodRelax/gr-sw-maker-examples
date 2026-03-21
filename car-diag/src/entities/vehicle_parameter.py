"""VehicleParameter: パラメータ読取結果の値オブジェクト.

traces: FR-08b
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleParameter:
    """車両パラメータの読取結果.

    PID または DID から読み取ったパラメータ値を保持する不変値オブジェクト。

    Attributes:
        parameter_identifier: パラメータ識別子（PID hex or DID hex）.
        raw_hex: 生データの hex 文字列（例: "1A 3F"）.
        physical_value: 変換後の物理値。変換不可の場合は None.
        unit: 物理値の単位。変換不可の場合は None.
        ecu_identifier: 読取元 ECU の識別子.
        timestamp_epoch: 読取時刻（Unix epoch 秒、float）.
    """

    parameter_identifier: str
    raw_hex: str
    physical_value: float | None
    unit: str | None
    ecu_identifier: str
    timestamp_epoch: float
