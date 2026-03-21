"""ScanEcusUseCase: CAN + KWP ECU 自動スキャン.

traces: FR-03, FR-03a, FR-03b, FR-03c, FR-03d, FR-03e, FR-03f
"""

from __future__ import annotations

import logging

from src.entities.ecu import EcuInfo
from src.use_cases.protocols import DiagProtocol, ProgressCallback

logger = logging.getLogger(__name__)


class ScanEcusUseCase:
    """ECU 自動スキャンユースケース.

    CAN バス上の ECU スキャン（UDS TesterPresent）と
    KWP2000 プロトコルの ECU スキャン（StartCommunication）を実行する。

    Attributes:
        _diag_protocol: 診断プロトコル抽象インターフェース.
    """

    def __init__(self, diag_protocol: DiagProtocol) -> None:
        """ScanEcusUseCase を初期化する.

        Args:
            diag_protocol: 診断プロトコル抽象インターフェース.
        """
        self._diag_protocol = diag_protocol

    def execute(
        self,
        on_progress: ProgressCallback | None = None,
    ) -> list[EcuInfo]:
        """ECU スキャンを実行する.

        CAN ECU スキャン（Phase 1）と KWP ECU スキャン（Phase 2）を順次実行する。

        Args:
            on_progress: 進捗コールバック (current, total, message).

        Returns:
            検出された ECU 情報のリスト.

        Raises:
            ConnectionError: 通信断が発生した場合.
            RuntimeError: スキャンで ECU が 1 つも検出されなかった場合 (FR-03f).
        """
        logger.info("ECU scan started")

        detected_ecus = self._diag_protocol.scan_ecus(
            on_progress=on_progress,
        )

        if not detected_ecus:
            logger.warning("No ECUs detected during scan")
            msg = (
                "ECU が検出されませんでした。"
                "OBD-II ポートへの接続を確認してください。"
            )
            raise RuntimeError(msg)

        logger.info(
            "ECU scan completed",
            extra={
                "detected_ecu_count": len(detected_ecus),
                "ecus": [
                    {
                        "ecu_identifier": ecu.ecu_identifier,
                        "ecu_display_name": ecu.ecu_display_name,
                        "protocol_type": ecu.protocol_type,
                    }
                    for ecu in detected_ecus
                ],
            },
        )

        return detected_ecus
