"""ECU 関連エンティティ: DiagProtocolType と EcuInfo.

traces: FR-03, FR-03c, CON-06
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DiagProtocolType(StrEnum):
    """診断プロトコル種別.

    ELM327 がサポートする 3 つの診断プロトコル体系を列挙する。
    """

    LEGACY_OBD = "LEGACY_OBD"
    UDS = "UDS"
    KWP2000 = "KWP2000"


@dataclass(frozen=True)
class EcuInfo:
    """ECU 識別情報.

    ECU スキャンで検出された ECU の情報を保持する不変値オブジェクト。

    Attributes:
        ecu_identifier: ECU 識別子（CAN ID hex 文字列 or KWP アドレス hex 文字列）.
        ecu_display_name: ECU 表示名（推定名。例: "Engine", "Transmission"）.
        protocol_type: この ECU が使用する診断プロトコル種別.
        response_id: 応答 CAN ID（例: "7E8"）or KWP 応答アドレス.
    """

    ecu_identifier: str
    ecu_display_name: str
    protocol_type: DiagProtocolType
    response_id: str
