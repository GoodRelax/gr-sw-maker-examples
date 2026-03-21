"""EcuScanDialog: ECU スキャンダイアログ (進捗表示).

traces: FR-03d, FR-02c
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QDialog,
        QLabel,
        QProgressBar,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    _PYQT6_AVAILABLE = True
except ImportError:
    _PYQT6_AVAILABLE = False
    QDialog = object  # type: ignore[assignment, misc]


class EcuScanDialog(QDialog if _PYQT6_AVAILABLE else object):  # type: ignore[misc]
    """ECU スキャン進捗ダイアログ.

    ECU スキャン中にプログレスバーとメッセージを表示する。

    Attributes:
        _progress_bar: プログレスバー.
        _message_label: 進捗メッセージラベル.
        _abort_button: 中断ボタン.
    """

    if _PYQT6_AVAILABLE:
        abort_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """EcuScanDialog を初期化する.

        Args:
            parent: 親ウィジェット.
        """
        if not _PYQT6_AVAILABLE:
            logger.error("PyQt6 is not installed")
            return

        super().__init__(parent)
        self.setWindowTitle("ECU スキャン")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI コンポーネントを構築する."""
        layout = QVBoxLayout(self)

        self._message_label = QLabel("ECU をスキャン中...")
        layout.addWidget(self._message_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        layout.addWidget(self._progress_bar)

        self._abort_button = QPushButton("中断")
        self._abort_button.clicked.connect(self._on_abort_clicked)
        layout.addWidget(self._abort_button)

    def update_progress(
        self,
        current: int,
        total: int,
        message: str,
    ) -> None:
        """進捗を更新する.

        Args:
            current: 現在のステップ.
            total: 総ステップ数.
            message: 進捗メッセージ.

        traces: FR-03d
        """
        if total > 0:
            percentage = int(current / total * 100)
            self._progress_bar.setValue(percentage)
        self._message_label.setText(message)

    def _on_abort_clicked(self) -> None:
        """中断ボタンクリック時.

        traces: FR-02c
        """
        self.abort_requested.emit()
        self._abort_button.setEnabled(False)
        self._message_label.setText("中断処理中...")
