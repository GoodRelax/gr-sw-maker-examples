"""DidDefinition: UDS DID (Data Identifier) の定義.

traces: FR-05, FR-05g
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DidDefinition:
    """UDS DID の定義.

    DID スキャンで検出された Data Identifier の情報を保持する不変値オブジェクト。

    Attributes:
        did_id: DID 番号の hex 文字列（例: "F400"）.
        display_name: パラメータの表示名（スキャンで発見された場合の推定名）.
        byte_count: 応答データのバイト数.
        ecu_identifier: この DID を保持する ECU の識別子.
    """

    did_id: str
    display_name: str
    byte_count: int
    ecu_identifier: str
