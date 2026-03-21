"""PoC v2: 18DB ファンクショナル + 18DA 物理を併用した ECU 全検出.

v1 からの改善:
  - ATCAF0 を使わない（クローン ELM327 との相性問題回避）
  - タイムアウトを延長（初回 10 秒、通常 5 秒）
  - 物理スキャンは前回検出済みの 0x0E, 0x30, 0x60 を含む重点アドレスのみ
  - 全検出 ECU に対して詳細情報取得

使い方:
  python poc/can29bit_functional_scan_v2.py COM3
"""

import logging
import serial
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

KNOWN_ECU_NAMES: dict[int, str] = {
    0x01: "Engine #1",
    0x02: "Transmission",
    0x03: "ABS/ESC",
    0x04: "Body Control",
    0x05: "Climate Control",
    0x07: "Instrument Cluster",
    0x08: "Steering (EPS)",
    0x09: "Airbag/SRS",
    0x0A: "Door (Driver)",
    0x0B: "Door (Passenger)",
    0x0E: "Engine (OBD-II)",
    0x10: "Engine #2",
    0x18: "Transmission #2",
    0x28: "ABS/VSC",
    0x30: "EPS / Suspension",
    0x38: "Parking Assist",
    0x40: "Body/BCM",
    0x44: "Gateway",
    0x47: "Window Control",
    0x50: "Immobilizer",
    0x58: "TPMS",
    0x60: "Headlamp / Body #2",
    0x68: "Audio/Infotainment",
    0x70: "Telematics",
    0x78: "Power Steering",
    0x7E: "Gateway #2",
}

# 物理スキャン対象（前回検出 + 主要アドレス）
PHYSICAL_SCAN_TARGETS: list[int] = [
    0x01, 0x02, 0x03, 0x04, 0x05, 0x07, 0x08, 0x09,
    0x0A, 0x0B, 0x0E, 0x10, 0x11, 0x18, 0x20, 0x28,
    0x30, 0x38, 0x40, 0x44, 0x47, 0x50, 0x58, 0x60,
    0x68, 0x70, 0x78, 0x7E,
]


_NRC_RESPONSE_PENDING = "7F"
_NRC_PENDING_CODE = "78"
_P2_STAR_EXTENSION_S = 5.0
_MAX_PENDING_RETRIES = 3


def _contains_response_pending(data: bytes) -> bool:
    """応答バイト列に NRC 0x78 (Response Pending) が含まれるかチェック."""
    text = data.decode("ascii", errors="replace").upper()
    # 29bit CAN: "18 DA F1 xx .. 7F ss 78" のパターン
    # 7F xx 78 が含まれていれば Response Pending
    tokens = text.replace("\r", " ").replace("\n", " ").split()
    for i in range(len(tokens) - 2):
        if tokens[i] == _NRC_RESPONSE_PENDING and tokens[i + 2] == _NRC_PENDING_CODE:
            return True
    return False


def send_command(ser: serial.Serial, command: str, timeout: float = 5.0) -> str:
    """ELM327 にコマンドを送信し、プロンプト '>' まで応答を読む.

    NRC 0x78 (Response Pending) を検出した場合、P2*server (5秒) 分
    タイムアウトを延長して本応答を待つ。最大 3 回まで延長。
    """
    ser.reset_input_buffer()
    ser.write(f"{command}\r".encode("ascii"))
    time.sleep(0.05)

    end_time = time.time() + timeout
    response = b""
    pending_count = 0

    while time.time() < end_time:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            response += chunk

            # NRC 0x78 検出 → タイムアウト延長
            if (
                pending_count < _MAX_PENDING_RETRIES
                and _contains_response_pending(chunk)
            ):
                pending_count += 1
                end_time = time.time() + _P2_STAR_EXTENSION_S
                logger.debug(
                    f"NRC 0x78 detected for '{command}', "
                    f"extending timeout ({pending_count}/{_MAX_PENDING_RETRIES})"
                )

            if b">" in response:
                break
        time.sleep(0.03)

    if pending_count > 0:
        logger.info(
            f"  Response Pending x{pending_count} for '{command}'"
        )

    decoded = response.decode("ascii", errors="replace").strip()
    lines = decoded.split("\r")
    result_lines = [
        line.strip()
        for line in lines
        if line.strip()
        and line.strip() != command
        and line.strip() != ">"
        and "SEARCHING" not in line.upper()
    ]
    return "\n".join(result_lines)


