"""MonitorDashboardUseCase: ラウンドロビンポーリングと物理値変換.

traces: FR-08, FR-08a-d, CON-02
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from src.entities.ecu import DiagProtocolType, EcuInfo
from src.entities.pid import STANDARD_PIDS, PidDefinition
from src.entities.vehicle_parameter import VehicleParameter
from src.use_cases.protocols import DiagProtocol

logger = logging.getLogger(__name__)


@dataclass
class PollingTarget:
    """ポーリング対象パラメータ.

    Attributes:
        parameter_id: PID or DID の hex 文字列.
        ecu: 対象 ECU.
        pid_definition: PID 定義（Legacy OBD の場合）。DID の場合は None.
    """

    parameter_id: str
    ecu: EcuInfo
    pid_definition: PidDefinition | None = None


class MonitorDashboardUseCase:
    """ダッシュボードモニタリングユースケース.

    PID と DID をラウンドロビンでポーリングし、物理値に変換する。

    Attributes:
        _diag_protocol: 診断プロトコル抽象インターフェース.
        _polling_active: ポーリング実行中フラグ.
    """

    def __init__(self, diag_protocol: DiagProtocol) -> None:
        """MonitorDashboardUseCase を初期化する.

        Args:
            diag_protocol: 診断プロトコル抽象インターフェース.
        """
        self._diag_protocol = diag_protocol
        self._polling_active = False
        self._last_readings: dict[str, VehicleParameter] = {}

    def build_polling_targets(
        self,
        supported_pids: list[str],
        did_list: list[tuple[str, EcuInfo]],
        legacy_obd_ecu: EcuInfo | None = None,
    ) -> list[PollingTarget]:
        """ポーリング対象のパラメータリストを構築する.

        Args:
            supported_pids: 車両が対応する PID の hex 文字列リスト.
            did_list: (DID hex, ECU) のタプルリスト.
            legacy_obd_ecu: Legacy OBD ECU（PID 読取用）.

        Returns:
            ポーリング対象のリスト.
        """
        targets: list[PollingTarget] = []

        if legacy_obd_ecu is not None:
            for pid_hex in supported_pids:
                pid_def = STANDARD_PIDS.get(pid_hex.upper())
                if pid_def is not None:
                    targets.append(PollingTarget(
                        parameter_id=pid_hex,
                        ecu=legacy_obd_ecu,
                        pid_definition=pid_def,
                    ))

        for did_hex, ecu in did_list:
            targets.append(PollingTarget(
                parameter_id=did_hex,
                ecu=ecu,
                pid_definition=None,
            ))

        logger.info(
            "Polling targets built",
            extra={"target_count": len(targets)},
        )

        return targets

    def poll_once(
        self,
        targets: list[PollingTarget],
    ) -> list[VehicleParameter]:
        """ポーリング対象を 1 巡分読み取る.

        Args:
            targets: ポーリング対象リスト.

        Returns:
            読取結果のリスト.
        """
        results: list[VehicleParameter] = []

        for target in targets:
            if not self._polling_active:
                break

            reading = self._diag_protocol.read_parameter(
                ecu=target.ecu,
                parameter_id=target.parameter_id,
            )

            if reading is None:
                # 読取失敗時は前回値を使用して表示を安定させる
                last = self._last_readings.get(target.parameter_id)
                if last is not None:
                    results.append(last)
                continue

            # PID の場合は物理値変換（FR-08b）
            if (
                target.pid_definition is not None
                and reading.raw_hex
            ):
                try:
                    raw_bytes = [
                        int(byte_str, 16)
                        for byte_str in reading.raw_hex.split()
                    ]
                    physical = target.pid_definition.convert_raw_bytes(
                        raw_bytes,
                    )
                    reading = VehicleParameter(
                        parameter_identifier=reading.parameter_identifier,
                        raw_hex=reading.raw_hex,
                        physical_value=physical,
                        unit=target.pid_definition.unit,
                        ecu_identifier=reading.ecu_identifier,
                        timestamp_epoch=reading.timestamp_epoch,
                    )
                except (ValueError, IndexError):
                    logger.warning(
                        "PID conversion failed",
                        extra={
                            "pid_id": target.parameter_id,
                            "raw_hex": reading.raw_hex,
                        },
                    )

            self._last_readings[target.parameter_id] = reading
            results.append(reading)

        return results

    def start_monitoring(self) -> None:
        """モニタリングを開始する."""
        self._polling_active = True
        logger.info("Dashboard monitoring started")

    def stop_monitoring(self) -> None:
        """モニタリングを停止する."""
        self._polling_active = False
        logger.info("Dashboard monitoring stopped")

    @property
    def is_monitoring(self) -> bool:
        """モニタリング中かを返す."""
        return self._polling_active
