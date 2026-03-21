"""全 PA スキャン (0x00-0xFF): TesterPresent + DiagSessionControl でゆっくり確実に.

ウォームアップ済み、プロンプト待ち、NRC 0x78 対応、長めタイムアウト。

使い方:
  python poc/can29bit_slow_full_scan.py COM3
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


def send_and_read(ser: serial.Serial, cmd: str, timeout: float = 5.0) -> str:
    """コマンドを送信し、プロンプト '>' まで確実に読む.

    NRC 0x78 (Response Pending) を検出したら +5 秒延長。
    """
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r".encode("ascii"))
    time.sleep(0.05)

    end_time = time.time() + timeout
    response = b""
    pending_count = 0

    while time.time() < end_time:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            response += chunk

            # NRC 0x78 検出
            text = chunk.decode("ascii", errors="replace").upper()
            tokens = text.replace("\r", " ").replace("\n", " ").split()
            for i in range(len(tokens) - 2):
                if tokens[i] == "7F" and tokens[i + 2] == "78":
                    if pending_count < 3:
                        pending_count += 1
                        end_time = time.time() + 5.0

            if b">" in response:
                break
        time.sleep(0.03)

    # プロンプト後の残りデータを読む
    time.sleep(0.2)
    while ser.in_waiting:
        response += ser.read(ser.in_waiting)
        time.sleep(0.1)

    decoded = response.decode("ascii", errors="replace")
    lines = decoded.replace("\r", "\n").split("\n")
    clean = [
        l.strip() for l in lines
        if l.strip() and l.strip() != ">" and l.strip() != cmd
        and "SEARCHING" not in l.upper()
    ]
    return "\n".join(clean)


def is_positive(resp: str) -> bool:
    """有効な応答か判定."""
    upper = resp.upper()
    return bool(
        resp.strip()
        and "NO DATA" not in upper
        and "ERROR" not in upper
        and "?" not in resp
    )


def main() -> None:
    """メインエントリーポイント."""
    if len(sys.argv) < 2:
        print("Usage: python poc/can29bit_slow_full_scan.py <COM_PORT>")
        sys.exit(1)

    port = sys.argv[1]
    logger.info(f"全 PA スキャン (slow) on {port}")

    ser = serial.Serial(port=port, baudrate=38400, timeout=5.0, write_timeout=5.0)

    detected: list[dict] = []
    scan_start = time.time()

    try:
        # 初期化
        logger.info("初期化中...")
        for cmd in ["ATZ", "ATE0", "ATH1", "ATS1", "ATSP7", "ATCP18", "ATSTFF"]:
            send_and_read(ser, cmd, timeout=3.0)

        # ウォームアップ
        logger.info("ウォームアップ中...")
        send_and_read(ser, "ATSH DB 33 F1", timeout=2.0)
        resp = send_and_read(ser, "0100", timeout=10.0)
        first = resp.split("\n")[0] if resp else "NO DATA"
        logger.info(f"  0100: {first}")
        time.sleep(0.5)

        # スキャン開始
        total = 256  # 0x00-0xFF
        logger.info("")
        logger.info("=" * 60)
        logger.info("全 PA スキャン開始 (0x00 - 0xFF) — ゆっくりモード")
        logger.info("  プローブ: 3E00 → 失敗なら 1001")
        logger.info("  タイムアウト: 各 5 秒")
        logger.info(f"  推定時間: 約 {total * 5 / 60:.0f}〜{total * 10 / 60:.0f} 分")
        logger.info("=" * 60)
        logger.info("")

        for addr in range(0x00, 0x100):
            addr_hex = f"{addr:02X}"

            # 進捗表示（16 アドレスごと）
            if addr % 16 == 0:
                elapsed = time.time() - scan_start
                if addr > 0:
                    per_addr = elapsed / addr
                    remaining = per_addr * (total - addr)
                    logger.info(
                        f"--- 0x{addr:02X}~ "
                        f"({addr}/{total}, 検出: {len(detected)}, "
                        f"経過: {elapsed:.0f}s, 残り約: {remaining / 60:.1f}分) ---"
                    )
                else:
                    logger.info(f"--- 0x{addr:02X}~ ({addr}/{total}) ---")

            # ヘッダ設定
            send_and_read(ser, f"ATSH DA {addr_hex} F1", timeout=2.0)
            time.sleep(0.1)

            # プローブ 1: TesterPresent (3E00)
            resp = send_and_read(ser, "3E00", timeout=5.0)

            if is_positive(resp):
                name = KNOWN_ECU_NAMES.get(addr, f"Unknown_0x{addr_hex}")
                detected.append({
                    "addr": addr,
                    "hex": addr_hex,
                    "name": name,
                    "method": "TesterPresent",
                    "response": resp.split("\n")[0],
                })
                logger.info(
                    f"  ★ 0x{addr_hex} ({name}) "
                    f"[3E00]: {resp.split(chr(10))[0]}"
                )
                continue

            # プローブ 2: DiagSessionControl Default (1001)
            time.sleep(0.1)
            resp = send_and_read(ser, "1001", timeout=5.0)

            if is_positive(resp):
                name = KNOWN_ECU_NAMES.get(addr, f"Unknown_0x{addr_hex}")
                detected.append({
                    "addr": addr,
                    "hex": addr_hex,
                    "name": name,
                    "method": "DiagSession",
                    "response": resp.split("\n")[0],
                })
                logger.info(
                    f"  ★ 0x{addr_hex} ({name}) "
                    f"[1001]: {resp.split(chr(10))[0]}"
                )

        scan_duration = time.time() - scan_start

        # サマリー
        logger.info("")
        logger.info("=" * 60)
        logger.info(
            f"スキャン完了 "
            f"({scan_duration:.0f}秒 = {scan_duration / 60:.1f}分)"
        )
        logger.info("=" * 60)
        logger.info(f"検出 ECU 総数: {len(detected)}")
        logger.info("")

        if detected:
            logger.info(f"{'Addr':<8} {'Name':<28} {'Method':<18} {'Response'}")
            logger.info("-" * 90)
            for ecu in detected:
                logger.info(
                    f"0x{ecu['hex']:<6} "
                    f"{ecu['name']:<28} "
                    f"{ecu['method']:<18} "
                    f"{ecu['response']}"
                )
        else:
            logger.warning("ECU が検出されませんでした")

    except KeyboardInterrupt:
        elapsed = time.time() - scan_start
        logger.info(f"\n中断 ({elapsed:.0f}秒)")
        logger.info(f"検出: {len(detected)} 個")
        for ecu in detected:
            logger.info(f"  0x{ecu['hex']} ({ecu['name']}) [{ecu['method']}]")
    except Exception as exc:
        logger.error(f"エラー: {exc}", exc_info=True)
    finally:
        ser.close()
        logger.info("シリアルポートを閉じました")


if __name__ == "__main__":
    main()
