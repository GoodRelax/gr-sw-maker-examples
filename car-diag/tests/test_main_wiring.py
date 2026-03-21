"""main.py の DI コンテナ構築と build_dependencies のテスト.

GUI シグナル接続は PyQt6 が必要なため、build_dependencies の
インスタンス生成・依存関係の正しさのみをテストする。

traces: M-04
"""

from __future__ import annotations

import pytest

from src.main import build_dependencies


class TestBuildDependencies:
    """build_dependencies 関数のテスト."""

    def test_returns_all_required_keys(self) -> None:
        """全ての必須コンポーネントキーが含まれることを確認する."""
        deps = build_dependencies()

        expected_keys = {
            "serial_port",
            "cache_repository",
            "dtc_database",
            "elm327_adapter",
            "connect_use_case",
            "scan_ecus_use_case",
            "scan_dids_use_case",
            "read_dtcs_use_case",
            "clear_dtcs_use_case",
            "monitor_use_case",
            "record_use_case",
            "cache_use_case",
        }

        assert set(deps.keys()) == expected_keys

    def test_all_values_are_not_none(self) -> None:
        """全てのコンポーネントが None でないことを確認する."""
        deps = build_dependencies()

        for key, value in deps.items():
            assert value is not None, f"{key} should not be None"

    def test_connect_use_case_type(self) -> None:
        """ConnectElm327UseCase のインスタンスが正しいことを確認する."""
        from src.use_cases.connect_elm327 import ConnectElm327UseCase

        deps = build_dependencies()
        assert isinstance(deps["connect_use_case"], ConnectElm327UseCase)

    def test_scan_ecus_use_case_type(self) -> None:
        """ScanEcusUseCase のインスタンスが正しいことを確認する."""
        from src.use_cases.scan_ecus import ScanEcusUseCase

        deps = build_dependencies()
        assert isinstance(deps["scan_ecus_use_case"], ScanEcusUseCase)

    def test_read_dtcs_use_case_type(self) -> None:
        """ReadDtcsUseCase のインスタンスが正しいことを確認する."""
        from src.use_cases.read_dtcs import ReadDtcsUseCase

        deps = build_dependencies()
        assert isinstance(deps["read_dtcs_use_case"], ReadDtcsUseCase)

    def test_clear_dtcs_use_case_type(self) -> None:
        """ClearDtcsUseCase のインスタンスが正しいことを確認する."""
        from src.use_cases.clear_dtcs import ClearDtcsUseCase

        deps = build_dependencies()
        assert isinstance(deps["clear_dtcs_use_case"], ClearDtcsUseCase)

    def test_monitor_use_case_type(self) -> None:
        """MonitorDashboardUseCase のインスタンスが正しいことを確認する."""
        from src.use_cases.monitor_dashboard import MonitorDashboardUseCase

        deps = build_dependencies()
        assert isinstance(deps["monitor_use_case"], MonitorDashboardUseCase)

    def test_record_use_case_type(self) -> None:
        """RecordDataUseCase のインスタンスが正しいことを確認する."""
        from src.use_cases.record_data import RecordDataUseCase

        deps = build_dependencies()
        assert isinstance(deps["record_use_case"], RecordDataUseCase)
