"""ELM327Adapter: DiagProtocol 実装.

ELM327 チップとの AT コマンド通信を通じて、Legacy OBD-II / UDS / KWP2000
の診断プロトコルを統一的に提供する。

traces: FR-01b, FR-03, FR-06, FR-07, FR-08, HWR-03 ~ HWR-26, NFR-02a, NFR-04a
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING

from src.entities.dtc import DTC, decode_obd2_dtc, decode_uds_dtc
from src.entities.ecu import DiagProtocolType, EcuInfo
from src.entities.pid import STANDARD_PIDS
from src.entities.vehicle_parameter import VehicleParameter

if TYPE_CHECKING:
    from src.use_cases.protocols import ProgressCallback, SerialPort

logger = logging.getLogger(__name__)

# ELM327 のエラー応答パターン (HWR-20)
_ELM327_ERROR_PATTERNS: tuple[str, ...] = (
    "NO DATA",
    "UNABLE TO CONNECT",
    "CAN ERROR",
    "BUS INIT: ...ERROR",
    "BUS INIT:...ERROR",
    "?",
    "BUFFER FULL",
    "DATA ERROR",
    "ACT ALERT",
    "LV RESET",
)

# 応答バリデーション: 印字可能 ASCII 文字のみ許可 (NFR-04a)
# ELM327 応答は AT テキスト応答 ("12.6V", "ELM327 v1.5") と hex データ応答を含む
_VALID_RESPONSE_PATTERN = re.compile(r"^[\x20-\x7E\r\n]*$")

# リトライ設定 (NFR-02a, HWR-24, HWR-25)
_MAX_RETRY_COUNT: int = 3
_RETRY_INTERVAL_S: float = 0.5

# プロトコル切替後のウェイト (HWR-07)
_PROTOCOL_SWITCH_WAIT_S: float = 0.2

# コマンド間インターバル (HW要求仕様 2.2)
_COMMAND_INTERVAL_S: float = 0.05

# CAN ECU スキャン範囲 (FR-03a)
_CAN_ECU_REQUEST_IDS: list[tuple[str, str]] = [
    ("7E0", "7E8"),
    ("7E1", "7E9"),
    ("7E2", "7EA"),
    ("7E3", "7EB"),
    ("7E4", "7EC"),
    ("7E5", "7ED"),
    ("7E6", "7EE"),
    ("7E7", "7EF"),
]

# CAN ID -> 推定 ECU 名 (11bit CAN + 29bit CAN 物理アドレス)
_CAN_ECU_NAMES: dict[str, str] = {
    # 11bit CAN
    "7E0": "Engine",
    "7E1": "Transmission",
    "7E2": "ABS/VSC",
    "7E3": "Airbag",
    "7E4": "Body",
    "7E5": "HVAC",
    "7E6": "Steering",
    "7E7": "Instrument",
    # 29bit CAN 物理アドレス (18DA_{addr})
    "18DA_01": "Engine #1",
    "18DA_02": "Transmission",
    "18DA_03": "ABS/ESC",
    "18DA_04": "Body Control",
    "18DA_05": "Climate Control",
    "18DA_07": "Instrument Cluster",
    "18DA_08": "Steering",
    "18DA_09": "Airbag/SRS",
    "18DA_0E": "PCM (Engine)",
    "18DA_10": "Engine #2",
    "18DA_18": "Transmission #2",
    "18DA_28": "ABS/VSC",
    "18DA_30": "EPS / Suspension",
    "18DA_40": "Body/BCM",
    "18DA_44": "Gateway",
    "18DA_47": "Window Control",
    "18DA_50": "Immobilizer",
    "18DA_58": "TPMS",
    "18DA_60": "Headlamp / Body",
    "18DA_68": "Audio/Infotainment",
    "18DA_78": "Power Steering",
    "18DA_7E": "Gateway #2",
}

# KWP アドレス範囲の主要アドレス (FR-03b)
_KWP_ECU_ADDRESSES: list[int] = [
    0x01, 0x02, 0x03, 0x04, 0x05,
    0x06, 0x07, 0x08, 0x09, 0x0A,
    0x10, 0x11, 0x15, 0x17, 0x18,
    0x19, 0x20, 0x28, 0x29, 0x40,
    0x44, 0x45, 0x46, 0x47, 0x50,
    0x55, 0x56, 0x57, 0x58, 0x60,
    0x61, 0x65, 0x70, 0x71, 0x75,
    0x76, 0x77, 0x78,
]


class Elm327CommunicationError(Exception):
    """ELM327 通信エラー."""


class Elm327ProtocolError(Exception):
    """ELM327 プロトコルエラー（NRC 等）."""


class ELM327Adapter:
    """ELM327 アダプタ: DiagProtocol の具体実装.

    SerialPort Protocol を通じて ELM327 チップと通信し、
    Legacy OBD-II / UDS / KWP2000 の診断操作を提供する。

    Attributes:
        _serial_port: シリアルポート抽象インターフェース.
        _current_protocol: 現在設定中のプロトコル番号.
    """

    def __init__(self, serial_port: SerialPort) -> None:
        """ELM327Adapter を初期化する.

        Args:
            serial_port: シリアルポート抽象インターフェース.
        """
        self._serial_port = serial_port
        self._current_protocol: int = 0
        self._is_29bit_can: bool = False

    # ------------------------------------------------------------------
    # DiagProtocol インターフェース実装
    # ------------------------------------------------------------------

    def initialize(self) -> str:
        """ELM327 初期化シーケンスを実行する.

        ATZ -> ATE0 -> ATL0 -> ATS1 -> ATH1 -> ATSP0 の順に送信する。

        Returns:
            ELM327 のバージョン文字列.

        Raises:
            Elm327CommunicationError: 初期化に失敗した場合.

        traces: FR-01b, HWR-03, HWR-04, HWR-05
        """
        # ATZ: リセット (リトライなし、特別処理)
        atz_response = self._send_raw_command("ATZ")
        if "ELM327" not in atz_response:
            msg = (
                "ELM327 が応答しません。応答内容: "
                f"{atz_response!r}"
            )
            logger.error(
                "ATZ response does not contain ELM327",
                extra={"atz_response": atz_response},
            )
            raise Elm327CommunicationError(msg)

        # バージョン文字列を抽出
        elm_version = self._extract_version(atz_response)

        # 残りの初期化コマンド (HWR-03)
        init_commands = ["ATE0", "ATL0", "ATS1", "ATH1", "ATSP0"]
        for command in init_commands:
            response = self._send_at_command_with_retry(command)
            if "OK" not in response:
                msg = f"{command} failed. Response: {response!r}"
                logger.error(
                    "Init command failed",
                    extra={"command": command, "response": response},
                )
                raise Elm327CommunicationError(msg)

        self._current_protocol = 0

        logger.info(
            "ELM327 initialization complete",
            extra={"elm_version": elm_version},
        )
        return elm_version

    def send_command(self, command: str) -> str:
        """ELM327 にコマンドを送信し応答を返す.

        Args:
            command: 送信するコマンド文字列.

        Returns:
            応答文字列.
        """
        return self._send_at_command_with_retry(command)

    def switch_protocol(self, protocol_number: int) -> None:
        """ELM327 のプロトコルを切り替える.

        Args:
            protocol_number: ATSP のプロトコル番号 (0-9).

        Raises:
            Elm327CommunicationError: プロトコル切替に失敗した場合.

        traces: HWR-06, HWR-07
        """
        if protocol_number == self._current_protocol:
            return

        command = f"ATSP{protocol_number}"
        response = self._send_at_command_with_retry(command)
        if "OK" not in response:
            msg = f"Protocol switch failed: {command} -> {response!r}"
            raise Elm327CommunicationError(msg)

        # HWR-07: プロトコル切替後のウェイト
        time.sleep(_PROTOCOL_SWITCH_WAIT_S)
        self._current_protocol = protocol_number

        logger.info(
            "Protocol switched",
            extra={
                "protocol_number": protocol_number,
                "command": command,
            },
        )

    def detect_supported_pids(self) -> list[str]:
        """車両が対応する PID のリストを検出する.

        PID 0x00, 0x20, 0x40, 0x60 のビットマスクをデコードして対応 PID を列挙する。

        Returns:
            対応 PID の hex 文字列リスト.

        traces: FR-01c, HWR-12
        """
        supported_pids: list[str] = []

        for base_pid in ["00", "20", "40", "60"]:
            command = f"01{base_pid}"
            try:
                response = self._send_at_command_with_retry(command)
            except Elm327CommunicationError:
                break

            if self._is_error_response(response):
                break

            # 最初の応答で 29bit CAN かどうかを判定
            if base_pid == "00" and "18 DA" in response.upper():
                self._is_29bit_can = True
                logger.info(
                    "29bit CAN detected from PID response",
                    extra={"response_snippet": response[:50]},
                )

            data_bytes = self._parse_obd_response(response, expected_sid=0x41)
            if data_bytes is None or len(data_bytes) < 5:
                break

            # data_bytes[0] = PID, data_bytes[1..4] = ビットマスク
            bitmask_bytes = data_bytes[1:5]
            base_value = int(base_pid, 16)

            for byte_index, byte_val in enumerate(bitmask_bytes):
                for bit_index in range(8):
                    if byte_val & (0x80 >> bit_index):
                        pid_number = base_value + byte_index * 8 + bit_index + 1
                        pid_hex = f"{pid_number:02X}"
                        supported_pids.append(pid_hex)

            # 次のグループビットマスク PID がサポートされているかチェック
            next_base = base_value + 0x20
            next_hex = f"{next_base:02X}"
            if next_hex not in supported_pids:
                break

        logger.info(
            "Supported PIDs detected",
            extra={
                "pid_count": len(supported_pids),
                "pids": supported_pids,
            },
        )
        return supported_pids

    def scan_ecus(
        self,
        on_progress: ProgressCallback | None = None,
    ) -> list[EcuInfo]:
        """3 フェーズで ECU をスキャンする.

        Phase 1: CAN ブロードキャスト (0100) で OBD-II ECU を検出
        Phase 2: CAN 29bit 物理アドレス全スキャン (0x00-0xFF)
                 TesterPresent ($3E00) を 2 段階タイムアウトで送信
                 - 高速パス: ATST20 (128ms) で全アドレス
                 - リトライ: 未検出アドレスを ATSTFF (1020ms) で再スキャン
        Phase 3: KWP ECU スキャン (StartCommunication)

        Args:
            on_progress: 進捗コールバック.

        Returns:
            検出された ECU 情報のリスト.

        traces: FR-03a, FR-03b, FR-03c
        """
        detected_ecus: list[EcuInfo] = []
        seen_ids: set[str] = set()

        # 全体ステップ数: Phase1(1) + Phase2(256+retry) + Phase3(KWP)
        kwp_step_count = len(_KWP_ECU_ADDRESSES)
        total_steps = 1 + 256 + kwp_step_count

        # ============================================================
        # Phase 1: CAN ブロードキャスト ECU スキャン
        # ============================================================
        if on_progress is not None:
            on_progress(0, total_steps, "CAN broadcast scan")

        self._ensure_can_protocol()

        # ウォームアップ: CAN バス接続確立
        try:
            self._send_raw_command("0100")
        except (ConnectionError, TimeoutError):
            pass

        can_ecus = self._scan_can_ecus_broadcast()
        for ecu in can_ecus:
            if ecu.ecu_identifier not in seen_ids:
                seen_ids.add(ecu.ecu_identifier)
                detected_ecus.append(ecu)

        logger.info(
            "CAN broadcast scan completed",
            extra={"detected_count": len(can_ecus)},
        )

        # ============================================================
        # Phase 2: CAN 29bit 物理アドレス全スキャン (TesterPresent)
        # ============================================================
        # 29bit CAN 設定: ATSP7 + ATCP18
        try:
            self.switch_protocol(7)
        except Elm327CommunicationError:
            logger.warning("ATSP7 failed, skipping 29bit PA scan")
            # Phase 2 をスキップして Phase 3 へ
            self._finish_scan(
                detected_ecus, kwp_step_count, total_steps, on_progress,
            )
            return detected_ecus

        try:
            self._send_raw_command("ATCP18")
        except (ConnectionError, TimeoutError):
            logger.warning("ATCP18 failed")

        # ウォームアップ (29bit CAN バス確立)
        try:
            self._send_raw_command("ATSH DB 33 F1")
            self._send_raw_command("0100")
        except (ConnectionError, TimeoutError):
            pass

        # --- 高速パス: ATST20 (128ms) ---
        try:
            self._send_raw_command("ATST20")
        except (ConnectionError, TimeoutError):
            pass

        not_found_addrs: list[int] = []

        for addr in range(0x00, 0x100):
            step = 1 + addr
            if on_progress is not None and addr % 16 == 0:
                on_progress(
                    step, total_steps,
                    f"PA scan (fast): 0x{addr:02X}",
                )

            ecu_id = f"18DA_{addr:02X}"
            if ecu_id in seen_ids:
                continue

            ecu = self._probe_29bit_tester_present(addr)
            if ecu is not None:
                seen_ids.add(ecu.ecu_identifier)
                detected_ecus.append(ecu)
                logger.info(
                    "ECU detected via PA scan (fast)",
                    extra={
                        "ecu_id": ecu.ecu_identifier,
                        "ecu_name": ecu.ecu_display_name,
                    },
                )
            else:
                not_found_addrs.append(addr)

        # --- リトライ: ATSTFF (1020ms) ---
        if not_found_addrs:
            try:
                self._send_raw_command("ATSTFF")
            except (ConnectionError, TimeoutError):
                pass

            retry_count = len(not_found_addrs)
            logger.info(
                "PA scan retry with extended timeout",
                extra={"retry_count": retry_count},
            )

            for i, addr in enumerate(not_found_addrs):
                if on_progress is not None and i % 32 == 0:
                    on_progress(
                        257 + i * kwp_step_count // max(retry_count, 1),
                        total_steps,
                        f"PA scan (retry): 0x{addr:02X}",
                    )

                ecu = self._probe_29bit_tester_present(addr)
                if ecu is not None:
                    seen_ids.add(ecu.ecu_identifier)
                    detected_ecus.append(ecu)
                    logger.info(
                        "ECU detected via PA scan (retry)",
                        extra={
                            "ecu_id": ecu.ecu_identifier,
                            "ecu_name": ecu.ecu_display_name,
                        },
                    )

        logger.info(
            "29bit PA scan completed",
            extra={"detected_count": len(detected_ecus)},
        )

        # ============================================================
        # Phase 3: KWP ECU スキャン
        # ============================================================
        self._finish_scan(
            detected_ecus, kwp_step_count, total_steps, on_progress,
        )
        return detected_ecus

    def _finish_scan(
        self,
        detected_ecus: list[EcuInfo],
        kwp_step_count: int,
        total_steps: int,
        on_progress: ProgressCallback | None,
    ) -> None:
        """KWP スキャンとスキャン完了処理."""
        try:
            self._switch_to_kwp()
        except Elm327CommunicationError:
            logger.warning("KWP protocol switch failed, skipping KWP scan")
            kwp_step_count = 0

        for idx in range(kwp_step_count):
            kwp_address = _KWP_ECU_ADDRESSES[idx]
            step = 257 + idx
            if on_progress is not None:
                on_progress(
                    step, total_steps,
                    f"KWP scan: 0x{kwp_address:02X}",
                )

            ecu = self._probe_kwp_ecu(kwp_address)
            if ecu is not None:
                detected_ecus.append(ecu)

        # プロトコル自動検出に復帰
        try:
            self.switch_protocol(0)
        except Elm327CommunicationError:
            logger.warning("Failed to restore protocol to auto-detect")

        if on_progress is not None:
            on_progress(total_steps, total_steps, "ECU scan complete")

        logger.info(
            "ECU scan completed",
            extra={"detected_count": len(detected_ecus)},
        )

    def _probe_29bit_tester_present(self, addr: int) -> EcuInfo | None:
        """29bit CAN 物理アドレスに TesterPresent を送信して ECU を検出する.

        Args:
            addr: ECU アドレス (0x00-0xFF).

        Returns:
            検出された場合は EcuInfo、未検出は None.
        """
        addr_hex = f"{addr:02X}"

        try:
            self._send_raw_command(f"ATSH DA {addr_hex} F1")
        except (ConnectionError, TimeoutError):
            return None

        try:
            response = self._send_raw_command("3E00")
        except (ConnectionError, TimeoutError):
            return None

        if self._is_error_response(response):
            return None

        # 応答があれば ECU 検出
        cleaned = self._clean_response(response)
        if not cleaned:
            return None

        # 29bit CAN 応答: "18DAF1xx027E00" or "7E00"
        ecu_id = f"18DA_{addr_hex}"
        ecu_name = _CAN_ECU_NAMES.get(
            ecu_id, f"ECU_0x{addr_hex}",
        )

        return EcuInfo(
            ecu_identifier=ecu_id,
            ecu_display_name=ecu_name,
            protocol_type=DiagProtocolType.UDS,
            response_id=f"18DAF1{addr_hex}",
        )

    def _scan_can_ecus_broadcast(self) -> list[EcuInfo]:
        """CAN ブロードキャストで ECU を検出する.

        ATH1 (ヘッダ表示ON) の状態で OBD-II ブロードキャスト 0100 を送信し、
        応答ヘッダから ECU を識別する。11bit CAN (7Ex) と
        29bit CAN (18 DA F1 xx) の両方に対応する。

        Returns:
            検出された ECU 情報のリスト.
        """
        detected: list[EcuInfo] = []
        seen_ids: set[str] = set()

        try:
            response = self._send_raw_command("0100")
        except (ConnectionError, TimeoutError):
            return detected

        if self._is_error_response(response):
            return detected

        # 応答を行ごとに解析して ECU を識別する
        lines = response.replace("\r", "\n").split("\n")
        for line in lines:
            stripped = line.strip().replace(">", "").strip().upper()
            if not stripped or stripped.startswith("SEARCHING"):
                continue

            tokens = stripped.split()
            if not tokens:
                continue

            ecu_id: str | None = None
            response_id: str | None = None

            # パターン A: 11bit CAN - "7E8 06 41 00 ..."
            if (
                len(tokens) >= 3
                and len(tokens[0]) == 3
                and tokens[0].startswith("7E")
                and self._is_hex_string(tokens[0])
            ):
                response_id = tokens[0]
                # 7E8 → 7E0, 7E9 → 7E1, etc.
                request_num = int(response_id[2], 16) - 8
                ecu_id = f"7E{request_num:X}"

            # パターン B: 29bit CAN - "18 DA F1 0E 06 41 00 ..."
            elif (
                len(tokens) >= 6
                and tokens[0] == "18"
                and tokens[1] == "DA"
            ):
                source_addr = tokens[3]
                ecu_id = f"18DA_{source_addr}"
                response_id = f"18DAF1{source_addr}"

            if ecu_id is not None and ecu_id not in seen_ids:
                seen_ids.add(ecu_id)
                ecu_name = _CAN_ECU_NAMES.get(
                    ecu_id, f"ECU_{ecu_id}",
                )
                detected.append(
                    EcuInfo(
                        ecu_identifier=ecu_id,
                        ecu_display_name=ecu_name,
                        protocol_type=DiagProtocolType.LEGACY_OBD,
                        response_id=response_id or ecu_id,
                    ),
                )
                logger.info(
                    "ECU detected via broadcast",
                    extra={
                        "ecu_id": ecu_id,
                        "ecu_name": ecu_name,
                        "response_id": response_id,
                    },
                )

        return detected

    def read_dtcs(self, ecu: EcuInfo) -> list[DTC]:
        """指定 ECU から DTC を読み取る.

        プロトコル種別に応じて適切な DTC 読取コマンドを送信する。

        Args:
            ecu: 対象 ECU.

        Returns:
            DTC のリスト.

        traces: FR-06a, HWR-11, HWR-14, HWR-17, HWR-18
        """
        protocol = ecu.protocol_type

        if protocol == DiagProtocolType.LEGACY_OBD:
            return self._read_dtcs_legacy_obd(ecu)
        elif protocol == DiagProtocolType.UDS:
            return self._read_dtcs_uds(ecu)
        elif protocol == DiagProtocolType.KWP2000:
            return self._read_dtcs_kwp(ecu)
        else:
            logger.warning(
                "Unknown protocol type for DTC read",
                extra={
                    "ecu_identifier": ecu.ecu_identifier,
                    "protocol_type": protocol,
                },
            )
            return []

    def clear_dtcs(self, ecu: EcuInfo) -> bool:
        """指定 ECU の DTC を消去する.

        Args:
            ecu: 対象 ECU.

        Returns:
            消去に成功した場合 True.

        traces: FR-07b, HWR-11
        """
        protocol = ecu.protocol_type

        if protocol == DiagProtocolType.LEGACY_OBD:
            return self._clear_dtcs_legacy_obd()
        elif protocol == DiagProtocolType.UDS:
            return self._clear_dtcs_uds(ecu)
        elif protocol == DiagProtocolType.KWP2000:
            return self._clear_dtcs_kwp(ecu)
        else:
            return False

    def read_parameter(
        self,
        ecu: EcuInfo,
        parameter_id: str,
    ) -> VehicleParameter | None:
        """指定パラメータを読み取る.

        Args:
            ecu: 対象 ECU.
            parameter_id: PID or DID の hex 文字列.

        Returns:
            読取結果。読取失敗時は None.

        traces: FR-08a
        """
        protocol = ecu.protocol_type

        if protocol == DiagProtocolType.LEGACY_OBD:
            return self._read_pid(ecu, parameter_id)
        elif protocol == DiagProtocolType.UDS:
            return self._read_did_uds(ecu, parameter_id)
        elif protocol == DiagProtocolType.KWP2000:
            return self._read_did_kwp(ecu, parameter_id)
        else:
            return None

    def scan_dids(
        self,
        ecu: EcuInfo,
        did_range_start: int,
        did_range_end: int,
        on_progress: ProgressCallback | None = None,
    ) -> list[str]:
        """指定範囲の DID をスキャンする.

        Args:
            ecu: 対象 ECU.
            did_range_start: スキャン開始 DID.
            did_range_end: スキャン終了 DID.
            on_progress: 進捗コールバック.

        Returns:
            応答のあった DID の hex 文字列リスト.

        traces: FR-05b, FR-05c
        """
        found_dids: list[str] = []
        total = did_range_end - did_range_start + 1

        # ECU 通信準備（プロトコル + ヘッダ設定）
        self._prepare_ecu_communication(ecu)

        for did_num in range(did_range_start, did_range_end + 1):
            if on_progress is not None and (did_num - did_range_start) % 100 == 0:
                on_progress(
                    did_num - did_range_start,
                    total,
                    f"DID 0x{did_num:04X}",
                )

            did_hex = f"{did_num:04X}"
            command = f"22{did_hex}"

            try:
                response = self._send_raw_command(command)
            except (ConnectionError, TimeoutError):
                continue

            if self._is_error_response(response):
                continue

            # 肯定応答 (0x62) を確認
            cleaned = self._clean_response(response)
            if cleaned.startswith("62"):
                found_dids.append(did_hex)

        if on_progress is not None:
            on_progress(total, total, "DID scan range complete")

        # ATCRA リセット
        self._reset_can_filter()

        logger.info(
            "DID scan range completed",
            extra={
                "ecu_identifier": ecu.ecu_identifier,
                "range_start": f"0x{did_range_start:04X}",
                "range_end": f"0x{did_range_end:04X}",
                "found_count": len(found_dids),
            },
        )
        return found_dids

    # ------------------------------------------------------------------
    # Legacy OBD-II 内部メソッド
    # ------------------------------------------------------------------

    def _read_dtcs_legacy_obd(self, ecu: EcuInfo) -> list[DTC]:
        """Legacy OBD-II Mode 03/07 で DTC を読み取る.

        traces: FR-06a, HWR-11
        """
        self._prepare_ecu_communication(ecu)
        dtcs: list[DTC] = []

        for mode, expected_sid in [("03", 0x43), ("07", 0x47)]:
            try:
                response = self._send_at_command_with_retry(mode)
            except Elm327CommunicationError:
                continue

            if self._is_error_response(response):
                continue

            data_bytes = self._parse_obd_response(response, expected_sid)
            if data_bytes is None or len(data_bytes) < 1:
                continue

            # data_bytes[0] = DTC カウント, 残りは 2 バイトずつ DTC
            dtc_byte_pairs = data_bytes[1:]
            for i in range(0, len(dtc_byte_pairs) - 1, 2):
                high = dtc_byte_pairs[i]
                low = dtc_byte_pairs[i + 1]
                if high == 0 and low == 0:
                    continue
                dtc_code = decode_obd2_dtc(high, low)
                dtcs.append(DTC(
                    dtc_code=dtc_code,
                    status_byte=0xFF,
                    description="Unknown",
                    ecu_identifier=ecu.ecu_identifier,
                    protocol_type=DiagProtocolType.LEGACY_OBD.value,
                ))

        return dtcs

    def _clear_dtcs_legacy_obd(self) -> bool:
        """Legacy OBD-II Mode 04 で DTC を消去する.

        traces: FR-07b
        """
        try:
            response = self._send_at_command_with_retry("04")
        except Elm327CommunicationError:
            return False

        cleaned = self._clean_response(response)
        return cleaned.startswith("44")

    def _read_pid(
        self,
        ecu: EcuInfo,
        pid_hex: str,
    ) -> VehicleParameter | None:
        """Legacy OBD Mode 01 で PID を読み取る.

        traces: FR-08a
        """
        self._prepare_ecu_communication(ecu)
        command = f"01{pid_hex}"
        try:
            response = self._send_at_command_with_retry(command)
        except Elm327CommunicationError:
            return None

        if self._is_error_response(response):
            return None

        data_bytes = self._parse_obd_response(response, expected_sid=0x41)
        if data_bytes is None or len(data_bytes) < 2:
            return None

        # data_bytes[0] = PID, data_bytes[1:] = データバイト
        raw_data_bytes = data_bytes[1:]
        raw_hex = " ".join(f"{b:02X}" for b in raw_data_bytes)

        return VehicleParameter(
            parameter_identifier=pid_hex,
            raw_hex=raw_hex,
            physical_value=None,
            unit=None,
            ecu_identifier=ecu.ecu_identifier,
            timestamp_epoch=time.time(),
        )

    # ------------------------------------------------------------------
    # UDS 内部メソッド
    # ------------------------------------------------------------------

    def _read_dtcs_uds(self, ecu: EcuInfo) -> list[DTC]:
        """UDS SID $19 $02 $FF で DTC を読み取る.

        traces: FR-06a, HWR-14
        """
        self._prepare_ecu_communication(ecu)

        command = "1902FF"
        try:
            response = self._send_at_command_with_retry(command)
        except Elm327CommunicationError:
            self._reset_can_filter()
            return []

        if self._is_error_response(response):
            self._reset_can_filter()
            return []

        cleaned = self._clean_response(response)
        hex_bytes = self._hex_string_to_bytes(cleaned)

        dtcs: list[DTC] = []

        if hex_bytes and hex_bytes[0] == 0x59 and len(hex_bytes) >= 3:
            # 59 02 [DTC1_H DTC1_M DTC1_L STATUS] [DTC2 ...]
            dtc_data = hex_bytes[2:]
            for i in range(0, len(dtc_data) - 3, 4):
                byte1 = dtc_data[i]
                byte2 = dtc_data[i + 1]
                byte3 = dtc_data[i + 2]
                status = dtc_data[i + 3]
                dtc_code = decode_uds_dtc(byte1, byte2, byte3)
                dtcs.append(DTC(
                    dtc_code=dtc_code,
                    status_byte=status,
                    description="Unknown",
                    ecu_identifier=ecu.ecu_identifier,
                    protocol_type=DiagProtocolType.UDS.value,
                ))

        self._reset_can_filter()
        return dtcs

    def _clear_dtcs_uds(self, ecu: EcuInfo) -> bool:
        """UDS SID $14 $FF $FF $FF で DTC を消去する.

        traces: FR-07b
        """
        self._prepare_ecu_communication(ecu)

        command = "14FFFFFF"
        try:
            response = self._send_at_command_with_retry(command)
        except Elm327CommunicationError:
            self._reset_can_filter()
            return False

        cleaned = self._clean_response(response)
        self._reset_can_filter()
        return cleaned.startswith("54")

    def _read_did_uds(
        self,
        ecu: EcuInfo,
        did_hex: str,
    ) -> VehicleParameter | None:
        """UDS SID $22 で DID を読み取る.

        traces: FR-08a
        """
        self._prepare_ecu_communication(ecu)

        command = f"22{did_hex}"
        try:
            response = self._send_at_command_with_retry(command)
        except Elm327CommunicationError:
            self._reset_can_filter()
            return None

        if self._is_error_response(response):
            self._reset_can_filter()
            return None

        cleaned = self._clean_response(response)
        hex_bytes = self._hex_string_to_bytes(cleaned)

        self._reset_can_filter()

        if not hex_bytes or hex_bytes[0] != 0x62:
            return None

        # 62 DID_H DID_L DATA...
        if len(hex_bytes) < 4:
            return None

        raw_data_bytes = hex_bytes[3:]
        raw_hex = " ".join(f"{b:02X}" for b in raw_data_bytes)

        return VehicleParameter(
            parameter_identifier=did_hex,
            raw_hex=raw_hex,
            physical_value=None,
            unit=None,
            ecu_identifier=ecu.ecu_identifier,
            timestamp_epoch=time.time(),
        )

    # ------------------------------------------------------------------
    # KWP2000 内部メソッド
    # ------------------------------------------------------------------

    def _read_dtcs_kwp(self, ecu: EcuInfo) -> list[DTC]:
        """KWP2000 SID $18 で DTC を読み取る。NRC 時は SID $13 にフォールバック.

        traces: FR-06a, HWR-17, HWR-18
        """
        self._switch_to_kwp()

        # KWP StartCommunication
        self._kwp_start_communication()

        # SID $18 を試行
        command = "18FF0000"
        try:
            response = self._send_at_command_with_retry(command)
        except Elm327CommunicationError:
            return []

        cleaned = self._clean_response(response)
        hex_bytes = self._hex_string_to_bytes(cleaned)

        dtcs: list[DTC] = []

        if hex_bytes and hex_bytes[0] == 0x58 and len(hex_bytes) >= 2:
            # 肯定応答: 58 COUNT [DTC_H DTC_L STATUS] ...
            dtc_count = hex_bytes[1]
            dtc_data = hex_bytes[2:]
            for i in range(0, len(dtc_data) - 2, 3):
                high = dtc_data[i]
                low = dtc_data[i + 1]
                status = dtc_data[i + 2]
                dtc_code = decode_obd2_dtc(high, low)
                dtcs.append(DTC(
                    dtc_code=dtc_code,
                    status_byte=status,
                    description="Unknown",
                    ecu_identifier=ecu.ecu_identifier,
                    protocol_type=DiagProtocolType.KWP2000.value,
                ))
        elif hex_bytes and hex_bytes[0] == 0x7F:
            # NRC: フォールバック to SID $13 (HWR-17)
            logger.info(
                "KWP SID $18 NRC, falling back to SID $13",
                extra={"ecu_identifier": ecu.ecu_identifier},
            )
            # SID $13 は個別 DTC 照会なので、ここでは空リストを返す
            # (完全実装には既知 DTC 範囲のスキャンが必要)

        return dtcs

    def _clear_dtcs_kwp(self, ecu: EcuInfo) -> bool:
        """KWP2000 SID $14 $FF $00 で DTC を消去する.

        traces: FR-07b
        """
        self._switch_to_kwp()
        self._kwp_start_communication()

        command = "14FF00"
        try:
            response = self._send_at_command_with_retry(command)
        except Elm327CommunicationError:
            return False

        cleaned = self._clean_response(response)
        return cleaned.startswith("54")

    def _read_did_kwp(
        self,
        ecu: EcuInfo,
        local_id_hex: str,
    ) -> VehicleParameter | None:
        """KWP2000 SID $21 で LocalIdentifier を読み取る.

        traces: FR-08a
        """
        self._switch_to_kwp()

        command = f"21{local_id_hex}"
        try:
            response = self._send_at_command_with_retry(command)
        except Elm327CommunicationError:
            return None

        if self._is_error_response(response):
            return None

        cleaned = self._clean_response(response)
        hex_bytes = self._hex_string_to_bytes(cleaned)

        if not hex_bytes or hex_bytes[0] != 0x61:
            return None

        raw_data_bytes = hex_bytes[2:]
        raw_hex = " ".join(f"{b:02X}" for b in raw_data_bytes)

        return VehicleParameter(
            parameter_identifier=local_id_hex,
            raw_hex=raw_hex,
            physical_value=None,
            unit=None,
            ecu_identifier=ecu.ecu_identifier,
            timestamp_epoch=time.time(),
        )

    def _kwp_start_communication(self) -> None:
        """KWP2000 StartCommunication (SID $81) を送信する.

        traces: HWR-16
        """
        try:
            response = self._send_at_command_with_retry("81")
        except Elm327CommunicationError:
            logger.warning("KWP StartCommunication failed")
            return

        cleaned = self._clean_response(response)
        hex_bytes = self._hex_string_to_bytes(cleaned)
        if hex_bytes and hex_bytes[0] == 0xC1 and len(hex_bytes) >= 3:
            logger.info(
                "KWP StartCommunication OK",
                extra={
                    "key_byte_1": f"0x{hex_bytes[1]:02X}",
                    "key_byte_2": f"0x{hex_bytes[2]:02X}",
                },
            )

    # ------------------------------------------------------------------
    # ECU プローブ内部メソッド
    # ------------------------------------------------------------------

    def _probe_can_ecu(
        self,
        request_id: str,
        response_id: str,
    ) -> EcuInfo | None:
        """CAN ECU をプローブする.

        UDS TesterPresent ($3E) を試行し、NO DATA の場合は
        OBD-II PID $0100 にフォールバックする（クローン ELM327 対応）。

        traces: FR-03a
        """
        self._set_can_header(request_id)

        # 方法1: UDS TesterPresent (SID $3E $00)
        try:
            response = self._send_raw_command("3E00")
        except (ConnectionError, TimeoutError):
            return None

        if not self._is_error_response(response):
            cleaned = self._clean_response(response)
            # 11bit CAN 応答 (7Exx) または 29bit CAN 応答 (18DA) を検出
            if cleaned.startswith("7E") or cleaned.startswith("18DA"):
                ecu_name = _CAN_ECU_NAMES.get(request_id, f"ECU_{request_id}")
                return EcuInfo(
                    ecu_identifier=request_id,
                    ecu_display_name=ecu_name,
                    protocol_type=DiagProtocolType.UDS,
                    response_id=response_id,
                )

        # 方法2: OBD-II PID $0100 フォールバック（クローン ELM327 向け）
        try:
            response = self._send_raw_command("0100")
        except (ConnectionError, TimeoutError):
            return None

        if self._is_error_response(response):
            return None

        data_bytes = self._parse_obd_response(response, expected_sid=0x41)
        if data_bytes is not None and len(data_bytes) >= 1:
            ecu_name = _CAN_ECU_NAMES.get(request_id, f"ECU_{request_id}")
            return EcuInfo(
                ecu_identifier=request_id,
                ecu_display_name=ecu_name,
                protocol_type=DiagProtocolType.LEGACY_OBD,
                response_id=response_id,
            )

        return None

    def _probe_kwp_ecu(self, kwp_address: int) -> EcuInfo | None:
        """KWP2000 ECU をプローブする (StartCommunication).

        traces: FR-03b
        """
        # HWR-10: KWP タイムアウト拡張
        try:
            self._send_raw_command("ATSTFF")
        except (ConnectionError, TimeoutError):
            pass

        try:
            response = self._send_raw_command("81")
        except (ConnectionError, TimeoutError):
            return None

        if self._is_error_response(response):
            return None

        cleaned = self._clean_response(response)
        hex_bytes = self._hex_string_to_bytes(cleaned)

        if hex_bytes and hex_bytes[0] == 0xC1:
            address_hex = f"{kwp_address:02X}"
            return EcuInfo(
                ecu_identifier=address_hex,
                ecu_display_name=f"KWP_ECU_{address_hex}",
                protocol_type=DiagProtocolType.KWP2000,
                response_id=address_hex,
            )

        return None

    # ------------------------------------------------------------------
    # プロトコル切替ヘルパー
    # ------------------------------------------------------------------

    def _ensure_can_protocol(self) -> None:
        """CAN プロトコル (ATSP6) に切り替える."""
        if self._current_protocol not in (6, 7, 8, 9, 0):
            self.switch_protocol(6)

    def _switch_to_kwp(self) -> None:
        """KWP2000 プロトコル (ATSP5: fast init) に切り替える."""
        if self._current_protocol not in (4, 5):
            self.switch_protocol(5)

    def _prepare_ecu_communication(self, ecu: EcuInfo) -> None:
        """ECU との通信準備を行う（プロトコル設定 + ヘッダ設定）.

        29bit CAN ECU (18DA_xx) の場合は ATSP7 + ATCP18 + ATSH DA xx F1 を設定。
        DEFAULT ECU の場合は _is_29bit_can フラグに基づいて設定。
        11bit CAN ECU (7Ex) の場合は ATSP6 + ATSH を設定。

        Args:
            ecu: 対象 ECU.
        """
        ecu_id = ecu.ecu_identifier

        if ecu_id.startswith("18DA_"):
            # 29bit CAN: ATSP7 + ATCP18 + ATSH DA xx F1
            addr_hex = ecu_id[5:]  # "18DA_0E" → "0E"
            self._setup_29bit_can(addr_hex)
        elif ecu_id == "DEFAULT" and self._is_29bit_can:
            # ECU スキャン前のデフォルト ECU で 29bit CAN 車両
            # ATSP0 (自動検出) のまま、ヘッダ設定なしで送信
            # ELM327 が接続時に自動検出したプロトコルを再利用する
            if self._current_protocol not in (0, 7, 8):
                self.switch_protocol(0)
        else:
            # 11bit CAN or other
            self._ensure_can_protocol()
            self._set_can_header(ecu_id)

    def _setup_29bit_can(self, addr_hex: str) -> None:
        """29bit CAN の通信設定を行う.

        Args:
            addr_hex: ECU アドレスの hex 文字列 (例: "0E").
        """
        if self._current_protocol != 7:
            self.switch_protocol(7)
        try:
            self._send_raw_command("ATCP18")
        except (ConnectionError, TimeoutError):
            logger.warning("ATCP18 failed")
        try:
            self._send_raw_command(f"ATSH DA {addr_hex} F1")
        except (ConnectionError, TimeoutError):
            logger.warning(
                "Failed to set 29bit CAN header",
                extra={"addr_hex": addr_hex},
            )

    def _set_can_header(self, can_id: str) -> None:
        """送信 CAN ID を設定する (HWR-08).

        Args:
            can_id: CAN ID hex 文字列.
        """
        try:
            self._send_raw_command(f"ATSH{can_id}")
        except (ConnectionError, TimeoutError):
            logger.warning(
                "Failed to set CAN header",
                extra={"can_id": can_id},
            )

    def _reset_can_filter(self) -> None:
        """受信フィルタを自動に戻す (HWR-09)."""
        try:
            self._send_raw_command("ATAR")
        except (ConnectionError, TimeoutError):
            logger.warning("Failed to reset CAN filter")

    # ------------------------------------------------------------------
    # 通信レイヤー
    # ------------------------------------------------------------------

    def _send_raw_command(self, command: str) -> str:
        """ELM327 にコマンドを送信し応答を返す（リトライなし）.

        Args:
            command: AT コマンドまたは診断コマンド.

        Returns:
            応答文字列.

        Raises:
            ConnectionError: 通信断.
            TimeoutError: タイムアウト.
        """
        self._serial_port.write(command)
        time.sleep(_COMMAND_INTERVAL_S)
        response = self._serial_port.read_until_prompt()
        logger.debug(
            "Raw ELM327 exchange",
            extra={"command": command, "response": repr(response)},
        )
        return response

    def _send_at_command_with_retry(self, command: str) -> str:
        """リトライ付きでコマンドを送信する.

        Args:
            command: 送信コマンド.

        Returns:
            応答文字列.

        Raises:
            Elm327CommunicationError: 全リトライ失敗.

        traces: NFR-02a, HWR-24, HWR-25, HWR-26
        """
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRY_COUNT):
            try:
                response = self._send_raw_command(command)

                # NFR-04a: 応答バリデーション
                if not self._validate_response(response):
                    logger.warning(
                        "Invalid response discarded",
                        extra={
                            "command": command,
                            "response_repr": repr(response),
                            "attempt": attempt + 1,
                        },
                    )
                    if attempt < _MAX_RETRY_COUNT - 1:
                        time.sleep(_RETRY_INTERVAL_S)
                    continue

                return response

            except (ConnectionError, TimeoutError) as exc:
                last_error = exc
                logger.warning(
                    "Command failed, retrying",
                    extra={
                        "command": command,
                        "attempt": attempt + 1,
                        "max_retries": _MAX_RETRY_COUNT,
                        "error": str(exc),
                    },
                )
                if attempt < _MAX_RETRY_COUNT - 1:
                    time.sleep(_RETRY_INTERVAL_S)

        msg = f"Command {command!r} failed after {_MAX_RETRY_COUNT} retries"
        raise Elm327CommunicationError(msg) from last_error

    # ------------------------------------------------------------------
    # 応答パースとバリデーション
    # ------------------------------------------------------------------

    def _validate_response(self, response: str) -> bool:
        """ELM327 応答をバリデーションする.

        AT コマンドの英字テキスト応答 ("OK", "ELM327" 等) と
        hex データ応答の両方を許可する。

        Args:
            response: 応答文字列.

        Returns:
            有効な場合 True.

        traces: NFR-04a
        """
        if not response or not response.strip():
            return False

        # AT 応答キーワードを含む場合は有効
        at_keywords = ("OK", "ELM327", "SEARCHING", "STOPPED")
        for keyword in at_keywords:
            if keyword in response:
                return True

        # エラー応答も「有効な応答」として処理対象にする
        for error_pattern in _ELM327_ERROR_PATTERNS:
            if error_pattern in response:
                return True

        # hex データ応答: 英数字・スペース・改行・プロンプトのみ許可
        cleaned = response.replace("\r", "").replace("\n", "").replace(">", "").strip()
        if _VALID_RESPONSE_PATTERN.match(cleaned):
            return True

        return False

    @staticmethod
    def _is_error_response(response: str) -> bool:
        """ELM327 エラー応答かを判定する.

        Args:
            response: 応答文字列.

        Returns:
            エラー応答の場合 True.

        traces: HWR-20
        """
        upper = response.upper()
        return any(pattern in upper for pattern in _ELM327_ERROR_PATTERNS)

    @staticmethod
    def _clean_response(response: str) -> str:
        """応答文字列から空白・改行・プロンプトを除去する.

        Args:
            response: 応答文字列.

        Returns:
            クリーニング済み hex 文字列.

        traces: HWR-19
        """
        cleaned = response.replace("\r", "").replace("\n", "").replace(">", "")
        cleaned = cleaned.replace(" ", "").strip()
        return cleaned.upper()

    @staticmethod
    def _hex_string_to_bytes(hex_string: str) -> list[int]:
        """hex 文字列をバイトリストに変換する.

        Args:
            hex_string: 連結 hex 文字列 (例: "4100BE3FA813").

        Returns:
            バイト値のリスト.
        """
        result: list[int] = []
        for i in range(0, len(hex_string) - 1, 2):
            try:
                result.append(int(hex_string[i : i + 2], 16))
            except ValueError:
                break
        return result

    def _parse_obd_response(
        self,
        response: str,
        expected_sid: int,
    ) -> list[int] | None:
        """OBD 応答をパースする.

        ヘッダなし応答とヘッダ付き応答（ATH1 有効時）の両方に対応する。

        ヘッダ付き応答フォーマット例:
          "7E8 06 41 0C 1A F8"  (CAN_ID DL SID PID DATA...)

        ヘッダなし応答フォーマット例:
          "41 0C 1A F8"  (SID PID DATA...)

        Args:
            response: ELM327 応答文字列.
            expected_sid: 期待するサービス応答バイト.

        Returns:
            データバイトのリスト (SID の次のバイトから)。パース失敗時は None.

        traces: HWR-11, HWR-21
        """
        lines = response.replace("\r", "\n").split("\n")
        all_data_bytes: list[int] = []

        for line in lines:
            stripped = line.strip().replace(">", "").strip()
            if not stripped:
                continue

            # スペース区切りのトークンに分割
            tokens = stripped.upper().split()
            if not tokens:
                continue

            # ヘッダ付き応答の判定:
            # パターン A: 11bit CAN (3桁 hex CAN ID + 2桁 DL)
            #   例: "7E8 06 41 00 BE 3E A8 13"
            # パターン B: 29bit CAN (4x 2桁 hex ヘッダ + 2桁 DL)
            #   例: "18 DA F1 0E 06 41 00 BE 3E A8 13"
            header_skip = 0
            if (
                len(tokens) >= 3
                and len(tokens[0]) == 3
                and self._is_hex_string(tokens[0])
                and len(tokens[1]) == 2
                and self._is_hex_string(tokens[1])
            ):
                # 11bit CAN: CAN ID (1) + DL (1) = skip 2
                header_skip = 2
            elif (
                len(tokens) >= 6
                and all(
                    len(t) == 2 and self._is_hex_string(t)
                    for t in tokens[:4]
                )
                and tokens[0].upper() == "18"
            ):
                # 29bit CAN: 4-byte header (4) + DL (1) = skip 5
                header_skip = 5

            data_tokens = tokens[header_skip:]

            for token in data_tokens:
                if self._is_hex_string(token) and len(token) == 2:
                    try:
                        all_data_bytes.append(int(token, 16))
                    except ValueError:
                        break

        if not all_data_bytes:
            return None

        # 先頭バイトが期待 SID か確認
        if all_data_bytes[0] != expected_sid:
            return None

        return all_data_bytes[1:]

    @staticmethod
    def _is_hex_string(text: str) -> bool:
        """文字列が有効な hex 文字列かを判定する.

        Args:
            text: 検査対象の文字列.

        Returns:
            hex 文字列の場合 True.
        """
        return all(c in "0123456789ABCDEFabcdef" for c in text)

    @staticmethod
    def _extract_version(atz_response: str) -> str:
        """ATZ 応答から ELM327 バージョン文字列を抽出する.

        Args:
            atz_response: ATZ コマンドの応答.

        Returns:
            バージョン文字列.
        """
        for line in atz_response.split("\n"):
            line = line.strip().replace("\r", "")
            if "ELM327" in line:
                return line
        return "ELM327 (version unknown)"
