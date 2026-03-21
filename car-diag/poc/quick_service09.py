"""Service $09 の情報を正しくマルチフレーム受信する.

使い方: python poc/quick_service09.py COM3
"""

import serial
import sys
import time

port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
s = serial.Serial(port, 38400, timeout=2, write_timeout=5)


def flush():
    """バッファを読み捨てる."""
    time.sleep(0.5)
    while s.in_waiting:
        s.read(s.in_waiting)
        time.sleep(0.1)


def send_and_read(cmd: str, wait: float = 8.0) -> str:
    """コマンドを送信し、プロンプト '>' まで確実に読む."""
    s.reset_input_buffer()
    s.write(f"{cmd}\r".encode("ascii"))

    response = b""
    end_time = time.time() + wait
    while time.time() < end_time:
        if s.in_waiting > 0:
            response += s.read(s.in_waiting)
            if b">" in response:
                break
        time.sleep(0.05)

    # プロンプト後にまだデータが来る場合（マルチフレーム）
    time.sleep(0.5)
    while s.in_waiting:
        response += s.read(s.in_waiting)
        time.sleep(0.2)

    decoded = response.decode("ascii", errors="replace")
    # エコーとプロンプトを除去
    lines = decoded.replace("\r", "\n").split("\n")
    clean = [
        l.strip() for l in lines
        if l.strip() and l.strip() != ">" and l.strip() != cmd
        and "SEARCHING" not in l.upper()
    ]
    return "\n".join(clean)


# 初期化
print("初期化中...")
for cmd in ["ATZ", "ATE0", "ATH1", "ATS1", "ATSP7", "ATCP18", "ATSTFF"]:
    s.write(f"{cmd}\r".encode())
    flush()

s.write(b"ATSH DB 33 F1\r")
flush()

# ウォームアップ
print("ウォームアップ中...")
resp = send_and_read("0100", wait=10.0)
print(f"  0100: {resp.split(chr(10))[0]}")

# Service $09 PID $00: 対応 PID 一覧
print("\n=== 0900: Service 09 Supported PIDs ===")
resp = send_and_read("0900", wait=5.0)
print(resp)

# Service $09 PID $04: Calibration ID
print("\n=== 0904: Calibration ID ===")
resp = send_and_read("0904", wait=8.0)
print(resp)

# Service $09 PID $06: CVN
print("\n=== 0906: Calibration Verification Number ===")
resp = send_and_read("0906", wait=8.0)
print(resp)

# Service $09 PID $0A: ECU Name
print("\n=== 090A: ECU Name ===")
resp = send_and_read("090A", wait=10.0)
print(resp)

# ECU Name を ASCII デコード
print("\n--- ECU Name デコード ---")
for line in resp.split("\n"):
    tokens = line.strip().upper().split()
    if len(tokens) >= 5 and tokens[0] == "18" and tokens[1] == "DA":
        # ヘッダ(4) + DL(1) + SID(1) + PID(1) + データ
        # またはマルチフレームのデータ部
        # First Frame: 18 DA F1 xx 10 LL 49 0A count ...
        # Consecutive: 18 DA F1 xx 2N data...
        src = tokens[3]
        frame_type = tokens[4]

        if frame_type.startswith("1"):
            # First Frame — データは tokens[7:] から
            data_tokens = tokens[7:]
        elif frame_type.startswith("2"):
            # Consecutive Frame — データは tokens[5:] から
            data_tokens = tokens[5:]
        else:
            # Single Frame — DL SID PID count data...
            data_tokens = tokens[7:]

        ascii_chars = []
        for t in data_tokens:
            if t == "55":  # パディング
                continue
            try:
                val = int(t, 16)
                if 0x20 <= val <= 0x7E:
                    ascii_chars.append(chr(val))
                elif val == 0x00:
                    ascii_chars.append("")
                else:
                    ascii_chars.append(f"[{t}]")
            except ValueError:
                pass

        if ascii_chars:
            print(f"  ECU 0x{src}: {''.join(ascii_chars)}")

# おまけ: ファンクショナル TesterPresent
print("\n=== 3E00: TesterPresent ===")
resp = send_and_read("3E00", wait=5.0)
print(resp)

# おまけ: Service $09 PID $02 (VIN) — 対応していないかもだが一応
print("\n=== 0902: VIN ===")
resp = send_and_read("0902", wait=8.0)
print(resp)

s.close()
print("\n完了")
