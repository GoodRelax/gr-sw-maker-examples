"""MainWindow: PyQt6 メインウインドウ (タブ切替方式).

traces: FR-01a, FR-01f, NFR-03a
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QMainWindow,
        QStatusBar,
        QTabWidget,
        QWidget,
    )

    _PYQT6_AVAILABLE = True
except ImportError:
    _PYQT6_AVAILABLE = False
    # テスト環境用のスタブ
    QMainWindow = object  # type: ignore[assignment, misc]


class MainWindow(QMainWindow if _PYQT6_AVAILABLE else object):  # type: ignore[misc]
    """アプリケーションメインウインドウ.

    タブ切替方式の UI を提供する。

    Attributes:
        _tab_widget: タブウィジェット.
        _status_bar: ステータスバー.
    """

    WINDOW_TITLE = "car-diag - ELM327 OBD-II Diagnostic Tool"
    WINDOW_MIN_WIDTH = 900
    WINDOW_MIN_HEIGHT = 600

    def __init__(self, parent: QWidget | None = None) -> None:
        """MainWindow を初期化する.

        Args:
            parent: 親ウィジェット.
        """
        if not _PYQT6_AVAILABLE:
            logger.error("PyQt6 is not installed")
            return

        super().__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)

        self._setup_ui()
        logger.info("MainWindow initialized")

    def _setup_ui(self) -> None:
        """UI コンポーネントを構築する."""
        # タブウィジェット
        self._tab_widget = QTabWidget()
        self.setCentralWidget(self._tab_widget)

        # ステータスバー (FR-01f)
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self.update_status_message("未接続")

    def add_tab(self, widget: QWidget, tab_label: str) -> None:
        """タブを追加する.

        Args:
            widget: タブに表示するウィジェット.
            tab_label: タブのラベル.
        """
        self._tab_widget.addTab(widget, tab_label)

    def update_status_message(self, message: str) -> None:
        """ステータスバーのメッセージを更新する.

        Args:
            message: 表示するメッセージ.

        traces: FR-01f, FR-02a
        """
        self._status_bar.showMessage(message)

    def update_connection_status(
        self,
        port_name: str,
        protocol_name: str,
    ) -> None:
        """接続状態をステータスバーに表示する.

        Args:
            port_name: 接続中の COM ポート名.
            protocol_name: 検出されたプロトコル名.

        traces: FR-01f
        """
        status_text = f"接続中: {port_name} | プロトコル: {protocol_name}"
        self.update_status_message(status_text)
