"""抽象インターフェース定義（Protocol ベース DIP）.

Use Case 層が依存する外部インターフェースを typing.Protocol で定義する。
Adapter 層・Framework 層の具体実装はこれらの Protocol を満たす。

traces: NFR-05a, ADR-001
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

from src.entities.dtc import DTC
from src.entities.ecu import EcuInfo
from src.entities.vehicle_parameter import VehicleParameter


@runtime_checkable
class SerialPort(Protocol):
    """シリアルポートの抽象インターフェース.

    ELM327 との物理通信を抽象化する。
    """

    @property
    def is_open(self) -> bool:
        """ポートが開いているかを返す."""
        ...

    def open(
        self,
        port_name: str,
        baudrate: int = 38400,
        timeout: float = 5.0,
    ) -> None:
        """シリアルポートを開く.

        Args:
            port_name: COM ポート名（例: "COM3"）.
            baudrate: ボーレート（デフォルト: 38400）.
            timeout: 読取タイムアウト秒数（デフォルト: 5.0）.

        Raises:
            ConnectionError: ポートが開けない場合.
        """
        ...

    def close(self) -> None:
        """シリアルポートを閉じる（冪等）."""
        ...

    def write(self, command: str) -> None:
        r"""コマンド文字列を送信する。末尾に \\r を自動付加する.

        Args:
            command: 送信する AT コマンドまたは OBD コマンド.

        Raises:
            ConnectionError: 送信に失敗した場合.
        """
        ...

    def read_until_prompt(self) -> str:
        """ELM327 のプロンプト文字 '>' まで読み取る.

        Returns:
            プロンプト文字を除いた応答文字列.

        Raises:
            TimeoutError: タイムアウトした場合.
            ConnectionError: 通信断が発生した場合.
        """
        ...


# 進捗コールバックの型: (current, total, message)
ProgressCallback = Callable[[int, int, str], None]


@runtime_checkable
class DiagProtocol(Protocol):
    """診断プロトコルの抽象インターフェース.

    ELM327Adapter が実装する。Use Case 層はこの Protocol にのみ依存する。
    """

    def scan_ecus(
        self,
        on_progress: ProgressCallback | None = None,
    ) -> list[EcuInfo]:
        """CAN + KWP の ECU をスキャンする.

        Args:
            on_progress: 進捗コールバック.

        Returns:
            検出された ECU 情報のリスト.
        """
        ...

    def read_dtcs(self, ecu: EcuInfo) -> list[DTC]:
        """指定 ECU から DTC を読み取る.

        Args:
            ecu: 対象 ECU.

        Returns:
            DTC のリスト.
        """
        ...

    def clear_dtcs(self, ecu: EcuInfo) -> bool:
        """指定 ECU の DTC を消去する.

        Args:
            ecu: 対象 ECU.

        Returns:
            消去に成功した場合 True.
        """
        ...

    def read_parameter(
        self,
        ecu: EcuInfo,
        parameter_id: str,
    ) -> VehicleParameter | None:
        """指定パラメータを読み取る.

        Args:
            ecu: 対象 ECU.
            parameter_id: PID or DID の hex 文字列.

        Returns:
            読取結果。読取失敗時は None.
        """
        ...

    def detect_supported_pids(self) -> list[str]:
        """車両が対応する PID のリストを検出する.

        Returns:
            対応 PID の hex 文字列リスト.
        """
        ...

    def scan_dids(
        self,
        ecu: EcuInfo,
        did_range_start: int,
        did_range_end: int,
        on_progress: ProgressCallback | None = None,
    ) -> list[str]:
        """指定範囲の DID をスキャンする.

        Args:
            ecu: 対象 ECU.
            did_range_start: スキャン開始 DID（0x0000-0xFFFF）.
            did_range_end: スキャン終了 DID（0x0000-0xFFFF）.
            on_progress: 進捗コールバック.

        Returns:
            応答のあった DID の hex 文字列リスト.
        """
        ...

    def switch_protocol(self, protocol_number: int) -> None:
        """ELM327 のプロトコルを切り替える.

        Args:
            protocol_number: ATSP のプロトコル番号（0-9）.
        """
        ...

    def send_command(self, command: str) -> str:
        """ELM327 にコマンドを送信し応答を返す.

        Args:
            command: 送信するコマンド文字列.

        Returns:
            応答文字列.
        """
        ...

    def initialize(self) -> str:
        """ELM327 初期化シーケンスを実行する.

        Returns:
            ELM327 のバージョン文字列.
        """
        ...


@runtime_checkable
class ScanCacheRepository(Protocol):
    """スキャンキャッシュの永続化インターフェース.

    traces: FR-04
    """

    def save(self, cache_key: str, cache_payload: dict[str, Any]) -> None:
        """キャッシュを保存する.

        Args:
            cache_key: VIN またはユーザー入力の識別名.
            cache_payload: キャッシュデータ.
        """
        ...

    def load(self, cache_key: str) -> dict[str, Any] | None:
        """キャッシュを読み込む.

        Args:
            cache_key: VIN またはユーザー入力の識別名.

        Returns:
            キャッシュデータ。存在しない場合は None.
        """
        ...

    def delete_expired(self, max_age_days: int) -> int:
        """有効期限切れのキャッシュを削除する.

        Args:
            max_age_days: キャッシュの最大保持日数.

        Returns:
            削除されたキャッシュファイル数.
        """
        ...

    def exists(self, cache_key: str) -> bool:
        """キャッシュが存在するかを確認する.

        Args:
            cache_key: VIN またはユーザー入力の識別名.

        Returns:
            存在する場合 True.
        """
        ...


@runtime_checkable
class DtcDescriptionProvider(Protocol):
    """DTC 説明文の検索インターフェース.

    traces: FR-06b, LIM-01
    """

    def lookup(self, dtc_code: str) -> str:
        """DTC コードに対応する説明文を返す.

        Args:
            dtc_code: DTC コード文字列（例: "P0143"）.

        Returns:
            英語説明文。該当なしの場合は "Unknown".
        """
        ...
