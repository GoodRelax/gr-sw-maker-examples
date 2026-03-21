"""PoC v3: 全 PA スキャン — F186 + 250kbps 対応.

v2 からの改善:
  - TesterPresent に加えて $22 F186 (ActiveDiagnosticSession) でもプローブ
  - 500kbps (ATSP7) に加えて 250kbps (ATSP8) もスキャン
  - ウォームアップ済み

使い方:
  python poc/can29bit_full_scan_v3.py COM3
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
    0x01: "Engine #1", 0x02: "Transmission", 0x03: "ABS/ESC",
    0x04: "Body Control", 0x05: "Climate Control", 0x06: "Seat Module",
    0x07: "Instrument Cluster", 0x08: "Steering", 0x09: "Airbag/SRS",
    0x0A: "Door (Driver)", 0x0B: "Door (Passenger)", 0x0E: "Engine (OBD-II)",
    0x10: "Engine #2", 0x18: "Transmission #2", 0x20: "Hybrid/EV",
    0x28: "ABS/VSC", 0x30: "EPS / Suspension", 0x38: "Parking Assist",
    0x40: "Body/BCM", 0x44: "Gateway", 0x47: "Window Control",
    0x50: "Immobilizer", 0x58: "TPMS", 0x60: "Headlamp / Body #2",
    0x68: "Audio/Infotainment", 0x70: "Telematics",
    0x78: "Power Steering (EPS)", 0x7E: "Gateway #2",
}

_MAX_PENDING_RETRIES = 3
_P2_STAR_EXTENSION_S = 5.0

# プローブコマンド（どれか1つでも応答すれば ECU 検出とする）
PROBE_COMMANDS: list[tuple[str, str]] = [
    ("3E00", "TesterPresent"),
    ("22F186", "ReadDID ActiveSession"),
    ("1001", "DiagSessionControl"),
]


def _contains_response_pending(data: bytes) -> bool:
    """NRC 0x78 を検出する."""
    text = data.decode("ascii", errors="replace").upper()
    tokens = text.replace("\r", " ").replace("\n", " ").split()
    for i in range(len(tokens) - 2):
        if tokens[i] == "7F" and tokens[i + 2] == "78":
            return True
    return False


def send_command(ser: serial.Serial, command: str, timeout: float = 5.0) -> tuple[str, int]:
    """ELM327 にコマンドを送信（NRC 0x78 対応）."""
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
            if (
                pending_count < _MAX_PENDING_RETRIES
                and _contains_response_pending(chunk)
            ):
                pending_count += 1
                end_time = time.time() + _P2_STAR_EXTENSION_S
            if b">" in response:
                break
        time.sleep(0.03)

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
    return "\n".join(result_lines), pending_count


def send_cmd(ser: serial.Serial, command: str, timeout: float = 5.0) -> str:
    """send_command ラッパー."""
    resp, _ = send_command(ser, command, timeout)
    return resp


def is_positive(resp: str) -> bool:
    """有効な応答かを判定する."""
    upper = resp.upper()
    return bool(
        resp.strip()
        and "NO DATA" not in upper
        and "ERROR" not in upper
        and "?" not in resp
    )


def warmup(ser: serial.Serial) -> None:
    """CAN バスを確立する."""
    logger.info("CAN バス ウォームアップ中...")
    send_cmd(ser, "ATSH DB 33 F1", timeout=2.0)
    resp = send_cmd(ser, "0100", timeout=10.0)
    first = resp.split("\n")[0] if resp else "NO DATA"
    logger.info(f"  応答: {first}")
    time.sleep(0.3)


def probe_ecu(ser: serial.Serial, addr: int) -> dict | None:
    """複数コマンドで ECU をプローブする."""
    addr_hex = f"{addr:02X}"
    send_cmd(ser, f"ATSH DA {addr_hex} F1", timeout=2.0)

    for cmd, desc in PROBE_COMMANDS:
        resp, pending = send_command(ser, cmd, timeout=3.0)
        if is_positive(resp):
            name = KNOWN_ECU_NAMES.get(addr, f"Unknown_0x{addr_hex}")
            return {
                "address": addr,
                "address_hex": addr_hex,
                "name": name,
                "detected_by": desc,
                "response": resp.split("\n")[0],
                "pending_count": pending,
            }

    return None


def get_ecu_details(ser: serial.Serial, ecu: dict) -> None:
    """検出 ECU の詳細情報を取得する."""
    addr_hex = ecu["address_hex"]
    send_cmd(ser, f"ATSH DA {addr_hex} F1", timeout=2.0)

    tests = [
        ("3E00", "TesterPresent"),
        ("1001", "DiagSession Default"),
        ("1003", "DiagSession Extended"),
        ("22F186", "ActiveSession"),
        ("0100", "OBD-II PIDs"),
        ("1902FF", "ReadDTC"),
        ("22F190", "VIN"),
        ("22F194", "Supplier SW No"),
        ("22F195", "Supplier SW Ver"),
    ]

    details: dict[str, str] = {}
    for cmd, desc in tests:
        resp = send_cmd(ser, cmd, timeout=5.0)
        if is_positive(resp):
            first = resp.split("\n")[0]
            if "7F" in first.upper().split():
                details[desc] = f"NRC: {first}"
            else:
                details[desc] = first

    ecu["details"] = details


def scan_with_protocol(
    ser: serial.Serial,
    protocol_cmd: str,
    protocol_desc: str,
    already_found: set[int],
) -> list[dict]:
    """指定プロトコルで全 PA スキャンを実行する."""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"スキャン: {protocol_desc}")
    logger.info("=" * 60)

    resp = send_cmd(ser, protocol_cmd)
    logger.info(f"{protocol_cmd} -> {resp}")

    resp = send_cmd(ser, "ATCP18")
    logger.info(f"ATCP18 -> {resp}")

    resp = send_cmd(ser, "ATSTFF")
    logger.info(f"ATSTFF -> {resp}")

    warmup(ser)

    detected: list[dict] = []
    scan_start = time.time()
    total = 255

    for i, addr in enumerate(range(0x01, 0x100)):
        if addr in already_found:
            continue

        if i % 16 == 0:
            elapsed = time.time() - scan_start
            scanned = max(i, 1)
            remaining = (elapsed / scanned) * (total - i)
            logger.info(
                f"  0x{addr:02X}~ ({i}/{total}, "
                f"検出: {len(detected)}, "
                f"残り約: {remaining / 60:.1f}分)"
            )

        result = probe_ecu(ser, addr)
        if result is not None:
            result["protocol"] = protocol_desc
            detected.append(result)
            logger.info(
                f"  ★ 0x{result['address_hex']} ({result['name']}) "
                f"by {result['detected_by']}: {result['response']}"
            )

    elapsed = time.time() - scan_start
    logger.info(f"  完了 ({elapsed:.0f}秒, 検出: {len(detected)})")

    return detected


def main() -> None:
    """メインエントリーポイント."""
    if len(sys.argv) < 2:
        print("Usage: python poc/can29bit_full_scan_v3.py <COM_PORT>")
        sys.exit(1)

    port = sys.argv[1]
    logger.info(f"PoC v3: 全 PA スキャン (F186 + 250k 対応) on {port}")

    try:
        ser = serial.Serial(port=port, baudrate=38400, timeout=10.0, write_timeout=5.0)
    except serial.SerialException as exc:
        logger.error(f"シリアルポートを開けません: {exc}")
        sys.exit(1)

    all_detected: list[dict] = []
    found_addrs: set[int] = set()
    total_start = time.time()

    try:
        logger.info("=== ELM327 初期化 ===")
        send_cmd(ser, "ATZ", timeout=5.0)
        send_cmd(ser, "ATE0")
        send_cmd(ser, "ATL0")
        send_cmd(ser, "ATH1")
        send_cmd(ser, "ATS1")
        send_cmd(ser, "ATCAF1")
        logger.info("初期化完了")

        # 500kbps (ATSP7) のみ
        ecus = scan_with_protocol(
            ser, "ATSP7", "29bit CAN 500kbps", found_addrs,
        )
        all_detected.extend(ecus)
        found_addrs.update(e["address"] for e in ecus)

        # Phase 3: 検出 ECU の詳細取得
        if all_detected:
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"詳細情報取得 ({len(all_detected)} ECU)")
            logger.info("=" * 60)

            # 詳細取得前にプロトコルを元に戻す
            for ecu in all_detected:
                proto = "ATSP7" if "500" in ecu["protocol"] else "ATSP8"
                send_cmd(ser, proto)
                send_cmd(ser, "ATCP18")
                send_cmd(ser, "ATSTFF")
                warmup(ser)

                logger.info(f"")
                logger.info(
                    f"--- 0x{ecu['address_hex']} ({ecu['name']}) "
                    f"[{ecu['protocol']}] ---"
                )
                get_ecu_details(ser, ecu)
                for svc, resp in ecu.get("details", {}).items():
                    logger.info(f"  {svc}: {resp}")

        # サマリー
        total_elapsed = time.time() - total_start
        logger.info("")
        logger.info("=" * 60)
        logger.info(
            f"全スキャン完了 "
            f"({total_elapsed:.0f}秒 = {total_elapsed / 60:.1f}分)"
        )
        logger.info("=" * 60)
        logger.info(f"検出 ECU 総数: {len(all_detected)}")
        logger.info("")

        if all_detected:
            logger.info(
                f"{'Addr':<8} {'Name':<25} {'Protocol':<20} "
                f"{'Detected by':<22} {'Services'}"
            )
            logger.info("-" * 110)
            for ecu in sorted(all_detected, key=lambda e: e["address"]):
                services = ", ".join(
                    k
                    for k, v in ecu.get("details", {}).items()
                    if not v.startswith("NRC")
                )
                if not services:
                    services = ecu["detected_by"]
                logger.info(
                    f"0x{ecu['address_hex']:<6} "
                    f"{ecu['name']:<25} "
                    f"{ecu['protocol']:<20} "
                    f"{ecu['detected_by']:<22} "
                    f"{services}"
                )

    except KeyboardInterrupt:
        elapsed = time.time() - total_start
        logger.info(f"\n中断 ({elapsed:.0f}秒)")
        logger.info(f"検出: {len(all_detected)} 個")
        for ecu in all_detected:
            logger.info(
                f"  0x{ecu['address_hex']} ({ecu['name']}) "
                f"[{ecu['protocol']}]"
            )
    except Exception as exc:
        logger.error(f"エラー: {exc}", exc_info=True)
    finally:
        ser.close()
        logger.info("シリアルポートを閉じました")


if __name__ == "__main__":
    main()
