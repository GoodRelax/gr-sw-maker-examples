"""car-diag アプリケーションエントリポイント.

DI コンテナ (手動依存注入) と PyQt6 QApplication の起動を行う。
GUI シグナルと Use Case を QThread ワーカーで接続する。

traces: M-04 (シグナル-UseCase 接続), M-03 (グラフデータ上限)
"""

from __future__ import annotations

import datetime
import logging
import sys
import time
from typing import TYPE_CHECKING, Any

from src.adapters.dtc_database import JsonDtcDatabase
from src.adapters.elm327_adapter import ELM327Adapter
from src.adapters.scan_cache_repository import JsonScanCacheRepository
from src.entities.connection_state import ConnectionState, is_valid_transition
from src.entities.ecu import DiagProtocolType, EcuInfo
from src.entities.pid import STANDARD_PIDS
from src.framework.logging_config import configure_logging
from src.framework.serial_port import PySerialPort, list_available_ports
from src.use_cases.clear_dtcs import ClearDtcsUseCase
from src.use_cases.connect_elm327 import ConnectElm327UseCase
from src.use_cases.manage_scan_cache import ManageScanCacheUseCase
from src.use_cases.monitor_dashboard import MonitorDashboardUseCase
from src.use_cases.read_dtcs import ReadDtcsUseCase
from src.use_cases.record_data import RecordDataUseCase
from src.use_cases.scan_dids import ScanDidsUseCase
from src.use_cases.scan_ecus import ScanEcusUseCase

if TYPE_CHECKING:
    from src.entities.dtc import DTC
    from src.entities.vehicle_parameter import VehicleParameter

logger = logging.getLogger(__name__)


def build_dependencies() -> dict[str, object]:
    """手動 DI コンテナ: 全依存関係を構築する.

    Returns:
        コンポーネント名をキー、インスタンスを値とする辞書.
    """
    # Framework layer
    serial_port = PySerialPort()
    cache_repository = JsonScanCacheRepository()
    dtc_database = JsonDtcDatabase()

    # Adapter layer
    elm327_adapter = ELM327Adapter(serial_port)

    # Use Case layer
    connect_use_case = ConnectElm327UseCase(serial_port, elm327_adapter)
    scan_ecus_use_case = ScanEcusUseCase(elm327_adapter)
    scan_dids_use_case = ScanDidsUseCase(elm327_adapter, cache_repository)
    read_dtcs_use_case = ReadDtcsUseCase(elm327_adapter, dtc_database)
    clear_dtcs_use_case = ClearDtcsUseCase(elm327_adapter)
    monitor_use_case = MonitorDashboardUseCase(elm327_adapter)
    record_use_case = RecordDataUseCase()
    cache_use_case = ManageScanCacheUseCase(cache_repository)

    return {
        "serial_port": serial_port,
        "cache_repository": cache_repository,
        "dtc_database": dtc_database,
        "elm327_adapter": elm327_adapter,
        "connect_use_case": connect_use_case,
        "scan_ecus_use_case": scan_ecus_use_case,
        "scan_dids_use_case": scan_dids_use_case,
        "read_dtcs_use_case": read_dtcs_use_case,
        "clear_dtcs_use_case": clear_dtcs_use_case,
        "monitor_use_case": monitor_use_case,
        "record_use_case": record_use_case,
        "cache_use_case": cache_use_case,
    }


