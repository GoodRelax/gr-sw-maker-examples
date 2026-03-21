"""PoC: ELM327 クローン v1.5 で 29bit CAN アドレス指定が可能か検証する.

検証項目:
  1. ATCP + ATSH で 29bit CAN ヘッダを設定できるか
  2. 物理アドレス 18 DA xx F1 で個別 ECU にリクエストを送れるか
  3. ファンクショナルアドレス 18 DB 33 F1 でブロードキャストできるか
  4. UDS SID $22 (ReadDataByIdentifier) が応答するか
  5. UDS SID $19 (ReadDTCInformation) が応答するか

使い方:
  python poc/can29bit_probe.py COM3
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

# 検証対象の ECU アドレス (29bit CAN physical addressing)
# 18 DA {target} F1 — F1 = tester address
PROBE_TARGETS: list[dict[str, str]] = [
    {"addr": "0E", "name": "ECU_0E (detected engine)"},
    {"addr": "10", "name": "ECU_10 (common engine)"},
    {"addr": "18", "name": "ECU_18 (common transmission)"},
    {"addr": "28", "name": "ECU_28 (common ABS/VSC)"},
    {"addr": "40", "name": "ECU_40 (common body/BCM)"},
    {"addr": "47", "name": "ECU_47 (common window)"},
    {"addr": "7E", "name": "ECU_7E (common gateway)"},
]

# テストコマンド
TEST_COMMANDS: list[dict[str, str]] = [
    {"cmd": "3E00", "desc": "UDS TesterPresent"},
    {"cmd": "0100", "desc": "OBD-II Supported PIDs"},
    {"cmd": "1902FF", "desc": "UDS ReadDTCByStatusMask (all)"},
    {"cmd": "22F190", "desc": "UDS ReadDataById (VIN)"},
]


def send_command(ser: serial.Serial, command: str, timeout: float = 3.0) -> str:
    """ELM327 にコマンドを送信し、応答を返す."""
    ser.reset_input_buffer()
    ser.write(f"{command}\r".encode("ascii"))
    time.sleep(0.1)

    end_time = time.time() + timeout
    response = b""
    while time.time() < end_time:
        if ser.in_waiting > 0:
            response += ser.read(ser.in_waiting)
            if b">" in response:
                break
        time.sleep(0.05)

    decoded = response.decode("ascii", errors="replace").strip()
    # エコーを除去
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

    resp = send_command(ser, "ATZ", timeout=5.0)
    logger.info(f"ATZ -> {resp}")

    resp = send_command(ser, "ATE0")
    logger.info(f"ATE0 -> {resp}")

    resp = send_command(ser, "ATL0")
    logger.info(f"ATL0 -> {resp}")

    # ヘッダ表示 ON（応答ヘッダを見るため必須）
    resp = send_command(ser, "ATH1")
    logger.info(f"ATH1 -> {resp}")

    # スペース ON（読みやすさ）
    resp = send_command(ser, "ATS1")
    logger.info(f"ATS1 -> {resp}")

    # CAN 29bit プロトコルを明示指定
    # Protocol 7 = ISO 15765-4 CAN (29bit, 500kbaud)
    resp = send_command(ser, "ATSP7")
    logger.info(f"ATSP7 (29bit CAN 500k) -> {resp}")

    if "OK" not in resp.upper():
        # Protocol B = user CAN (29bit, 500k) を試す
        resp = send_command(ser, "ATSPB")
        logger.info(f"ATSPB (user CAN 29bit) -> {resp}")

    return True


def test_broadcast_functional(ser: serial.Serial) -> None:
    """ファンクショナルアドレス 18 DB 33 F1 でブロードキャストテスト."""
    logger.info("")
    logger.info("=== テスト 1: ファンクショナルアドレス (18 DB 33 F1) ===")

    # CAN Priority byte 設定
    resp = send_command(ser, "ATCP18")
    logger.info(f"ATCP18 -> {resp}")

    # ファンクショナルアドレスヘッダ設定
    resp = send_command(ser, "ATSH DB 33 F1")
    logger.info(f"ATSH DB 33 F1 -> {resp}")

    # OBD-II PID $0100 を送信
    resp = send_command(ser, "0100", timeout=5.0)
    logger.info(f"0100 (functional broadcast) -> {resp}")

    if "NO DATA" in resp.upper() or "ERROR" in resp.upper():
        logger.warning("ファンクショナルアドレスでの応答なし")
    else:
        logger.info("✓ ファンクショナルアドレスで応答あり！")
        for line in resp.split("\n"):
            if line.strip():
                logger.info(f"  応答: {line.strip()}")


def test_physical_addressing(ser: serial.Serial) -> None:
    """物理アドレス 18 DA xx F1 で個別 ECU にプローブ."""
    logger.info("")
    logger.info("=== テスト 2: 物理アドレス (18 DA xx F1) で個別 ECU プローブ ===")

    # CAN Priority byte 設定
    resp = send_command(ser, "ATCP18")
    logger.info(f"ATCP18 -> {resp}")

    for target in PROBE_TARGETS:
        addr = target["addr"]
        name = target["name"]
        logger.info(f"")
        logger.info(f"--- {name} (18 DA {addr} F1) ---")

        # 物理アドレスヘッダ設定
        resp = send_command(ser, f"ATSH DA {addr} F1")
        logger.info(f"ATSH DA {addr} F1 -> {resp}")

        if "OK" not in resp.upper():
            logger.warning(f"ヘッダ設定失敗: {resp}")
            continue

        # 各テストコマンドを送信
        for test in TEST_COMMANDS:
            resp = send_command(ser, test["cmd"], timeout=3.0)
            is_ok = (
                "NO DATA" not in resp.upper()
                and "ERROR" not in resp.upper()
                and "?" not in resp
                and resp.strip() != ""
            )
            marker = "✓" if is_ok else "✗"
            logger.info(f"  {marker} {test['desc']}: {resp}")


def test_atcra_filter(ser: serial.Serial) -> None:
    """ATCRA で受信フィルタを設定して応答を確認."""
    logger.info("")
    logger.info("=== テスト 3: ATCRA 受信フィルタテスト ===")

    # 受信フィルタを 18 DA F1 xx に設定（テスターへの応答のみ受信）
    resp = send_command(ser, "ATCRA 18 DA F1")
    logger.info(f"ATCRA 18 DA F1 -> {resp}")

    if "OK" not in resp.upper():
        # ATCRA が使えない場合
        logger.warning("ATCRA 非対応（クローンの制限の可能性）")
        return

    # ファンクショナルブロードキャスト
    resp = send_command(ser, "ATSH DB 33 F1")
    logger.info(f"ATSH DB 33 F1 -> {resp}")

    resp = send_command(ser, "0100", timeout=5.0)
    logger.info(f"0100 (with CRA filter) -> {resp}")

    for line in resp.split("\n"):
        if line.strip():
            logger.info(f"  応答: {line.strip()}")

    # フィルタ解除
    resp = send_command(ser, "ATAR")
    logger.info(f"ATAR (reset filter) -> {resp}")


def test_elm327_capabilities(ser: serial.Serial) -> None:
    """ELM327 の AT コマンド対応状況を確認."""
    logger.info("")
    logger.info("=== テスト 4: ELM327 AT コマンド対応状況 ===")

    at_commands = [
        ("ATDP", "現在のプロトコル表示"),
        ("ATDPN", "プロトコル番号表示"),
        ("ATCEA", "CAN Extended Address 対応確認"),
        ("ATCAF1", "CAN Auto Formatting ON"),
        ("ATCAF0", "CAN Auto Formatting OFF"),
    ]

    for cmd, desc in at_commands:
        resp = send_command(ser, cmd)
        logger.info(f"  {cmd} ({desc}) -> {resp}")

    # CAN Auto Formatting を元に戻す
    send_command(ser, "ATCAF1")


def main() -> None:
    """メインエントリーポイント."""
    if len(sys.argv) < 2:
        print("Usage: python poc/can29bit_probe.py <COM_PORT>")
        print("Example: python poc/can29bit_probe.py COM3")
        sys.exit(1)

    port = sys.argv[1]
    logger.info(f"PoC: 29bit CAN addressing test on {port}")

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

    try:
        init_elm327(ser)
        test_elm327_capabilities(ser)
        test_broadcast_functional(ser)
        test_physical_addressing(ser)
        test_atcra_filter(ser)

        logger.info("")
        logger.info("=== PoC 完了 ===")
        logger.info("結果を確認し、どのアドレッシング方式が使えるか判断してください。")

    except KeyboardInterrupt:
        logger.info("中断されました")
    except Exception as exc:
        logger.error(f"エラー: {exc}", exc_info=True)
    finally:
        ser.close()
        logger.info("シリアルポートを閉じました")


if __name__ == "__main__":
    main()
