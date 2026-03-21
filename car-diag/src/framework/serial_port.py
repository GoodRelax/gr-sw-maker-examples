"""PySerialPort: SerialPort Protocol の pyserial 実装.

pyserial ライブラリを使用した実際のシリアルポート通信を提供する。

traces: NFR-05a, HWR-01, HWR-02, HWR-22
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# タイムアウト秒数 (HW要求仕様 2.2)
_DEFAULT_TIMEOUT_S: float = 5.0

# ELM327 プロンプト文字
_ELM327_PROMPT: str = ">"


def list_available_ports() -> list[dict[str, str]]:
    """利用可能な COM ポートの一覧を返す.

    Returns:
        COM ポート情報の辞書リスト。各辞書には以下のキーを含む:
        - port_name: ポート名 (例: "COM3")
        - description: ポートの説明
        - hwid: ハードウェア ID

    traces: HWR-01, HWR-02
    """
    try:
        from serial.tools import list_ports

        ports: list[dict[str, str]] = []
        for port_info in list_ports.comports():
            ports.append({
                "port_name": port_info.device,
                "description": port_info.description or "",
                "hwid": port_info.hwid or "",
            })

        logger.info(
            "Available COM ports listed",
            extra={"port_count": len(ports)},
        )
        return ports

    except ImportError:
        logger.error("pyserial is not installed, cannot list ports")
        return []


class PySerialPort:
    """pyserial によるシリアルポート実装.

    SerialPort Protocol を満たす具体実装。Bluetooth SPP 経由の
    ELM327 通信に使用する。

    Attributes:
        _serial: pyserial の Serial インスタンス.
        _is_open: ポートが開いているか.
    """

    def __init__(self) -> None:
        """PySerialPort を初期化する."""
        self._serial: Any = None
        self._is_open: bool = False

    @property
    def is_open(self) -> bool:
        """ポートが開いているかを返す."""
        return self._is_open and self._serial is not None

    def open(
        self,
        port_name: str,
        baudrate: int = 38400,
        timeout: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        """シリアルポートを開く.

        Args:
            port_name: COM ポート名 (例: "COM3").
            baudrate: ボーレート (デフォルト: 38400).
            timeout: 読取タイムアウト秒数 (デフォルト: 5.0).

        Raises:
            ConnectionError: ポートが開けない場合.

        traces: HWR-22
        """
        try:
            import serial

            self._serial = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            self._is_open = True

            logger.info(
                "Serial port opened",
                extra={
                    "port_name": port_name,
                    "baudrate": baudrate,
                    "timeout": timeout,
                },
            )

        except ImportError:
            msg = "pyserial is not installed"
            logger.error(msg)
            raise ConnectionError(msg) from None

        except Exception as exc:
            msg = f"Failed to open serial port {port_name}: {exc}"
            logger.error(
                "Serial port open failed",
                extra={
                    "port_name": port_name,
                    "error": str(exc),
                },
            )
            raise ConnectionError(msg) from exc

    def close(self) -> None:
        """シリアルポートを閉じる (冪等)."""
        if self._serial is not None:
            try:
                if self._serial.is_open:
                    self._serial.close()
                    logger.info("Serial port closed")
            except Exception:
                logger.exception("Error while closing serial port")
            finally:
                self._serial = None
                self._is_open = False

    def write(self, command: str) -> None:
        r"""コマンド文字列を送信する。末尾に \r を自動付加する.

        Args:
            command: 送信する AT コマンドまたは OBD コマンド.

        Raises:
            ConnectionError: 送信に失敗した場合.

        traces: HWR-22
        """
        if self._serial is None or not self._is_open:
            msg = "Serial port is not open"
            raise ConnectionError(msg)

        try:
            data = (command + "\r").encode("ascii")
            self._serial.write(data)
            self._serial.flush()

            logger.debug(
                "Command sent",
                extra={"command": command, "byte_count": len(data)},
            )

        except Exception as exc:
            self._is_open = False
            msg = f"Serial write failed: {exc}"
            logger.error(
                "Serial write failed",
                extra={"command": command, "error": str(exc)},
            )
            raise ConnectionError(msg) from exc

    def read_until_prompt(self) -> str:
        """ELM327 のプロンプト文字 '>' まで読み取る.

        Returns:
            プロンプト文字を除いた応答文字列.

        Raises:
            TimeoutError: タイムアウトした場合.
            ConnectionError: 通信断が発生した場合.

        traces: HWR-22
        """
        if self._serial is None or not self._is_open:
            msg = "Serial port is not open"
            raise ConnectionError(msg)

        try:
            response_bytes = b""
            while True:
                byte = self._serial.read(1)
                if not byte:
                    # タイムアウト
                    if response_bytes:
                        # 部分応答があれば返す
                        break
                    msg = "ELM327 response timeout"
                    raise TimeoutError(msg)

                response_bytes += byte
                if byte == b">":
                    break

            response = response_bytes.decode("ascii", errors="replace")
            # プロンプト文字を除去
            response = response.rstrip(">")

            logger.debug(
                "Response received",
                extra={
                    "response_length": len(response),
                    "response_repr": repr(response[:100]),
                },
            )
            return response

        except TimeoutError:
            raise

        except Exception as exc:
            self._is_open = False
            msg = f"Serial read failed: {exc}"
            logger.error(
                "Serial read failed",
                extra={"error": str(exc)},
            )
            raise ConnectionError(msg) from exc
