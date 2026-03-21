"""ScanDidsUseCase: UDS DID スキャン（プリセット / 全範囲）.

中断・再開に対応する。

traces: FR-05, FR-05a-g, ADR-003
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.entities.did import DidDefinition
from src.entities.ecu import DiagProtocolType, EcuInfo
from src.use_cases.protocols import (
    DiagProtocol,
    ProgressCallback,
    ScanCacheRepository,
)

logger = logging.getLogger(__name__)

# FR-05b: UDS 標準の主要 DID 範囲
PRESET_DID_RANGES: list[tuple[int, int]] = [
    (0xF400, 0xF4FF),
    (0xF600, 0xF6FF),
]

# FR-05c: 全 DID 範囲
FULL_DID_RANGE: tuple[int, int] = (0x0000, 0xFFFF)


@dataclass
class DidScanProgress:
    """DID スキャン中断位置を表すデータ.

    Attributes:
        ecu_index: 現在スキャン中の ECU インデックス.
        last_scanned_did: 最後にスキャンした DID 番号.
        completed: スキャン完了フラグ.
    """

    ecu_index: int
    last_scanned_did: int
    completed: bool


class ScanDidsUseCase:
    """DID スキャンユースケース.

    UDS 対応 ECU に対して DID をスキャンし、応答のあった DID を記録する。
    中断位置をキャッシュに保存し、再開時にはそこから続行する。

    Attributes:
        _diag_protocol: 診断プロトコル抽象インターフェース.
        _cache_repository: スキャンキャッシュリポジトリ.
        _abort_requested: 中断リクエストフラグ.
    """

    def __init__(
        self,
        diag_protocol: DiagProtocol,
        cache_repository: ScanCacheRepository,
    ) -> None:
        """ScanDidsUseCase を初期化する.

        Args:
            diag_protocol: 診断プロトコル抽象インターフェース.
            cache_repository: スキャンキャッシュリポジトリ.
        """
        self._diag_protocol = diag_protocol
        self._cache_repository = cache_repository
        self._abort_requested = False

    def request_abort(self) -> None:
        """スキャン中断をリクエストする.

        FR-05e: ユーザーが DID スキャンを中断した際に呼び出される。
        """
        self._abort_requested = True
        logger.info("DID scan abort requested")

    def execute_preset_scan(
        self,
        ecu_list: list[EcuInfo],
        cache_key: str,
        on_progress: ProgressCallback | None = None,
    ) -> list[DidDefinition]:
        """プリセット DID スキャンを実行する.

        FR-05b: UDS 標準の主要 DID 範囲をスキャンする。

        Args:
            ecu_list: スキャン対象の ECU リスト.
            cache_key: VIN またはユーザー識別名.
            on_progress: 進捗コールバック.

        Returns:
            検出された DID 定義のリスト.
        """
        return self._scan_dids(
            ecu_list=ecu_list,
            did_ranges=PRESET_DID_RANGES,
            cache_key=cache_key,
            on_progress=on_progress,
        )

    def execute_full_scan(
        self,
        ecu_list: list[EcuInfo],
        cache_key: str,
        on_progress: ProgressCallback | None = None,
    ) -> list[DidDefinition]:
        """全 DID スキャンを実行する.

        FR-05c: 全 UDS 対応 ECU に対して DID 0x0000-0xFFFF をスキャンする。

        Args:
            ecu_list: スキャン対象の ECU リスト.
            cache_key: VIN またはユーザー識別名.
            on_progress: 進捗コールバック.

        Returns:
            検出された DID 定義のリスト.
        """
        return self._scan_dids(
            ecu_list=ecu_list,
            did_ranges=[FULL_DID_RANGE],
            cache_key=cache_key,
            on_progress=on_progress,
        )

    def _scan_dids(
        self,
        ecu_list: list[EcuInfo],
        did_ranges: list[tuple[int, int]],
        cache_key: str,
        on_progress: ProgressCallback | None = None,
    ) -> list[DidDefinition]:
        """DID スキャンの内部実装.

        中断・再開対応付き。

        Args:
            ecu_list: スキャン対象の ECU リスト.
            did_ranges: スキャンする DID 範囲のリスト.
            cache_key: VIN またはユーザー識別名.
            on_progress: 進捗コールバック.

        Returns:
            検出された DID 定義のリスト.
        """
        self._abort_requested = False
        uds_ecus = [
            ecu for ecu in ecu_list
            if ecu.protocol_type == DiagProtocolType.UDS
        ]

        if not uds_ecus:
            logger.info("No UDS ECUs found, skipping DID scan")
            return []

        # FR-05f: キャッシュから中断位置を読み込む
        start_ecu_index = 0
        start_did = 0
        found_dids: list[DidDefinition] = []
        cached = self._cache_repository.load(cache_key)
        if cached and "did_scan_progress" in cached:
            progress_data = cached["did_scan_progress"]
            start_ecu_index = progress_data.get("ecu_index", 0)
            start_did = progress_data.get("last_scanned_did", 0)
            # 前回検出済みの DID を復元
            for did_entry in progress_data.get("found_dids", []):
                found_dids.append(DidDefinition(
                    did_id=did_entry["did_id"],
                    display_name=did_entry.get("display_name", ""),
                    byte_count=did_entry.get("byte_count", 0),
                    ecu_identifier=did_entry.get("ecu_identifier", ""),
                ))
            logger.info(
                "Resuming DID scan from cache",
                extra={
                    "start_ecu_index": start_ecu_index,
                    "start_did": start_did,
                    "previously_found": len(found_dids),
                },
            )

        total_ecus = len(uds_ecus)

        for ecu_idx in range(start_ecu_index, total_ecus):
            ecu = uds_ecus[ecu_idx]

            for did_start, did_end in did_ranges:
                actual_start = max(did_start, start_did) if ecu_idx == start_ecu_index else did_start
                total_dids_in_range = did_end - actual_start + 1

                scanned_dids = self._diag_protocol.scan_dids(
                    ecu=ecu,
                    did_range_start=actual_start,
                    did_range_end=did_end,
                    on_progress=on_progress,
                )

                for did_hex in scanned_dids:
                    found_dids.append(DidDefinition(
                        did_id=did_hex,
                        display_name=f"DID_{did_hex}",
                        byte_count=0,  # Adapter 層でバイト数を取得
                        ecu_identifier=ecu.ecu_identifier,
                    ))

                if self._abort_requested:
                    # FR-05e: 中断位置をキャッシュに保存
                    self._save_progress(
                        cache_key=cache_key,
                        ecu_index=ecu_idx,
                        last_scanned_did=did_end,
                        found_dids=found_dids,
                        completed=False,
                    )
                    logger.info(
                        "DID scan aborted by user",
                        extra={
                            "ecu_index": ecu_idx,
                            "found_count": len(found_dids),
                        },
                    )
                    return found_dids

            # この ECU の中断位置をリセット
            start_did = 0

            if on_progress is not None:
                remaining_ecus = total_ecus - ecu_idx - 1
                on_progress(
                    ecu_idx + 1,
                    total_ecus,
                    f"ECU {ecu.ecu_display_name} completed. "
                    f"Remaining: {remaining_ecus} ECUs",
                )

        # 完了: キャッシュに保存
        self._save_progress(
            cache_key=cache_key,
            ecu_index=total_ecus - 1,
            last_scanned_did=0xFFFF,
            found_dids=found_dids,
            completed=True,
        )

        logger.info(
            "DID scan completed",
            extra={
                "total_found": len(found_dids),
                "ecu_count": total_ecus,
            },
        )

        return found_dids

    def save_interrupted_progress(
        self,
        cache_key: str,
        ecu_index: int,
        last_scanned_did: int,
        found_dids: list[DidDefinition],
    ) -> None:
        """通信断時に中断位置を保存する.

        FR-02a: 通信断時の DID スキャン進捗保存用。
        Use Case の外部から呼び出される。

        Args:
            cache_key: VIN またはユーザー識別名.
            ecu_index: 中断時の ECU インデックス.
            last_scanned_did: 最後にスキャンした DID.
            found_dids: これまでに検出された DID リスト.
        """
        self._save_progress(
            cache_key=cache_key,
            ecu_index=ecu_index,
            last_scanned_did=last_scanned_did,
            found_dids=found_dids,
            completed=False,
        )

    def _save_progress(
        self,
        cache_key: str,
        ecu_index: int,
        last_scanned_did: int,
        found_dids: list[DidDefinition],
        completed: bool,
    ) -> None:
        """スキャン進捗をキャッシュに保存する.

        Args:
            cache_key: キャッシュキー.
            ecu_index: ECU インデックス.
            last_scanned_did: 最後にスキャンした DID.
            found_dids: 検出済み DID リスト.
            completed: 完了フラグ.
        """
        progress_payload: dict[str, Any] = {
            "did_scan_progress": {
                "ecu_index": ecu_index,
                "last_scanned_did": last_scanned_did,
                "completed": completed,
                "found_dids": [
                    {
                        "did_id": did_def.did_id,
                        "display_name": did_def.display_name,
                        "byte_count": did_def.byte_count,
                        "ecu_identifier": did_def.ecu_identifier,
                    }
                    for did_def in found_dids
                ],
            },
        }

        # 既存キャッシュとマージ
        existing = self._cache_repository.load(cache_key) or {}
        existing.update(progress_payload)
        self._cache_repository.save(cache_key, existing)

        logger.info(
            "DID scan progress saved",
            extra={
                "cache_key": cache_key,
                "ecu_index": ecu_index,
                "last_scanned_did": f"0x{last_scanned_did:04X}",
                "found_count": len(found_dids),
                "completed": completed,
            },
        )