def extract_source_addresses(response: str) -> dict[str, list[str]]:
    """応答から 29bit CAN ソースアドレスと応答行を抽出する.

    Returns:
        {addr_hex: [response_lines]} の辞書.
    """
    result: dict[str, list[str]] = {}
    for line in response.split("\n"):
        tokens = line.strip().upper().split()
        if (
            len(tokens) >= 4
            and tokens[0] == "18"
            and tokens[1] == "DA"
            and tokens[2] == "F1"
        ):
            src = tokens[3]
            if src not in result:
                result[src] = []
            result[src].append(line.strip())
    return result


def init_elm327(ser: serial.Serial) -> None:
    """ELM327 を初期化する."""
    logger.info("=== ELM327 初期化 ===")
    send_command(ser, "ATZ", timeout=5.0)
    send_command(ser, "ATE0")
    send_command(ser, "ATL0")
    send_command(ser, "ATH1")
    send_command(ser, "ATS1")
    send_command(ser, "ATCAF1")

    resp = send_command(ser, "ATSP7")
    logger.info(f"ATSP7 (29bit CAN 500k) -> {resp}")

    resp = send_command(ser, "ATCP18")
    logger.info(f"ATCP18 -> {resp}")

    # タイムアウトをデフォルト最大に設定 (FF = 1020ms)
    resp = send_command(ser, "ATSTFF")
    logger.info(f"ATSTFF (timeout 1020ms) -> {resp}")

    logger.info("初期化完了")


def functional_test(
    ser: serial.Serial,
    cmd: str,
    desc: str,
    timeout: float = 10.0,
) -> dict[str, list[str]]:
    """ファンクショナルアドレスでコマンドを送信し、応答した ECU を返す."""
    logger.info(f"")
    logger.info(f"--- {desc} ---")

    send_command(ser, "ATSH DB 33 F1", timeout=2.0)

    resp = send_command(ser, cmd, timeout=timeout)

    if "NO DATA" in resp.upper() or not resp.strip():
        logger.info(f"  応答なし (NO DATA)")
        return {}

    ecus = extract_source_addresses(resp)
    logger.info(f"  応答 ECU: {len(ecus)} 個")
    for addr, lines in ecus.items():
        addr_int = int(addr, 16)
        name = KNOWN_ECU_NAMES.get(addr_int, "Unknown")
        logger.info(f"    0x{addr} ({name}): {lines[0]}")
        for extra_line in lines[1:]:
            logger.info(f"      {extra_line}")

    return ecus


def physical_probe(
    ser: serial.Serial,
    addr: int,
    timeout: float = 5.0,
) -> bool:
    """物理アドレスで TesterPresent を送信し、応答があるか確認する."""
    addr_hex = f"{addr:02X}"

    send_command(ser, f"ATSH DA {addr_hex} F1", timeout=2.0)
    resp = send_command(ser, "3E00", timeout=timeout)

    if "NO DATA" in resp.upper() or "ERROR" in resp.upper() or "?" in resp:
        return False

    return bool(resp.strip())


def get_ecu_details(ser: serial.Serial, addr_hex: str) -> dict[str, str]:
    """検出済み ECU の詳細情報を物理アドレスで取得する."""
    details: dict[str, str] = {}

    send_command(ser, f"ATSH DA {addr_hex} F1", timeout=2.0)

    commands = [
        ("3E00", "TesterPresent"),
        ("1001", "DiagSession Default"),
        ("1003", "DiagSession Extended"),
        ("0100", "OBD-II PIDs"),
        ("1902FF", "ReadDTC"),
        ("22F190", "VIN"),
        ("22F187", "Spare Part No"),
        ("22F18A", "ECU SW No"),
        ("22F18C", "ECU Serial"),
        ("22F191", "ECU HW No"),
    ]

    for cmd, desc in commands:
        resp = send_command(ser, cmd, timeout=5.0)
        is_ok = (
            "NO DATA" not in resp.upper()
            and "ERROR" not in resp.upper()
            and "?" not in resp
            and resp.strip()
        )
        if is_ok:
            first_line = resp.split("\n")[0]
            details[desc] = first_line
        else:
            # NRC を解析
            if "7F" in resp.upper():
                details[desc] = f"NRC: {resp.split(chr(10))[0].strip()}"

    return details


