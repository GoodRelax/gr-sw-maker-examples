"""エンジン OFF 状態でファンクショナル $22 F186 を送信する.

使い方: python poc/quick_f186.py COM3
事前にイグニッション ON・エンジン OFF にすること。
"""

import serial
import sys
import time

port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
s = serial.Serial(port, 38400, timeout=2, write_timeout=5)


def flush_read():
    """バッファを読み捨てる."""
    time.sleep(0.5)
    while s.in_waiting:
        s.read(s.in_waiting)
        time.sleep(0.1)


print("初期化中...")
for cmd in ["ATZ", "ATE0", "ATH1", "ATS1", "ATSP7", "ATCP18", "ATSTFF"]:
    s.write(f"{cmd}\r".encode())
    flush_read()

# ウォームアップ
s.write(b"ATSH DB 33 F1\r")
flush_read()

print("ウォームアップ中...")
s.reset_input_buffer()
s.write(b"0100\r")
time.sleep(5)
warmup = b""
while s.in_waiting:
    warmup += s.read(s.in_waiting)
    time.sleep(0.1)
print(f"Warmup (0100): {warmup.decode('ascii', errors='replace').strip()}")

# 本番: ファンクショナル $22 F186
print("\n=== Functional 22 F186 (ActiveDiagnosticSession) ===")
s.reset_input_buffer()
s.write(b"22F186\r")
time.sleep(8)
resp = b""
while s.in_waiting:
    resp += s.read(s.in_waiting)
    time.sleep(0.3)
print(resp.decode("ascii", errors="replace"))

# おまけ: ファンクショナル TesterPresent
print("\n=== Functional 3E00 (TesterPresent) ===")
s.reset_input_buffer()
s.write(b"3E00\r")
time.sleep(5)
resp = b""
while s.in_waiting:
    resp += s.read(s.in_waiting)
    time.sleep(0.3)
print(resp.decode("ascii", errors="replace"))

# おまけ: ファンクショナル $19 02 FF
print("\n=== Functional 1902FF (ReadDTCByStatusMask) ===")
s.reset_input_buffer()
s.write(b"1902FF\r")
time.sleep(8)
resp = b""
while s.in_waiting:
    resp += s.read(s.in_waiting)
    time.sleep(0.3)
print(resp.decode("ascii", errors="replace"))

# Service $09 PID $0A: ECU Name (全ECUが応答する可能性)
print("\n=== Functional 090A (ECU Name) ===")
s.reset_input_buffer()
s.write(b"090A\r")
time.sleep(8)
resp = b""
while s.in_waiting:
    resp += s.read(s.in_waiting)
    time.sleep(0.3)
print(resp.decode("ascii", errors="replace"))

# Service $09 PID $02: VIN
print("\n=== Functional 0902 (VIN) ===")
s.reset_input_buffer()
s.write(b"0902\r")
time.sleep(8)
resp = b""
while s.in_waiting:
    resp += s.read(s.in_waiting)
    time.sleep(0.3)
print(resp.decode("ascii", errors="replace"))

# Service $09 PID $00: Supported PIDs [01-20]
print("\n=== Functional 0900 (Supported Service 09 PIDs) ===")
s.reset_input_buffer()
s.write(b"0900\r")
time.sleep(5)
resp = b""
while s.in_waiting:
    resp += s.read(s.in_waiting)
    time.sleep(0.3)
print(resp.decode("ascii", errors="replace"))

s.close()
print("\n完了")
