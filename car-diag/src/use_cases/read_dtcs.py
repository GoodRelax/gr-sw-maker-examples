"""ReadDtcsUseCase: マルチプロトコル DTC 読取.

traces: FR-06, FR-06a-f, CON-08
"""

from __future__ import annotations

import logging

from src.entities.dtc import DTC
from src.entities.ecu import EcuInfo
from src.use_cases.protocols import DiagProtocol, DtcDescriptionProvider

logger = logging.getLogger(__name__)


class ReadDtcsUseCase:
    """DTC 読取ユースケース.

    スキャン済みの全 ECU に対して、各プロトコルに応じた DTC 読取を実行する。
    DTC 説明文を付与し、ECU ごとにグループ化して返す。

    Attributes:
        _diag_protocol: 診断プロトコル抽象インターフェース.
        _dtc_description: DTC 説明文検索インターフェース.
    """

    def __init__(
        self,
        diag_protocol: DiagProtocol,
        dtc_description: DtcDescriptionProvider,
    ) -> None:
        """ReadDtcsUseCase を初期化する.

        Args:
            diag_protocol: 診断プロトコル抽象インターフェース.
            dtc_description: DTC 説明文検索インターフェース.
        """
        self._diag_protocol = diag_protocol
        self._dtc_description = dtc_description

    def execute(
        self,
        ecu_list: list[EcuInfo],
    ) -> dict[str, list[DTC]]:
        """全 ECU から DTC を読み取り、ECU ごとにグループ化して返す.

        Args:
            ecu_list: スキャン済みの ECU リスト.

        Returns:
            ECU 識別子をキー、DTC リストを値とする辞書。
            DTC が 0 件の ECU も空リストとして含む。
        """
        logger.info(
            "DTC read started",
            extra={"ecu_count": len(ecu_list)},
        )

        dtc_by_ecu: dict[str, list[DTC]] = {}

        for ecu in ecu_list:
            try:
                raw_dtcs = self._diag_protocol.read_dtcs(ecu)

                # DTC 説明文を付与（FR-06b）
                enriched_dtcs: list[DTC] = []
                for raw_dtc in raw_dtcs:
                    description = self._dtc_description.lookup(raw_dtc.dtc_code)
                    enriched_dtc = DTC(
                        dtc_code=raw_dtc.dtc_code,
                        status_byte=raw_dtc.status_byte,
                        description=description,
                        ecu_identifier=ecu.ecu_identifier,
                        protocol_type=ecu.protocol_type.value,
                    )
                    enriched_dtcs.append(enriched_dtc)

                dtc_by_ecu[ecu.ecu_identifier] = enriched_dtcs

                logger.info(
                    "DTCs read from ECU",
                    extra={
                        "ecu_identifier": ecu.ecu_identifier,
                        "ecu_display_name": ecu.ecu_display_name,
                        "protocol_type": ecu.protocol_type,
                        "dtc_count": len(enriched_dtcs),
                    },
                )

            except Exception:
                logger.exception(
                    "DTC read failed for ECU",
                    extra={
                        "ecu_identifier": ecu.ecu_identifier,
                        "ecu_display_name": ecu.ecu_display_name,
                    },
                )
                dtc_by_ecu[ecu.ecu_identifier] = []

        total_dtcs = sum(len(dtcs) for dtcs in dtc_by_ecu.values())
        logger.info(
            "DTC read completed",
            extra={
                "total_dtc_count": total_dtcs,
                "ecu_count": len(ecu_list),
            },
        )

        return dtc_by_ecu
