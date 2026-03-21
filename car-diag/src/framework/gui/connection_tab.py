"""ConnectionTab: 接続タブ (COM ポート選択、接続/切断ボタン).

traces: FR-01a, FR-01b, FR-01d, FR-02b
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import (
        QComboBox,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    _PYQT6_AVAILABLE = True
except ImportError:
    _PYQT6_AVAILABLE = False
    QWidget = object  # type: ignore[assignment, misc]


class ConnectionTab(QWidget if _PYQT6_AVAILABLE else object):  # type: ignore[misc]
    """接続タブウィジェット.

    COM ポートの選択、接続/切断、ECU スキャン開始の UI を提供する。

    Attributes:
        _port_combo: COM ポート選択コンボボックス.
        _connect_button: 接続ボタン.
        _disconnect_button: 切断ボタン.
        _scan_ecu_button: ECU スキャンボタン.
        _refresh_button: ポート一覧更新ボタン.
    """

    if _PYQT6_AVAILABLE:
        connect_requested = pyqtSignal(str)
        disconnect_requested = pyqtSignal()
        scan_ecu_requested = pyqtSignal()
        refresh_ports_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """ConnectionTab を初期化する.

        Args:
            parent: 親ウィジェット.
        """
        if not _PYQT6_AVAILABLE:
            logger.error("PyQt6 is not installed")
            return

        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI コンポーネントを構築する."""
        layout = QVBoxLayout(self)

        # COM ポート選択グループ
        port_group = QGroupBox("COM ポート")
        port_layout = QHBoxLayout()

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(200)
        port_layout.addWidget(QLabel("ポート:"))
        port_layout.addWidget(self._port_combo)

        self._refresh_button = QPushButton("更新")
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        port_layout.addWidget(self._refresh_button)

        port_group.setLayout(port_layout)
        layout.addWidget(port_group)

        # 接続操作グループ
        action_group = QGroupBox("接続操作")
        action_layout = QHBoxLayout()

        self._connect_button = QPushButton("接続")
        self._connect_button.clicked.connect(self._on_connect_clicked)
        action_layout.addWidget(self._connect_button)

        self._disconnect_button = QPushButton("切断")
        self._disconnect_button.setEnabled(False)
        self._disconnect_button.clicked.connect(self._on_disconnect_clicked)
        action_layout.addWidget(self._disconnect_button)

        self._scan_ecu_button = QPushButton("ECU スキャン")
        self._scan_ecu_button.setEnabled(False)
        self._scan_ecu_button.clicked.connect(self._on_scan_ecu_clicked)
        action_layout.addWidget(self._scan_ecu_button)

        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        layout.addStretch()

    def set_ports(self, port_list: list[dict[str, str]]) -> None:
        """COM ポート一覧を設定する.

        Args:
            port_list: ポート情報の辞書リスト.

        traces: FR-01a
        """
        self._port_combo.clear()
        for port_info in port_list:
            display_text = (
                f"{port_info['port_name']} - {port_info['description']}"
            )
            self._port_combo.addItem(display_text, port_info["port_name"])

    def set_connected_state(self, connected: bool) -> None:
        """接続状態に応じて UI を更新する.

        Args:
            connected: 接続中の場合 True.

        traces: FR-02b
        """
        self._connect_button.setEnabled(not connected)
        self._disconnect_button.setEnabled(connected)
        self._scan_ecu_button.setEnabled(connected)
        self._port_combo.setEnabled(not connected)
        self._refresh_button.setEnabled(not connected)

    def _on_connect_clicked(self) -> None:
        """接続ボタンクリック時."""
        port_name = self._port_combo.currentData()
        if port_name:
            self.connect_requested.emit(port_name)

    def _on_disconnect_clicked(self) -> None:
        """切断ボタンクリック時."""
        self.disconnect_requested.emit()

    def _on_scan_ecu_clicked(self) -> None:
        """ECU スキャンボタンクリック時."""
        self.scan_ecu_requested.emit()

    def _on_refresh_clicked(self) -> None:
        """ポート更新ボタンクリック時."""
        self.refresh_ports_requested.emit()
