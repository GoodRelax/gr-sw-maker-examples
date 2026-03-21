"""PoC: 29bit CAN 全 PA スキャン (0x01-0xFF) v2.

v1 からの改善:
  - ATSTFF (1020ms) でタイムアウト最大化
  - NRC 0x78 (Response Pending) ハンドリング追加
  - 検出 ECU には追加サービス確認
  - 経過時間と残り時間の推定表示

使い方:
  python poc/can29bit_full_scan_v2.py COM3
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
    0x06: "Seat Module",
    0x07: "Instrument Cluster",
    0x08: "Steering",
    0x09: "Airbag/SRS",
    0x0A: "Door (Driver)",
    0x0B: "Door (Passenger)",
    0x0E: "Engine (OBD-II)",
    0x10: "Engine #2",
    0x11: "Engine (alt)",
    0x18: "Transmission #2",
    0x20: "Hybrid/EV",
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
    0x78: "Power Steering (EPS)",
    0x7E: "Gateway #2",
}

_MAX_PENDING_RETRIES = 3
_P2_STAR_EXTENSION_S = 5.0


def _contains_response_pending(data: bytes) -> bool:
    """NRC 0x78 (Response Pending) を検出する."""
    text = data.decode("ascii", errors="replace").upper()
    tokens = text.replace("\r", " ").replace("\n", " ").split()
    for i in range(len(tokens) - 2):
        if tokens[i] == "7F" and tokens[i + 2] == "78":
            return True
    return False


def send_command(ser: serial.Serial, command: str, timeout: float = 5.0) -> str:
    """ELM327 にコマンドを送信し応答を返す（NRC 0x78 対応）."""
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
    """send_command のラッパー（pending_count 不要な場合用）."""
    resp, _ = send_command(ser, command, timeout)
    return resp


def init_elm327(ser: serial.Serial) -> None:
    """ELM327 を初期化する."""
    logger.info("=== ELM327 初期化 ===")
    send_cmd(ser, "ATZ", timeout=5.0)
    send_cmd(ser, "ATE0")
    send_cmd(ser, "ATL0")
    send_cmd(ser, "ATH1")
    send_cmd(ser, "ATS1")
    send_cmd(ser, "ATCAF1")

    resp = send_cmd(ser, "ATSP7")
    logger.info(f"ATSP7 (29bit CAN 500k) -> {resp}")

    resp = send_cmd(ser, "ATCP18")
    logger.info(f"ATCP18 -> {resp}")

    resp = send_cmd(ser, "ATSTFF")
    logger.info(f"ATSTFF (timeout 1020ms) -> {resp}")

    logger.info("初期化完了")


def is_positive_response(resp: str) -> bool:
    """NO DATA / ERROR / ? でないか判定."""
    upper = resp.upper()
    return bool(
        resp.strip()
        and "NO DATA" not in upper
        and "ERROR" not in upper
        and "?" not in resp
    )


def probe_ecu(ser: serial.Serial, addr: int) -> dict | None:
    """指定アドレスの ECU を TesterPresent でプローブする."""
    addr_hex = f"{addr:02X}"

    send_cmd(ser, f"ATSH DA {addr_hex} F1", timeout=2.0)
    resp, pending = send_command(ser, "3E00", timeout=3.0)

    if not is_positive_response(resp):
        return None

    name = KNOWN_ECU_NAMES.get(addr, f"Unknown_0x{addr_hex}")

    return {
        "address": addr,
        "address_hex": addr_hex,
        "name": name,
        "tester_present": resp.split("\n")[0],
        "response_pending_count": pending,
    }


def get_ecu_details(ser: serial.Serial, ecu: dict) -> dict:
    """検出 ECU の詳細サービス対応を確認する."""
    addr_hex = ecu["address_hex"]
    details: dict[str, str] = {}

    send_cmd(ser, f"ATSH DA {addr_hex} F1", timeout=2.0)

    tests = [
        ("1001", "DiagSession Default"),
        ("1003", "DiagSession Extended"),
        ("0100", "OBD-II PIDs"),
        ("1902FF", "ReadDTC"),
        ("22F190", "VIN"),
    ]

    for cmd, desc in tests:
        resp = send_cmd(ser, cmd, timeout=5.0)
        if is_positive_response(resp):
            first_line = resp.split("\n")[0]
            # NRC かどうか判定
            if "7F" in first_line.upper().split():
                details[desc] = f"NRC: {first_line}"
            else:
                details[desc] = first_line

    ecu["details"] = details
    return ecu


def main() -> None:
    """メインエントリーポイント."""
    if len(sys.argv) < 2:
        print("Usage: python poc/can29bit_full_scan_v2.py <COM_PORT>")
        sys.exit(1)

    port = sys.argv[1]
    logger.info(f"PoC v2: 全 PA スキャン (0x01-0xFF) on {port}")

    try:
        ser = serial.Serial(port=port, baudrate=38400, timeout=10.0, write_timeout=5.0)
    except serial.SerialException as exc:
        logger.error(f"シリアルポートを開けません: {exc}")
        sys.exit(1)

    detected: list[dict] = []
    scan_start = time.time()
    total = 255  # 0x01 - 0xFF

    try:
        init_elm327(ser)

        # ウォームアップ: CAN バス接続を確立する
        logger.info("CAN バス ウォームアップ中...")
        send_cmd(ser, "ATSH DB 33 F1", timeout=2.0)
        warmup_resp = send_cmd(ser, "0100", timeout=10.0)
        logger.info(f"ウォームアップ応答: {warmup_resp.split(chr(10))[0] if warmup_resp else 'NO DATA'}")
        # ヘッダを戻す（次のスキャンで個別設定するため）
        time.sleep(0.3)

        logger.info("")
        logger.info("=" * 60)
        logger.info("全 PA スキャン開始 (0x01 - 0xFF)")
        logger.info("=" * 60)
        logger.info("")

        for i, addr in enumerate(range(0x01, 0x100)):
            # 進捗表示（16 アドレスごと）
            if i % 16 == 0:
                elapsed = time.time() - scan_start
                if i > 0:
                    per_addr = elapsed / i
                    remaining = per_addr * (total - i)
                    eta_min = remaining / 60
                    logger.info(
                        f"スキャン中: 0x{addr:02X}-0x{min(addr + 15, 0xFF):02X} "
                        f"({i}/{total}, 検出: {len(detected)}, "
                        f"経過: {elapsed:.0f}s, 残り約: {eta_min:.1f}分)"
                    )
                else:
                    logger.info(
                        f"スキャン中: 0x{addr:02X}-0x{min(addr + 15, 0xFF):02X} "
                        f"({i}/{total})"
                    )

            result = probe_ecu(ser, addr)
            if result is not None:
                detected.append(result)
                pending_info = ""
                if result["response_pending_count"] > 0:
                    pending_info = (
                        f" (NRC 0x78 x{result['response_pending_count']})"
                    )
                logger.info(
                    f"  ★ ECU 検出! 0x{result['address_hex']} "
                    f"({result['name']}){pending_info}"
                )
                logger.info(
                    f"    TesterPresent: {result['tester_present']}"
                )

        scan_duration = time.time() - scan_start

        # 検出 ECU の詳細取得
        if detected:
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"詳細情報取得 ({len(detected)} ECU)")
            logger.info("=" * 60)

            for ecu in detected:
                logger.info(f"")
                logger.info(f"--- 0x{ecu['address_hex']} ({ecu['name']}) ---")
                get_ecu_details(ser, ecu)
                for svc, resp in ecu.get("details", {}).items():
                    logger.info(f"  {svc}: {resp}")

        # サマリー
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"スキャン完了 ({scan_duration:.0f}秒 = {scan_duration / 60:.1f}分)")
        logger.info("=" * 60)
        logger.info(f"検出 ECU 総数: {len(detected)}")
        logger.info("")

        if detected:
            logger.info(
                f"{'Addr':<8} {'Name':<25} {'TesterPresent':<35} {'Services'}"
            )
            logger.info("-" * 100)
            for ecu in detected:
                services = ", ".join(
                    k
                    for k, v in ecu.get("details", {}).items()
                    if not v.startswith("NRC")
                )
                if not services:
                    services = "TesterPresent only"
                logger.info(
                    f"0x{ecu['address_hex']:<6} "
                    f"{ecu['name']:<25} "
                    f"{ecu['tester_present']:<35} "
                    f"{services}"
                )
        else:
            logger.warning("ECU が検出されませんでした")

    except KeyboardInterrupt:
        elapsed = time.time() - scan_start
        logger.info(f"\n中断 ({elapsed:.0f}秒)")
        logger.info(f"検出: {len(detected)} 個")
        for ecu in detected:
            logger.info(f"  0x{ecu['address_hex']} ({ecu['name']})")
    except Exception as exc:
        logger.error(f"エラー: {exc}", exc_info=True)
    finally:
        ser.close()
        logger.info("シリアルポートを閉じました")


if __name__ == "__main__":
    main()
