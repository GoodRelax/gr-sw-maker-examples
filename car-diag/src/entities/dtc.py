"""DTC (Diagnostic Trouble Code) エンティティ.

OBD-II 2バイト DTC および UDS 3バイト DTC のデコードを行う。

traces: FR-06, CON-08, LIM-01
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DtcCategory(StrEnum):
    """DTC カテゴリ（先頭文字）.

    OBD-II DTC コードの上位 2 ビットで決定される。
    """

    POWERTRAIN = "P"
    CHASSIS = "C"
    BODY = "B"
    NETWORK = "U"


# 上位 2 ビット → カテゴリ文字のマッピング
_CATEGORY_MAP: dict[int, DtcCategory] = {
    0b00: DtcCategory.POWERTRAIN,
    0b01: DtcCategory.CHASSIS,
    0b10: DtcCategory.BODY,
    0b11: DtcCategory.NETWORK,
}

# 上位 2 ビット目のサブ桁（0-3）
_SECOND_DIGIT_MAP: dict[int, str] = {
    0b00: "0",
    0b01: "1",
    0b10: "2",
    0b11: "3",
}


def decode_obd2_dtc(high_byte: int, low_byte: int) -> str:
    """OBD-II 2バイト DTC を人間可読コードにデコードする.

    2バイト hex（例: 0x01, 0x43）を P0143 のような文字列に変換する。

    Args:
        high_byte: DTC の上位バイト (0x00-0xFF).
        low_byte: DTC の下位バイト (0x00-0xFF).

    Returns:
        デコードされた DTC コード文字列（例: "P0143"）.

    Raises:
        ValueError: バイト値が 0x00-0xFF の範囲外の場合.
    """
    if not (0x00 <= high_byte <= 0xFF):
        msg = f"high_byte must be 0x00-0xFF, got 0x{high_byte:02X}"
        raise ValueError(msg)
    if not (0x00 <= low_byte <= 0xFF):
        msg = f"low_byte must be 0x00-0xFF, got 0x{low_byte:02X}"
        raise ValueError(msg)

    category_bits = (high_byte >> 6) & 0x03
    second_digit_bits = (high_byte >> 4) & 0x03
    third_digit = (high_byte & 0x0F)
    fourth_digit = (low_byte >> 4) & 0x0F
    fifth_digit = low_byte & 0x0F

    category = _CATEGORY_MAP[category_bits]
    second_digit = _SECOND_DIGIT_MAP[second_digit_bits]

    return f"{category.value}{second_digit}{third_digit:X}{fourth_digit:X}{fifth_digit:X}"


def decode_uds_dtc(byte1: int, byte2: int, byte3: int) -> str:
    """UDS 3バイト DTC をデコードする.

    UDS (ISO 14229) の 3バイト DTC フォーマット:
    - byte1-byte2: OBD-II 互換の 2バイト DTC コード
    - byte3: Failure Type Byte (サブ故障種別)

    Args:
        byte1: DTC 第1バイト.
        byte2: DTC 第2バイト.
        byte3: DTC 第3バイト（Failure Type）.

    Returns:
        デコードされた DTC コード文字列（例: "P0143-07"）.
        byte3 は "-XX" として付加される。

    Raises:
        ValueError: バイト値が 0x00-0xFF の範囲外の場合.
    """
    if not (0x00 <= byte3 <= 0xFF):
        msg = f"byte3 must be 0x00-0xFF, got 0x{byte3:02X}"
        raise ValueError(msg)

    base_code = decode_obd2_dtc(byte1, byte2)
    return f"{base_code}-{byte3:02X}"


@dataclass(frozen=True)
class DTC:
    """診断トラブルコード（Diagnostic Trouble Code）.

    車両 ECU が検出した故障コードとその付属情報を保持する不変値オブジェクト。

    Attributes:
        dtc_code: デコード済み DTC 文字列（例: "P0143" or "P0143-07"）.
        status_byte: DTC ステータスバイト.
        description: 英語説明文。不明な場合は "Unknown".
        ecu_identifier: 検出元 ECU の識別子.
        protocol_type: 検出に使用した診断プロトコル種別.
    """

    dtc_code: str
    status_byte: int
    description: str
    ecu_identifier: str
    protocol_type: str  # DiagProtocolType の値を文字列で保持（循環 import 回避）
