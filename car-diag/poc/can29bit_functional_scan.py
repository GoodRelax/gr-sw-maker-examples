"""PoC: 18DB (ファンクショナルアドレス) で全 ECU を一斉検出する.

18DA (物理) だと 1 アドレスずつ試す必要があるが、
18DB (ファンクショナル) なら 1 コマンドで全 ECU が応答する可能性がある。

検証:
  1. 18 DB 33 F1 + TesterPresent (3E00) — UDS 対応 ECU 全検出
  2. 18 DB 33 F1 + ReadDTCByStatusMask (1902FF) — DTC 対応 ECU 全検出
  3. 18 DB 33 F1 + DiagnosticSessionControl (1001) — 全 ECU のセッション確認
  4. ATMA (Monitor All) で CAN バス上のトラフィックを観察

使い方:
  python poc/can29bit_functional_scan.py COM3
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
    0x0E: "Engine (OBD-II)",
    0x30: "Air Suspension / EPS",
    0x60: "Headlamp / Body",
}


def send_command(ser: serial.Serial, command: str, timeout: float = 3.0) -> str:
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


def send_command_multi(ser: serial.Serial, command: str, timeout: float = 5.0) -> str:
    """複数 ECU からの応答を待つ（長めのタイムアウト）.

    ELM327 は最初の応答で > を返すことがある。
    ATCAF0 + ATAR でフィルタを外して複数応答を取得試行。
    """
    ser.reset_input_buffer()
    ser.write(f"{command}\r".encode("ascii"))
    time.sleep(0.1)

    end_time = time.time() + timeout
    response = b""
    prompt_count = 0
    while time.time() < end_time:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            response += chunk
            if b">" in chunk:
                prompt_count += 1
                # 最初のプロンプトから少し待って追加応答があるか確認
                if prompt_count >= 1:
                    time.sleep(0.5)
                    if ser.in_waiting > 0:
                        response += ser.read(ser.in_waiting)
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
    return "\n".join(result_lines)


def extract_source_addresses(response: str) -> list[dict[str, str]]:
    """応答文字列から 29bit CAN ソースアドレスを抽出する.

    応答フォーマット: 18 DA F1 {src} ...
    """
    seen: dict[str, str] = {}
    for line in response.split("\n"):
        tokens = line.strip().upper().split()
        if len(tokens) >= 4 and tokens[0] == "18" and tokens[1] == "DA" and tokens[2] == "F1":
            src_addr = tokens[3]
            if src_addr not in seen:
                seen[src_addr] = line.strip()
    return [{"addr": addr, "first_response": resp} for addr, resp in seen.items()]


def init_elm327(ser: serial.Serial) -> None:
    """ELM327 を初期化する."""
    logger.info("=== ELM327 初期化 ===")
    send_command(ser, "ATZ", timeout=5.0)
    send_command(ser, "ATE0")
    send_command(ser, "ATL0")
    send_command(ser, "ATH1")
    send_command(ser, "ATS1")
    resp = send_command(ser, "ATSP7")
    logger.info(f"ATSP7 -> {resp}")
    resp = send_command(ser, "ATCP18")
    logger.info(f"ATCP18 -> {resp}")
    # タイムアウトをデフォルト (ATSTFF = 1020ms) に戻す
    send_command(ser, "ATSTFF")
    logger.info("初期化完了")


def test_functional(ser: serial.Serial, cmd: str, desc: str) -> list[dict[str, str]]:
    """ファンクショナルアドレスでコマンドを送信し、応答した ECU を列挙."""
    logger.info(f"")
    logger.info(f"--- {desc} ---")
    logger.info(f"送信: ATSH DB 33 F1 + {cmd}")

    send_command(ser, "ATSH DB 33 F1")

    # ATCAF0 で auto formatting OFF → 生の CAN フレームを取得
    send_command(ser, "ATCAF0")

    resp = send_command_multi(ser, cmd, timeout=5.0)

    # ATCAF1 に戻す
    send_command(ser, "ATCAF1")

    logger.info(f"応答:")
    for line in resp.split("\n"):
        if line.strip():
            logger.info(f"  {line.strip()}")

    if "NO DATA" in resp.upper():
        logger.info("  応答なし")
        return []

    ecus = extract_source_addresses(resp)
    logger.info(f"検出 ECU: {len(ecus)} 個")
    for ecu in ecus:
        addr_int = int(ecu["addr"], 16)
        name = KNOWN_ECU_NAMES.get(addr_int, f"Unknown")
        logger.info(f"  0x{ecu['addr']} ({name})")

    return ecus


def test_functional_with_caf1(ser: serial.Serial, cmd: str, desc: str) -> list[dict[str, str]]:
    """ATCAF1 (auto formatting ON) でファンクショナル送信.

    ELM327 がフォーマット済みの応答を返す。
    """
    logger.info(f"")
    logger.info(f"--- {desc} (ATCAF1) ---")
    logger.info(f"送信: ATSH DB 33 F1 + {cmd}")

    send_command(ser, "ATSH DB 33 F1")
    send_command(ser, "ATCAF1")

    resp = send_command_multi(ser, cmd, timeout=5.0)

    logger.info(f"応答:")
    for line in resp.split("\n"):
        if line.strip():
            logger.info(f"  {line.strip()}")

    if "NO DATA" in resp.upper():
        logger.info("  応答なし")
        return []

    ecus = extract_source_addresses(resp)
    logger.info(f"検出 ECU: {len(ecus)} 個")
    for ecu in ecus:
        addr_int = int(ecu["addr"], 16)
        name = KNOWN_ECU_NAMES.get(addr_int, f"Unknown")
        logger.info(f"  0x{ecu['addr']} ({name})")

    return ecus


def test_physical_verification(ser: serial.Serial, addresses: list[str]) -> None:
    """検出されたアドレスに物理アドレスで再確認."""
    logger.info("")
    logger.info("=== 物理アドレスで再確認 ===")

    send_command(ser, "ATCAF1")

    for addr_hex in addresses:
        logger.info(f"")
        logger.info(f"--- 0x{addr_hex} ---")

        send_command(ser, f"ATSH DA {addr_hex} F1")

        commands = [
            ("3E00", "TesterPresent"),
            ("1001", "DiagSessionControl (default)"),
            ("1902FF", "ReadDTCByStatusMask"),
            ("22F190", "ReadDataById (VIN)"),
            ("22F18C", "ReadDataById (ECU Serial)"),
        ]

        for cmd, desc in commands:
            resp = send_command(ser, cmd, timeout=2.0)
            is_ok = "NO DATA" not in resp.upper() and "ERROR" not in resp.upper()
            marker = "✓" if is_ok else "✗"
            # 長い応答は最初の行だけ表示
            first_line = resp.split("\n")[0] if resp else "(empty)"
            logger.info(f"  {marker} {desc}: {first_line}")


def main() -> None:
    """メインエントリーポイント."""
    if len(sys.argv) < 2:
        print("Usage: python poc/can29bit_functional_scan.py <COM_PORT>")
        sys.exit(1)

    port = sys.argv[1]
    logger.info(f"PoC: ファンクショナルアドレス (18DB) スキャン on {port}")

    try:
        ser = serial.Serial(port=port, baudrate=38400, timeout=5.0, write_timeout=5.0)
    except serial.SerialException as exc:
        logger.error(f"シリアルポートを開けません: {exc}")
        sys.exit(1)

    all_detected: set[str] = set()

    try:
        init_elm327(ser)

        # テスト 1: 各種 UDS サービスでファンクショナルブロードキャスト
        tests = [
            ("3E00", "TesterPresent (3E 00)"),
            ("1001", "DiagSessionControl Default (10 01)"),
            ("1003", "DiagSessionControl Extended (10 03)"),
            ("1902FF", "ReadDTCByStatusMask (19 02 FF)"),
            ("0100", "OBD-II Supported PIDs (01 00)"),
            ("0902", "OBD-II VIN (09 02)"),
        ]

        for cmd, desc in tests:
            ecus = test_functional(ser, cmd, desc)
            for ecu in ecus:
                all_detected.add(ecu["addr"])

        # テスト 2: ATCAF1 でも同じテスト（フォーマット差異の確認）
        ecus = test_functional_with_caf1(ser, "3E00", "TesterPresent (CAF1)")
        for ecu in ecus:
            all_detected.add(ecu["addr"])

        # テスト 3: 検出された全アドレスに物理アドレスで詳細確認
        if all_detected:
            test_physical_verification(ser, sorted(all_detected))

        # サマリー
        logger.info("")
        logger.info("=" * 60)
        logger.info("=== 最終結果 ===")
        logger.info("=" * 60)
        logger.info(f"検出 ECU 総数: {len(all_detected)}")
        for addr in sorted(all_detected):
            addr_int = int(addr, 16)
            name = KNOWN_ECU_NAMES.get(addr_int, "Unknown")
            logger.info(f"  0x{addr} ({name})")

    except KeyboardInterrupt:
        logger.info("\n中断されました")
    except Exception as exc:
        logger.error(f"エラー: {exc}", exc_info=True)
    finally:
        ser.close()
        logger.info("シリアルポートを閉じました")


if __name__ == "__main__":
    main()
