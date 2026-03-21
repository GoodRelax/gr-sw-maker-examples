"""ScanDidsUseCase のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.entities.ecu import DiagProtocolType, EcuInfo
from src.use_cases.scan_dids import ScanDidsUseCase


def _make_uds_ecu(identifier: str = "7E0") -> EcuInfo:
    """テスト用 UDS ECU を生成する."""
    return EcuInfo(
        identifier, f"ECU_{identifier}",
        DiagProtocolType.UDS, identifier.replace("E0", "E8"),
    )


class TestScanDidsUseCase:
    """ScanDidsUseCase のテスト."""

    def test_preset_scan_filters_uds_ecus(self) -> None:
        """プリセットスキャンは UDS ECU のみを対象とする."""
        diag_protocol = MagicMock()
        cache_repo = MagicMock()
        cache_repo.load.return_value = None

        diag_protocol.scan_dids.return_value = ["F400", "F401"]

        uds_ecu = _make_uds_ecu()
        kwp_ecu = EcuInfo("10", "ABS", DiagProtocolType.KWP2000, "10")

        use_case = ScanDidsUseCase(diag_protocol, cache_repo)
        result = use_case.execute_preset_scan(
            ecu_list=[uds_ecu, kwp_ecu],
            cache_key="VIN123",
        )

        assert len(result) >= 1
        # KWP ECU はスキャン対象外なので scan_dids は UDS ECU 分だけ呼ばれる
        assert all(did.ecu_identifier == "7E0" for did in result)

    def test_abort_saves_progress(self) -> None:
        """中断時にキャッシュへ進捗が保存される."""
        diag_protocol = MagicMock()
        cache_repo = MagicMock()
        cache_repo.load.return_value = None

        # scan_dids 実行中に abort がリクエストされるシミュレーション
        def scan_dids_with_abort(ecu, did_range_start, did_range_end, on_progress=None):
            use_case.request_abort()
            return ["F400"]

        diag_protocol.scan_dids.side_effect = scan_dids_with_abort

        uds_ecu = _make_uds_ecu()
        use_case = ScanDidsUseCase(diag_protocol, cache_repo)
        result = use_case.execute_preset_scan(
            ecu_list=[uds_ecu],
            cache_key="VIN123",
        )

        # 進捗がキャッシュに保存された
        cache_repo.save.assert_called()

    def test_resume_from_cache(self) -> None:
        """キャッシュから前回の中断位置を復元して再開."""
        diag_protocol = MagicMock()
        cache_repo = MagicMock()

        cache_repo.load.return_value = {
            "did_scan_progress": {
                "ecu_index": 0,
                "last_scanned_did": 0x0100,
                "completed": False,
                "found_dids": [
                    {"did_id": "F400", "display_name": "DID_F400",
                     "byte_count": 4, "ecu_identifier": "7E0"},
                ],
            },
        }

        diag_protocol.scan_dids.return_value = ["F401"]

        uds_ecu = _make_uds_ecu()
        use_case = ScanDidsUseCase(diag_protocol, cache_repo)
        result = use_case.execute_full_scan(
            ecu_list=[uds_ecu],
            cache_key="VIN123",
        )

        # 前回検出分 + 今回検出分
        assert len(result) >= 2

    def test_no_uds_ecus_returns_empty(self) -> None:
        """UDS ECU がない場合は空リストを返す."""
        diag_protocol = MagicMock()
        cache_repo = MagicMock()
        cache_repo.load.return_value = None

        kwp_ecu = EcuInfo("10", "ABS", DiagProtocolType.KWP2000, "10")
        legacy_ecu = EcuInfo("7DF", "Engine", DiagProtocolType.LEGACY_OBD, "7E8")

        use_case = ScanDidsUseCase(diag_protocol, cache_repo)
        result = use_case.execute_preset_scan(
            ecu_list=[kwp_ecu, legacy_ecu],
            cache_key="VIN123",
        )

        assert result == []
        diag_protocol.scan_dids.assert_not_called()
