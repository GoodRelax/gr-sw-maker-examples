"""RecordingTab: 記録タブ (記録開始/停止、ファイル選択).

traces: FR-09a, FR-09d, FR-09e
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import (
        QFileDialog,
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


class RecordingTab(QWidget if _PYQT6_AVAILABLE else object):  # type: ignore[misc]
    """記録タブウィジェット.

    データ記録の開始/停止とファイル選択を提供する。

    Attributes:
        _start_button: 記録開始ボタン.
        _stop_button: 記録停止ボタン.
        _status_label: 記録状態ラベル.
        _row_count_label: 記録行数ラベル.
        _file_path_label: 記録先ファイルパスラベル.
    """

    if _PYQT6_AVAILABLE:
        start_recording_requested = pyqtSignal(str)
        stop_recording_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """RecordingTab を初期化する.

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

        # 記録操作グループ
        record_group = QGroupBox("データ記録")
        record_layout = QVBoxLayout()

        # ボタン行
        button_layout = QHBoxLayout()

        self._start_button = QPushButton("記録開始")
        self._start_button.setEnabled(False)
        self._start_button.clicked.connect(self._on_start_clicked)
        button_layout.addWidget(self._start_button)

        self._stop_button = QPushButton("記録停止")
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._on_stop_clicked)
        button_layout.addWidget(self._stop_button)

        button_layout.addStretch()
        record_layout.addLayout(button_layout)

        # 状態表示
        self._file_path_label = QLabel("記録先: ---")
        record_layout.addWidget(self._file_path_label)

        self._status_label = QLabel("状態: 停止")
        record_layout.addWidget(self._status_label)

        self._row_count_label = QLabel("記録行数: 0")
        record_layout.addWidget(self._row_count_label)

        record_group.setLayout(record_layout)
        layout.addWidget(record_group)
        layout.addStretch()

    def set_enabled(self, enabled: bool) -> None:
        """操作ボタンの有効/無効を切り替える.

        Args:
            enabled: 有効にする場合 True.
        """
        self._start_button.setEnabled(enabled)

    def set_recording_state(self, recording: bool) -> None:
        """記録状態に応じて UI を更新する.

        Args:
            recording: 記録中の場合 True.
        """
        self._start_button.setEnabled(not recording)
        self._stop_button.setEnabled(recording)
        self._status_label.setText(
            "状態: 記録中" if recording else "状態: 停止",
        )

    def update_row_count(self, row_count: int) -> None:
        """記録行数を更新する.

        Args:
            row_count: 現在の記録行数.

        traces: FR-09e
        """
        self._row_count_label.setText(f"記録行数: {row_count}")

    def _on_start_clicked(self) -> None:
        """記録開始ボタンクリック時.

        traces: FR-09a
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "記録先ファイルの選択",
            "",
            "TSV ファイル (*.tsv);;全てのファイル (*)",
        )
        if file_path:
            self._file_path_label.setText(f"記録先: {file_path}")
            self.start_recording_requested.emit(file_path)

    def _on_stop_clicked(self) -> None:
        """記録停止ボタンクリック時.

        traces: FR-09d
        """
        self.stop_recording_requested.emit()