def main() -> None:
    """メインエントリーポイント."""
    if len(sys.argv) < 2:
        print("Usage: python poc/can29bit_functional_scan_v2.py <COM_PORT>")
        sys.exit(1)

    port = sys.argv[1]
    logger.info(f"PoC v2: ファンクショナル + 物理 併用スキャン on {port}")

    try:
        ser = serial.Serial(port=port, baudrate=38400, timeout=10.0, write_timeout=5.0)
    except serial.SerialException as exc:
        logger.error(f"シリアルポートを開けません: {exc}")
        sys.exit(1)

    all_detected: dict[str, str] = {}  # addr_hex -> detection_method

    try:
        init_elm327(ser)

        # ============================================================
        # Phase 1: ファンクショナルアドレス (18 DB 33 F1) でブロードキャスト
        # ============================================================
        logger.info("")
        logger.info("=" * 60)
        logger.info("Phase 1: ファンクショナルアドレス スキャン")
        logger.info("=" * 60)

        func_tests = [
            ("3E00", "TesterPresent"),
            ("1001", "DiagSessionControl Default"),
            ("1003", "DiagSessionControl Extended"),
            ("1902FF", "ReadDTCByStatusMask"),
            ("0100", "OBD-II Supported PIDs"),
            ("0902", "OBD-II VIN Request"),
        ]

        for cmd, desc in func_tests:
            ecus = functional_test(ser, cmd, desc, timeout=10.0)
            for addr in ecus:
                if addr not in all_detected:
                    all_detected[addr] = f"functional ({desc})"

        # ============================================================
        # Phase 2: 物理アドレス (18 DA xx F1) で重点スキャン
        # ============================================================
        logger.info("")
        logger.info("=" * 60)
        logger.info("Phase 2: 物理アドレス 重点スキャン")
        logger.info(f"  対象: {len(PHYSICAL_SCAN_TARGETS)} アドレス")
        logger.info("=" * 60)

        for i, addr in enumerate(PHYSICAL_SCAN_TARGETS):
            addr_hex = f"{addr:02X}"
            if addr_hex in all_detected:
                logger.info(f"  0x{addr_hex}: Phase 1 で検出済み、スキップ")
                continue

            found = physical_probe(ser, addr, timeout=5.0)
            if found:
                name = KNOWN_ECU_NAMES.get(addr, "Unknown")
                all_detected[addr_hex] = "physical (TesterPresent)"
                logger.info(f"  ★ 0x{addr_hex} ({name}): 検出!")
            else:
                # 進捗は 8 アドレスごとに表示
                if (i + 1) % 8 == 0:
                    logger.info(
                        f"  スキャン進捗: {i + 1}/{len(PHYSICAL_SCAN_TARGETS)}, "
                        f"検出: {len(all_detected)}"
                    )

        # ============================================================
        # Phase 3: 全検出 ECU の詳細情報取得
        # ============================================================
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Phase 3: 検出 ECU の詳細情報取得 ({len(all_detected)} 個)")
        logger.info("=" * 60)

        ecu_details: dict[str, dict[str, str]] = {}
        for addr_hex in sorted(all_detected.keys()):
            addr_int = int(addr_hex, 16)
            name = KNOWN_ECU_NAMES.get(addr_int, "Unknown")
            logger.info(f"")
            logger.info(f"--- 0x{addr_hex} ({name}) ---")
            logger.info(f"  検出方法: {all_detected[addr_hex]}")

            details = get_ecu_details(ser, addr_hex)
            ecu_details[addr_hex] = details

            for svc, resp in details.items():
                logger.info(f"  {svc}: {resp}")

        # ============================================================
        # サマリー
        # ============================================================
        logger.info("")
        logger.info("=" * 60)
        logger.info("=== 最終サマリー ===")
        logger.info("=" * 60)
        logger.info(f"検出 ECU 総数: {len(all_detected)}")
        logger.info("")
        logger.info(f"{'Addr':<8} {'Name':<25} {'検出方法':<35} {'対応サービス'}")
        logger.info("-" * 100)

        for addr_hex in sorted(all_detected.keys()):
            addr_int = int(addr_hex, 16)
            name = KNOWN_ECU_NAMES.get(addr_int, "Unknown")
            method = all_detected[addr_hex]
            details = ecu_details.get(addr_hex, {})
            services = ", ".join(
                k for k, v in details.items() if not v.startswith("NRC")
            )
            logger.info(
                f"0x{addr_hex:<6} {name:<25} {method:<35} {services}"
            )

    except KeyboardInterrupt:
        logger.info("\n中断されました")
        if all_detected:
            logger.info(f"ここまでの検出: {len(all_detected)} 個")
            for addr_hex in sorted(all_detected.keys()):
                addr_int = int(addr_hex, 16)
                name = KNOWN_ECU_NAMES.get(addr_int, "Unknown")
                logger.info(f"  0x{addr_hex} ({name})")
    except Exception as exc:
        logger.error(f"エラー: {exc}", exc_info=True)
    finally:
        ser.close()
        logger.info("シリアルポートを閉じました")


if __name__ == "__main__":
    main()
