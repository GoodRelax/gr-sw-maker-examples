"""ClearDtcsUseCase: マルチプロトコル DTC 消去.

traces: FR-07, FR-07a-d, CON-04
"""

from __future__ import annotations

import logging

from src.entities.ecu import EcuInfo
from src.use_cases.protocols import DiagProtocol

logger = logging.getLogger(__name__)


class ClearDtcsUseCase:
    """DTC 消去ユースケース.

    対象 ECU に各プロトコルに応じた DTC 消去コマンドを送信する。

    Attributes:
        _diag_protocol: 診断プロトコル抽象インターフェース.
    """

    def __init__(self, diag_protocol: DiagProtocol) -> None:
        """ClearDtcsUseCase を初期化する.

        Args:
            diag_protocol: 診断プロトコル抽象インターフェース.
        """
        self._diag_protocol = diag_protocol

    def execute(self, ecu_list: list[EcuInfo]) -> dict[str, bool]:
        """対象 ECU の DTC を消去する.

        Args:
            ecu_list: DTC 消去対象の ECU リスト.

        Returns:
            ECU 識別子をキー、消去成否を値とする辞書.
        """
        logger.info(
            "DTC clear started",
            extra={"ecu_count": len(ecu_list)},
        )

        clear_results: dict[str, bool] = {}

        for ecu in ecu_list:
            try:
                clear_success = self._diag_protocol.clear_dtcs(ecu)
                clear_results[ecu.ecu_identifier] = clear_success

                if clear_success:
                    logger.info(
                        "DTC cleared successfully",
                        extra={
                            "ecu_identifier": ecu.ecu_identifier,
                            "ecu_display_name": ecu.ecu_display_name,
                        },
                    )
                else:
                    logger.warning(
                        "DTC clear returned negative response",
                        extra={
                            "ecu_identifier": ecu.ecu_identifier,
                            "ecu_display_name": ecu.ecu_display_name,
                        },
                    )

            except Exception:
                logger.exception(
                    "DTC clear failed for ECU",
                    extra={
                        "ecu_identifier": ecu.ecu_identifier,
                        "ecu_display_name": ecu.ecu_display_name,
                    },
                )
                clear_results[ecu.ecu_identifier] = False

        successful_count = sum(1 for v in clear_results.values() if v)
        logger.info(
            "DTC clear completed",
            extra={
                "total_ecus": len(ecu_list),
                "successful_count": successful_count,
                "failed_count": len(ecu_list) - successful_count,
            },
        )

        return clear_results
