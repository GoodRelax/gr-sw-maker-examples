"""PoC: 29bit CAN 物理アドレス 0x01-0xFF を全スキャンし、応答する ECU を列挙する.

検証済み前提:
  - ATCP18 + ATSH DA xx F1 で 29bit CAN 物理アドレス指定が可能
  - UDS TesterPresent (3E00) で ECU の存在を確認可能

使い方:
  python poc/can29bit_full_scan.py COM3
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

# 既知の ECU アドレス → 推定名マッピング（一般的な割当）
KNOWN_ECU_NAMES: dict[int, str] = {
    0x00: "Broadcast",
    0x01: "Engine #1",
    0x02: "Transmission #1",
    0x03: "ABS/ESC",
    0x04: "Body Control Module",
    0x05: "Climate Control",
    0x06: "Seat Module",
    0x07: "Instrument Cluster",
    0x08: "Steering",
    0x09: "Airbag/SRS",
    0x0A: "Door Module (Driver)",
    0x0B: "Door Module (Passenger)",
    0x0E: "Engine (detected)",
    0x10: "Engine #2",
    0x11: "Engine (alt)",
    0x18: "Transmission #2",
    0x20: "Hybrid/EV",
    0x28: "ABS/VSC (alt)",
    0x30: "Air Suspension",
    0x38: "Parking Assist",
    0x40: "Body/BCM (alt)",
    0x44: "Gateway",
    0x47: "Window Control",
    0x50: "Immobilizer",
    0x58: "TPMS",
    0x60: "Headlamp",
    0x68: "Audio/Infotainment",
    0x70: "Telematics",
    0x78: "Power Steering (EPS)",
    0x7E: "Gateway (alt)",
}


def send_command(ser: serial.Serial, command: str, timeout: float = 2.0) -> str:
    """ELM327 にコマンドを送信し、応答を返す."""
    ser.reset_input_buffer()
    ser.write(f"{command}\r".encode("ascii"))
    time.sleep(0.05)

    end_time = time.time() + timeout
    response = b""
    while time.time() < end_time:
        if ser.in_waiting > 0:
            response += ser.read(ser.in_waiting)
            if b">" in response:
                break
        time.sleep(0.03)

    decoded = response.decode("ascii", errors="replace").strip()
    lines = decoded.split("\r")
    result_lines = [
        line.strip()
        for line in lines
        if line.strip() and line.strip() != command and line.strip() != ">"
    ]
    return "\n".join(result_lines)


def init_elm327(ser: serial.Serial) -> bool:
    """ELM327 を初期化する."""
    logger.info("=== ELM327 初期化 ===")

    send_command(ser, "ATZ", timeout=5.0)
    send_command(ser, "ATE0")
    send_command(ser, "ATL0")
    send_command(ser, "ATH1")
    send_command(ser, "ATS1")

    resp = send_command(ser, "ATSP7")
    logger.info(f"ATSP7 (29bit CAN 500k) -> {resp}")

    resp = send_command(ser, "ATCP18")
    logger.info(f"ATCP18 -> {resp}")

    # タイムアウトを短めに設定（スキャン高速化）
    # ATST は 4ms 単位。FF = 1020ms, 40 = 256ms
    resp = send_command(ser, "ATSTC8")
    logger.info(f"ATSTC8 (timeout 800ms) -> {resp}")

    return True


def probe_ecu(ser: serial.Serial, addr: int) -> dict | None:
    """指定アドレスの ECU をプローブする.

    Returns:
        検出された場合は ECU 情報の辞書、未検出は None.
    """
    addr_hex = f"{addr:02X}"

    # ヘッダ設定
    resp = send_command(ser, f"ATSH DA {addr_hex} F1", timeout=1.0)
    if "OK" not in resp.upper():
        return None

    # TesterPresent (3E 00) で ECU 存在確認
    resp = send_command(ser, "3E00", timeout=1.5)

    if "NO DATA" in resp.upper() or "ERROR" in resp.upper() or "?" in resp:
        return None

    # 応答あり = ECU 検出
    ecu_name = KNOWN_ECU_NAMES.get(addr, f"Unknown (0x{addr_hex})")

    result = {
        "address": addr,
        "address_hex": addr_hex,
        "name": ecu_name,
        "tester_present_response": resp.strip(),
        "services": {},
    }

    # 追加情報を取得
    # OBD-II PID 対応確認
    resp = send_command(ser, "0100", timeout=1.5)
    if "NO DATA" not in resp.upper() and "ERROR" not in resp.upper():
        result["services"]["obd2_pids"] = resp.strip()

    # UDS ReadDTC
    resp = send_command(ser, "1902FF", timeout=2.0)
    if "NO DATA" not in resp.upper() and "ERROR" not in resp.upper():
        # レスポンスの行数でDTC数を推定
        dtc_lines = [l for l in resp.split("\n") if l.strip()]
        result["services"]["uds_read_dtc"] = f"{len(dtc_lines)} frames"

    # UDS ReadDataByIdentifier - ECU識別 (F18A = System Supplier ECU SW Number)
    resp = send_command(ser, "22F18A", timeout=1.5)
    if "NO DATA" not in resp.upper() and "ERROR" not in resp.upper():
        result["services"]["ecu_sw_number"] = resp.strip()

    # UDS ReadDataByIdentifier - ECU識別 (F187 = Spare Part Number)
    resp = send_command(ser, "22F187", timeout=1.5)
    if "NO DATA" not in resp.upper() and "ERROR" not in resp.upper():
        result["services"]["spare_part_number"] = resp.strip()

    return result


def main() -> None:
    """メインエントリーポイント."""
    if len(sys.argv) < 2:
        print("Usage: python poc/can29bit_full_scan.py <COM_PORT>")
        print("Example: python poc/can29bit_full_scan.py COM3")
        sys.exit(1)

    port = sys.argv[1]
    logger.info(f"PoC: 29bit CAN full address scan (0x01-0xFF) on {port}")

    try:
        ser = serial.Serial(
            port=port,
            baudrate=38400,
            timeout=5.0,
            write_timeout=5.0,
        )
    except serial.SerialException as exc:
        logger.error(f"シリアルポートを開けません: {exc}")
        sys.exit(1)

    detected_ecus: list[dict] = []
    scan_start = time.time()

    try:
        init_elm327(ser)

        logger.info("")
        logger.info("=== フルスキャン開始 (0x01 - 0xFF) ===")
        logger.info("")

        for addr in range(0x01, 0x100):
            # 進捗表示（16 アドレスごと）
            if addr % 16 == 1:
                elapsed = time.time() - scan_start
                logger.info(
                    f"スキャン中: 0x{addr:02X}-0x{min(addr + 15, 0xFF):02X} "
                    f"({addr - 1}/255, 検出: {len(detected_ecus)}, "
                    f"経過: {elapsed:.0f}s)"
                )

            result = probe_ecu(ser, addr)
            if result is not None:
                detected_ecus.append(result)
                logger.info(
                    f"  ★ ECU 検出! 0x{result['address_hex']} "
                    f"({result['name']})"
                )
                logger.info(
                    f"    TesterPresent: {result['tester_present_response']}"
                )
                for svc_name, svc_data in result["services"].items():
                    logger.info(f"    {svc_name}: {svc_data}")

        scan_duration = time.time() - scan_start

        # サマリー
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"=== スキャン完了 ({scan_duration:.0f}秒) ===")
        logger.info("=" * 60)
        logger.info(f"検出 ECU 数: {len(detected_ecus)}")
        logger.info("")

        if detected_ecus:
            logger.info(f"{'Addr':<8} {'Name':<30} {'Services'}")
            logger.info("-" * 70)
            for ecu in detected_ecus:
                services = ", ".join(ecu["services"].keys()) or "TesterPresent only"
                logger.info(
                    f"0x{ecu['address_hex']:<6} "
                    f"{ecu['name']:<30} "
                    f"{services}"
                )
        else:
            logger.warning("ECU が検出されませんでした")

    except KeyboardInterrupt:
        scan_duration = time.time() - scan_start
        logger.info(f"\n中断されました ({scan_duration:.0f}秒)")
        logger.info(f"ここまでの検出数: {len(detected_ecus)}")
        for ecu in detected_ecus:
            logger.info(f"  0x{ecu['address_hex']} ({ecu['name']})")
    except Exception as exc:
        logger.error(f"エラー: {exc}", exc_info=True)
    finally:
        ser.close()
        logger.info("シリアルポートを閉じました")


if __name__ == "__main__":
    main()