def main() -> int:
    """アプリケーションのメインエントリポイント.

    Returns:
        終了コード.
    """
    # ログ設定初期化
    configure_logging(log_level=logging.INFO)
    logger.info("car-diag application starting")

    # DI コンテナ構築
    dependencies = build_dependencies()

    # 起動時キャッシュクリーンアップ (FR-04e)
    cache_use_case: ManageScanCacheUseCase = dependencies["cache_use_case"]  # type: ignore[assignment]
    cache_use_case.cleanup_expired_caches()

    # PyQt6 GUI 起動
    try:
        from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
        from PyQt6.QtWidgets import QApplication

        from src.framework.gui.connection_tab import ConnectionTab
        from src.framework.gui.dashboard_tab import DashboardTab
        from src.framework.gui.dtc_tab import DtcTab
        from src.framework.gui.main_window import MainWindow
        from src.framework.gui.recording_tab import RecordingTab

        app = QApplication(sys.argv)
        app.setApplicationName("car-diag")

        # メインウインドウ構築
        window = MainWindow()

        # タブ追加
        connection_tab = ConnectionTab()
        dtc_tab = DtcTab()
        dashboard_tab = DashboardTab()
        recording_tab = RecordingTab()

        window.add_tab(connection_tab, "接続")
        window.add_tab(dtc_tab, "DTC")
        window.add_tab(dashboard_tab, "ダッシュボード")
        window.add_tab(recording_tab, "記録")

        # 初期 COM ポート一覧取得
        ports = list_available_ports()
        connection_tab.set_ports(ports)

        # --- Use Case 参照の型付き取得 ---
        connect_use_case: ConnectElm327UseCase = dependencies["connect_use_case"]  # type: ignore[assignment]
        scan_ecus_use_case: ScanEcusUseCase = dependencies["scan_ecus_use_case"]  # type: ignore[assignment]
        read_dtcs_use_case: ReadDtcsUseCase = dependencies["read_dtcs_use_case"]  # type: ignore[assignment]
        clear_dtcs_use_case: ClearDtcsUseCase = dependencies["clear_dtcs_use_case"]  # type: ignore[assignment]
        monitor_use_case: MonitorDashboardUseCase = dependencies["monitor_use_case"]  # type: ignore[assignment]
        record_use_case: RecordDataUseCase = dependencies["record_use_case"]  # type: ignore[assignment]
        serial_port: PySerialPort = dependencies["serial_port"]  # type: ignore[assignment]

        # --- アプリケーション状態 ---
        detected_ecu_list: list[EcuInfo] = []
        supported_pid_list: list[str] = []
        monitoring_timer: QTimer | None = None
        polling_targets: list[Any] = []

        # ============================================================
        # ワーカースレッド基盤
        # ============================================================

        class UseCaseWorker(QObject):
            """Use Case をワーカースレッドで実行する汎用ワーカー.

            Attributes:
                finished: 実行完了シグナル (結果オブジェクト).
                error_occurred: エラー発生シグナル (エラーメッセージ).
            """

            finished = pyqtSignal(object)
            error_occurred = pyqtSignal(str)

            def __init__(
                self,
                task_callable: Any,
                task_description: str,
            ) -> None:
                """UseCaseWorker を初期化する.

                Args:
                    task_callable: 実行するタスク (引数なし callable).
                    task_description: ログ用のタスク説明.
                """
                super().__init__()
                self._task_callable = task_callable
                self._task_description = task_description

            def run(self) -> None:
                """タスクを実行する. QThread.started シグナルから呼ばれる."""
                try:
                    result = self._task_callable()
                    self.finished.emit(result)
                except Exception as exc:
                    error_message = f"{self._task_description} 失敗: {exc}"
                    logger.exception(
                        "Worker task failed",
                        extra={
                            "task_description": self._task_description,
                            "error": str(exc),
                        },
                    )
                    self.error_occurred.emit(error_message)

        # ワーカースレッド管理用リスト（GC 防止）
        active_workers: list[tuple[QThread, UseCaseWorker]] = []

        def _run_in_worker(
            task_callable: Any,
            task_description: str,
            on_finished: Any,
            on_error: Any | None = None,
        ) -> None:
            """Use Case タスクをワーカースレッドで実行する.

            Args:
                task_callable: 実行する callable (引数なし).
                task_description: ログ用のタスク説明.
                on_finished: 完了時コールバック (結果を受け取る).
                on_error: エラー時コールバック (エラーメッセージを受け取る).
            """
            thread = QThread()
            worker = UseCaseWorker(task_callable, task_description)
            worker.moveToThread(thread)

            thread.started.connect(worker.run)
            worker.finished.connect(on_finished)
            if on_error is not None:
                worker.error_occurred.connect(on_error)
            else:
                worker.error_occurred.connect(_on_default_error)

            # スレッド終了時のクリーンアップ
            def cleanup() -> None:
                thread.quit()
                thread.wait()
                pair = (thread, worker)
                if pair in active_workers:
                    active_workers.remove(pair)

            worker.finished.connect(cleanup)
            worker.error_occurred.connect(cleanup)

            active_workers.append((thread, worker))
            thread.start()

        def _on_default_error(error_message: str) -> None:
            """デフォルトのエラーハンドラ: ステータスバーにメッセージを表示する.

            Args:
                error_message: エラーメッセージ.
            """
            window.update_status_message(f"エラー: {error_message}")

        # ============================================================
        # 接続タブ: シグナル接続
        # ============================================================

        def _on_connect_requested(port_name: str) -> None:
            """接続ボタン押下時: ConnectElm327UseCase をワーカーで実行する.

            Args:
                port_name: 選択された COM ポート名.
            """
            nonlocal supported_pid_list
            window.update_status_message(f"接続中: {port_name}...")

            def task() -> list[str]:
                return connect_use_case.connect(port_name)

            def on_connect_finished(pids: object) -> None:
                nonlocal supported_pid_list
                supported_pid_list = pids if isinstance(pids, list) else []

                connection_tab.set_connected_state(True)
                dtc_tab.set_enabled(True)
                dashboard_tab.set_enabled(True)
                recording_tab.set_enabled(True)
                window.update_status_message(
                    f"接続完了: {port_name} | PID数: {len(supported_pid_list)}"
                )
                logger.info(
                    "Connection established via GUI",
                    extra={
                        "port_name": port_name,
                        "supported_pid_count": len(supported_pid_list),
                    },
                )

            def on_connect_error(error_message: str) -> None:
                connection_tab.set_connected_state(False)
                window.update_status_message(f"接続失敗: {error_message}")

            _run_in_worker(task, "ELM327 接続", on_connect_finished, on_connect_error)

        def _on_disconnect_requested() -> None:
            """切断ボタン押下時: シリアルポートを閉じて状態を遷移させる."""
            nonlocal supported_pid_list, detected_ecu_list

            # ダッシュボードモニタリング中なら停止
            _stop_monitoring_polling()

            # 記録中なら停止
            if record_use_case.is_recording:
                record_use_case.stop_recording()
                recording_tab.set_recording_state(False)

            # 切断実行
            try:
                connect_use_case.disconnect()
            except Exception as exc:
                logger.exception(
                    "Disconnect failed",
                    extra={"error": str(exc)},
                )

            # 状態リセット
            supported_pid_list = []
            detected_ecu_list = []

            connection_tab.set_connected_state(False)
            dtc_tab.set_enabled(False)
            dashboard_tab.set_enabled(False)
            dashboard_tab.set_monitoring_state(False)
            dashboard_tab.clear_graph_data()
            recording_tab.set_enabled(False)
            recording_tab.set_recording_state(False)
            window.update_status_message("切断しました")

            logger.info("Disconnected via GUI")

        def _on_scan_ecu_requested() -> None:
            """ECU スキャンボタン押下時: ScanEcusUseCase をワーカーで実行する."""
            # ダッシュボード監視中ならポーリングを一時停止する
            was_monitoring = monitor_use_case.is_monitoring
            if was_monitoring:
                _stop_monitoring_polling()
                logger.info("Dashboard polling paused for ECU scan")

            window.update_status_message("ECU スキャン中...")

            def task() -> list[EcuInfo]:
                return scan_ecus_use_case.execute()

            def on_scan_finished(ecus: object) -> None:
                nonlocal detected_ecu_list
                detected_ecu_list = ecus if isinstance(ecus, list) else []
                window.update_status_message(
                    f"ECU スキャン完了: {len(detected_ecu_list)} 個検出"
                )
                logger.info(
                    "ECU scan completed via GUI",
                    extra={"detected_ecu_count": len(detected_ecu_list)},
                )
                # スキャン前に監視中だった場合はポーリングを再開する
                if was_monitoring:
                    _start_monitoring_polling()
                    logger.info("Dashboard polling resumed after ECU scan")

            _run_in_worker(task, "ECU スキャン", on_scan_finished)

        def _on_refresh_ports_requested() -> None:
            """ポート更新ボタン押下時: COM ポート一覧を再取得する."""
            refreshed_ports = list_available_ports()
            connection_tab.set_ports(refreshed_ports)

        connection_tab.connect_requested.connect(_on_connect_requested)
        connection_tab.disconnect_requested.connect(_on_disconnect_requested)
        connection_tab.scan_ecu_requested.connect(_on_scan_ecu_requested)
        connection_tab.refresh_ports_requested.connect(_on_refresh_ports_requested)

        # ============================================================
        # DTC タブ: シグナル接続
        # ============================================================

        def _on_read_dtcs_requested() -> None:
            """DTC 読取ボタン押下時: ReadDtcsUseCase をワーカーで実行する."""
            if not detected_ecu_list:
                window.update_status_message(
                    "先に ECU スキャンを実行してください"
                )
                return

            window.update_status_message("DTC 読取中...")

            def task() -> dict[str, list[Any]]:
                return read_dtcs_use_case.execute(detected_ecu_list)

            def on_read_finished(dtc_by_ecu: object) -> None:
                if not isinstance(dtc_by_ecu, dict):
                    return

                # DTC エンティティを GUI 表示用辞書に変換
                display_data: dict[str, list[dict[str, str]]] = {}
                total_count = 0
                for ecu_id, dtc_list in dtc_by_ecu.items():
                    display_dtcs: list[dict[str, str]] = []
                    for dtc in dtc_list:
                        display_dtcs.append({
                            "dtc_code": dtc.dtc_code,
                            "description": dtc.description,
                            "status": f"0x{dtc.status_byte:02X}",
                            "protocol": dtc.protocol_type,
                        })
                        total_count += 1
                    display_data[ecu_id] = display_dtcs

                dtc_tab.display_dtcs(display_data)
                window.update_status_message(
                    f"DTC 読取完了: {total_count} 件"
                )

            _run_in_worker(task, "DTC 読取", on_read_finished)

        def _on_clear_dtcs_requested() -> None:
            """DTC 消去ボタン押下時: ClearDtcsUseCase をワーカーで実行する."""
            if not detected_ecu_list:
                window.update_status_message(
                    "先に ECU スキャンを実行してください"
                )
                return

            window.update_status_message("DTC 消去中...")

            def task() -> dict[str, bool]:
                return clear_dtcs_use_case.execute(detected_ecu_list)

            def on_clear_finished(results: object) -> None:
                if not isinstance(results, dict):
                    return

                success_count = sum(1 for v in results.values() if v)
                fail_count = len(results) - success_count

                if fail_count == 0:
                    window.update_status_message(
                        f"DTC 消去完了: {success_count} ECU 成功"
                    )
                else:
                    window.update_status_message(
                        f"DTC 消去完了: {success_count} 成功 / {fail_count} 失敗"
                    )

                # 消去後にテーブルをクリア
                dtc_tab.display_dtcs({})

            _run_in_worker(task, "DTC 消去", on_clear_finished)

        dtc_tab.read_dtcs_requested.connect(_on_read_dtcs_requested)
        dtc_tab.clear_dtcs_requested.connect(_on_clear_dtcs_requested)

        # ============================================================
        # ダッシュボードタブ: シグナル接続 + ポーリング
        # ============================================================

        def _start_monitoring_polling() -> None:
            """ダッシュボードモニタリングのポーリングを開始する."""
            nonlocal monitoring_timer, polling_targets

            monitor_use_case.start_monitoring()
            # ECU スキャン済みの場合、最初の LEGACY_OBD ECU を使用する
            # 未スキャンでも PID が検出済みならデフォルト ECU を生成する
            obd_ecu: EcuInfo | None = None
            for ecu in detected_ecu_list:
                if ecu.protocol_type == DiagProtocolType.LEGACY_OBD:
                    obd_ecu = ecu
                    break

            if obd_ecu is None and supported_pid_list:
                # ECU スキャン前でも PID が取れているならデフォルト ECU を作成
                obd_ecu = EcuInfo(
                    ecu_identifier="DEFAULT",
                    ecu_display_name="Engine (default)",
                    protocol_type=DiagProtocolType.LEGACY_OBD,
                    response_id="DEFAULT",
                )
                logger.info(
                    "Using default OBD ECU for dashboard (ECU scan not yet performed)",
                )

            polling_targets = monitor_use_case.build_polling_targets(
                supported_pids=supported_pid_list,
                did_list=[],
                legacy_obd_ecu=obd_ecu,
            )

            dashboard_tab.set_monitoring_state(True)
            dashboard_tab.clear_graph_data()

            # QTimer でポーリング間隔 500ms (FR-08a)
            monitoring_timer = QTimer()
            monitoring_timer.setInterval(500)
            monitoring_timer.timeout.connect(_poll_dashboard)
            monitoring_timer.start()

            window.update_status_message("ダッシュボードモニタリング開始")
            logger.info("Dashboard monitoring polling started")

        def _stop_monitoring_polling() -> None:
            """ダッシュボードモニタリングのポーリングを停止する."""
            nonlocal monitoring_timer

            if monitoring_timer is not None:
                monitoring_timer.stop()
                monitoring_timer = None

            monitor_use_case.stop_monitoring()
            dashboard_tab.set_monitoring_state(False)

            logger.info("Dashboard monitoring polling stopped")

        polling_in_progress = False

        def _poll_dashboard() -> None:
            """ダッシュボードを 1 巡分ポーリングし、UI を更新する.

            QTimer.timeout から呼ばれる。ワーカースレッドで実行し、
            結果を GUI スレッドで反映する。
            前回のポーリングが完了するまで次のポーリングをスキップする。
            """
            nonlocal polling_in_progress

            if not monitor_use_case.is_monitoring:
                return

            # 前回のポーリングがまだ完了していない場合はスキップ
            if polling_in_progress:
                return

            polling_in_progress = True

            def task() -> list[Any]:
                return monitor_use_case.poll_once(polling_targets)

            def on_poll_finished(parameters: object) -> None:
                nonlocal polling_in_progress
                polling_in_progress = False

                if not isinstance(parameters, list):
                    return

                # VehicleParameter を GUI 表示用辞書に変換
                # PID 定義からパラメータ名を取得し、ECU 名も解決する
                display_params: list[dict[str, str]] = []
                for param in parameters:
                    pid_hex = param.parameter_identifier.upper()
                    pid_def = STANDARD_PIDS.get(pid_hex)
                    # パラメータ名: "0C: Engine RPM (SID $01)"
                    if pid_def is not None:
                        param_label = f"{pid_hex}: {pid_def.display_name}"
                    else:
                        param_label = pid_hex

                    # ECU 名: detected_ecu_list から解決、なければ identifier
                    ecu_label = param.ecu_identifier
                    for ecu in detected_ecu_list:
                        if ecu.ecu_identifier == param.ecu_identifier:
                            ecu_label = ecu.ecu_display_name
                            break
                    if ecu_label == "DEFAULT" and detected_ecu_list:
                        ecu_label = detected_ecu_list[0].ecu_display_name

                    display_params.append({
                        "name": param_label,
                        "value": (
                            str(param.physical_value)
                            if param.physical_value is not None
                            else param.raw_hex
                        ),
                        "unit": param.unit or "",
                        "ecu": ecu_label,
                    })

                dashboard_tab.update_parameters(display_params)
                dashboard_tab.append_graph_data(display_params)

                # 記録中なら行を書き込む
                if record_use_case.is_recording:
                    timestamp_iso = datetime.datetime.now(
                        tz=datetime.timezone.utc,
                    ).isoformat()
                    record_use_case.write_row(timestamp_iso, parameters)
                    recording_tab.update_row_count(record_use_case.row_count)

            def on_poll_error(error_message: str) -> None:
                nonlocal polling_in_progress
                polling_in_progress = False

                # 通信断の可能性があるためモニタリングを停止
                _stop_monitoring_polling()
                window.update_status_message(
                    f"モニタリング中断: {error_message}"
                )

            _run_in_worker(task, "ダッシュボードポーリング", on_poll_finished, on_poll_error)

        def _on_start_monitoring_requested() -> None:
            """モニタリング開始ボタン押下時."""
            _start_monitoring_polling()

        def _on_stop_monitoring_requested() -> None:
            """モニタリング停止ボタン押下時."""
            _stop_monitoring_polling()
            window.update_status_message("ダッシュボードモニタリング停止")

        dashboard_tab.start_monitoring_requested.connect(
            _on_start_monitoring_requested,
        )
        dashboard_tab.stop_monitoring_requested.connect(
            _on_stop_monitoring_requested,
        )

        # ============================================================
        # 記録タブ: シグナル接続
        # ============================================================

        def _on_start_recording_requested(file_path: str) -> None:
            """記録開始ボタン押下時: RecordDataUseCase.start_recording を呼ぶ.

            Args:
                file_path: 記録先 TSV ファイルパス.
            """
            # パラメータ名リストを構築 (ポーリング対象から)
            parameter_names = [
                t.parameter_id for t in polling_targets
            ] if polling_targets else supported_pid_list

            try:
                record_use_case.start_recording(file_path, parameter_names)
                recording_tab.set_recording_state(True)
                window.update_status_message(f"記録開始: {file_path}")
                logger.info(
                    "Recording started via GUI",
                    extra={"file_path": file_path},
                )
            except OSError as exc:
                window.update_status_message(
                    f"記録開始失敗: {exc}"
                )
                logger.exception(
                    "Recording start failed",
                    extra={"file_path": file_path, "error": str(exc)},
                )

        def _on_stop_recording_requested() -> None:
            """記録停止ボタン押下時: RecordDataUseCase.stop_recording を呼ぶ."""
            record_use_case.stop_recording()
            recording_tab.set_recording_state(False)
            window.update_status_message(
                f"記録停止: {record_use_case.row_count} 行記録済"
            )
            logger.info(
                "Recording stopped via GUI",
                extra={"total_rows": record_use_case.row_count},
            )

        recording_tab.start_recording_requested.connect(
            _on_start_recording_requested,
        )
        recording_tab.stop_recording_requested.connect(
            _on_stop_recording_requested,
        )

        # ============================================================
        # ウインドウ表示・イベントループ
        # ============================================================

        window.show()
        logger.info("GUI displayed")

        exit_code = app.exec()

        # クリーンアップ: モニタリング停止、記録停止、切断
        _stop_monitoring_polling()
        if record_use_case.is_recording:
            record_use_case.stop_recording()
        try:
            connect_use_case.disconnect()
        except Exception:
            pass

        logger.info(
            "Application exiting",
            extra={"exit_code": exit_code},
        )
        return exit_code

    except ImportError:
        logger.error(
            "PyQt6 is not installed. GUI cannot be started. "
            "Install with: pip install PyQt6"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
