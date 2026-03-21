"""DidScanDialog: DID スキャンダイアログ (2 段プログレスバー).

traces: FR-05d, FR-05e, FR-02c
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import pyqtSignal
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


class DidScanDialog(QDialog if _PYQT6_AVAILABLE else object):  # type: ignore[misc]
    """DID スキャン進捗ダイアログ (2 段プログレスバー).

    全体進捗と現在 ECU 進捗を 2 段のプログレスバーで表示する。

    Attributes:
        _overall_progress: 全体プログレスバー.
        _ecu_progress: 現在 ECU プログレスバー.
        _overall_label: 全体進捗ラベル.
        _ecu_label: ECU 進捗ラベル.
        _found_label: 検出 DID 数ラベル.
        _abort_button: 中断ボタン.
    """

    if _PYQT6_AVAILABLE:
        abort_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """DidScanDialog を初期化する.

        Args:
            parent: 親ウィジェット.
        """
        if not _PYQT6_AVAILABLE:
            logger.error("PyQt6 is not installed")
            return

        super().__init__(parent)
        self.setWindowTitle("DID スキャン")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI コンポーネントを構築する."""
        layout = QVBoxLayout(self)

        # 全体進捗
        self._overall_label = QLabel("全体進捗:")
        layout.addWidget(self._overall_label)

        self._overall_progress = QProgressBar()
        self._overall_progress.setMinimum(0)
        self._overall_progress.setMaximum(100)
        layout.addWidget(self._overall_progress)

        # ECU 進捗
        self._ecu_label = QLabel("ECU 進捗:")
        layout.addWidget(self._ecu_label)

        self._ecu_progress = QProgressBar()
        self._ecu_progress.setMinimum(0)
        self._ecu_progress.setMaximum(100)
        layout.addWidget(self._ecu_progress)

        # 検出 DID 数
        self._found_label = QLabel("検出 DID: 0 件")
        layout.addWidget(self._found_label)

        # 中断ボタン (FR-02c)
        self._abort_button = QPushButton("中断")
        self._abort_button.clicked.connect(self._on_abort_clicked)
        layout.addWidget(self._abort_button)

    def update_overall_progress(
        self,
        current_ecu: int,
        total_ecus: int,
        message: str,
    ) -> None:
        """全体進捗を更新する.

        Args:
            current_ecu: 現在の ECU インデックス.
            total_ecus: 総 ECU 数.
            message: 進捗メッセージ.

        traces: FR-05d
        """
        if total_ecus > 0:
            percentage = int(current_ecu / total_ecus * 100)
            self._overall_progress.setValue(percentage)
        self._overall_label.setText(
            f"全体進捗: 全{total_ecus}ECU中、残り{total_ecus - current_ecu}ECU "
            f"| {message}",
        )

    def update_ecu_progress(
        self,
        scanned_dids: int,
        total_dids: int,
        ecu_name: str,
    ) -> None:
        """ECU 進捗を更新する.

        Args:
            scanned_dids: スキャン済み DID 数.
            total_dids: スキャン対象の総 DID 数.
            ecu_name: 現在スキャン中の ECU 名.

        traces: FR-05d
        """
        if total_dids > 0:
            percentage = int(scanned_dids / total_dids * 100)
            self._ecu_progress.setValue(percentage)
        self._ecu_label.setText(
            f"ECU {ecu_name}: {scanned_dids}/{total_dids} DID スキャン済",
        )

    def update_found_count(self, found_count: int) -> None:
        """検出 DID 数を更新する.

        Args:
            found_count: 検出された DID 数.

        traces: FR-05d
        """
        self._found_label.setText(f"検出 DID: {found_count} 件")

    def _on_abort_clicked(self) -> None:
        """中断ボタンクリック時.

        traces: FR-05e
        """
        self.abort_requested.emit()
        self._abort_button.setEnabled(False)
        self._overall_label.setText("中断処理中...")
