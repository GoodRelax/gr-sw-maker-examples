"""MonitorDashboardUseCase のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.entities.ecu import DiagProtocolType, EcuInfo
from src.entities.vehicle_parameter import VehicleParameter
from src.use_cases.monitor_dashboard import MonitorDashboardUseCase, PollingTarget


def _make_ecu() -> EcuInfo:
    """テスト用 Legacy OBD ECU を生成する."""
    return EcuInfo("7DF", "Engine", DiagProtocolType.LEGACY_OBD, "7E8")


class TestMonitorDashboardUseCase:
    """MonitorDashboardUseCase のテスト."""

    def test_build_polling_targets_with_pids(self) -> None:
        """サポート PID からポーリングターゲットを構築."""
        diag_protocol = MagicMock()
        use_case = MonitorDashboardUseCase(diag_protocol)
        ecu = _make_ecu()

        targets = use_case.build_polling_targets(
            supported_pids=["0C", "0D", "05"],
            did_list=[],
            legacy_obd_ecu=ecu,
        )

        assert len(targets) == 3
        assert all(t.pid_definition is not None for t in targets)

    def test_build_polling_targets_with_dids(self) -> None:
        """DID からもポーリングターゲットを構築."""
        diag_protocol = MagicMock()
        use_case = MonitorDashboardUseCase(diag_protocol)
        uds_ecu = EcuInfo("7E0", "Engine", DiagProtocolType.UDS, "7E8")

        targets = use_case.build_polling_targets(
            supported_pids=[],
            did_list=[("F400", uds_ecu)],
        )

        assert len(targets) == 1
        assert targets[0].pid_definition is None

    def test_poll_once_returns_parameters(self) -> None:
        """ポーリング 1 巡分のパラメータ取得."""
        diag_protocol = MagicMock()
        ecu = _make_ecu()
        reading = VehicleParameter(
            parameter_identifier="0C",
            raw_hex="1A F8",
            physical_value=None,
            unit=None,
            ecu_identifier="7E8",
            timestamp_epoch=1.0,
        )
        diag_protocol.read_parameter.return_value = reading

        use_case = MonitorDashboardUseCase(diag_protocol)
        use_case.start_monitoring()

        targets = use_case.build_polling_targets(
            supported_pids=["0C"],
            did_list=[],
            legacy_obd_ecu=ecu,
        )
        results = use_case.poll_once(targets)

        assert len(results) == 1
        # PID 変換が適用されて physical_value が設定される
        assert results[0].physical_value == pytest.approx(1726.0)

    def test_start_stop_monitoring(self) -> None:
        """モニタリングの開始と停止."""
        diag_protocol = MagicMock()
        use_case = MonitorDashboardUseCase(diag_protocol)

        assert not use_case.is_monitoring
        use_case.start_monitoring()
        assert use_case.is_monitoring
        use_case.stop_monitoring()
        assert not use_case.is_monitoring

    def test_poll_once_skips_none_readings(self) -> None:
        """読取失敗（None）はスキップされる."""
        diag_protocol = MagicMock()
        diag_protocol.read_parameter.return_value = None

        ecu = _make_ecu()
        use_case = MonitorDashboardUseCase(diag_protocol)
        use_case.start_monitoring()

        targets = use_case.build_polling_targets(
            supported_pids=["0C"],
            did_list=[],
            legacy_obd_ecu=ecu,
        )
        results = use_case.poll_once(targets)

        assert len(results) == 0
