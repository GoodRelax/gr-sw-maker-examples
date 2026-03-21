"""DtcTab: DTC タブ (DTC 読取/消去ボタン、DTC リスト表示).

traces: FR-06b, FR-06c, FR-06d, FR-07a
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import (
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    _PYQT6_AVAILABLE = True
except ImportError:
    _PYQT6_AVAILABLE = False
    QWidget = object  # type: ignore[assignment, misc]


class DtcTab(QWidget if _PYQT6_AVAILABLE else object):  # type: ignore[misc]
    """DTC タブウィジェット.

    DTC の読取・消去操作と DTC リスト表示を提供する。

    Attributes:
        _read_button: DTC 読取ボタン.
        _clear_button: DTC 消去ボタン.
        _dtc_table: DTC 表示テーブル.
        _dtc_count_label: DTC 件数ラベル.
    """

    if _PYQT6_AVAILABLE:
        read_dtcs_requested = pyqtSignal()
        clear_dtcs_requested = pyqtSignal()

    _DTC_TABLE_COLUMNS = ["ECU", "DTC コード", "説明", "ステータス", "プロトコル"]

    def __init__(self, parent: QWidget | None = None) -> None:
        """DtcTab を初期化する.

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

        # 操作ボタングループ
        button_group = QGroupBox("DTC 操作")
        button_layout = QHBoxLayout()

        self._read_button = QPushButton("DTC 読取")
        self._read_button.setEnabled(False)
        self._read_button.clicked.connect(self._on_read_clicked)
        button_layout.addWidget(self._read_button)

        self._clear_button = QPushButton("DTC 消去")
        self._clear_button.setEnabled(False)
        self._clear_button.clicked.connect(self._on_clear_clicked)
        button_layout.addWidget(self._clear_button)

        self._dtc_count_label = QLabel("DTC: ---")
        button_layout.addWidget(self._dtc_count_label)

        button_layout.addStretch()
        button_group.setLayout(button_layout)
        layout.addWidget(button_group)

        # DTC テーブル (FR-06c)
        self._dtc_table = QTableWidget()
        self._dtc_table.setColumnCount(len(self._DTC_TABLE_COLUMNS))
        self._dtc_table.setHorizontalHeaderLabels(self._DTC_TABLE_COLUMNS)
        self._dtc_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch,
        )
        self._dtc_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers,
        )
        layout.addWidget(self._dtc_table)

    def set_enabled(self, enabled: bool) -> None:
        """操作ボタンの有効/無効を切り替える.

        Args:
            enabled: 有効にする場合 True.
        """
        self._read_button.setEnabled(enabled)
        self._clear_button.setEnabled(enabled)

    def display_dtcs(
        self,
        dtc_by_ecu: dict[str, list[dict[str, str]]],
    ) -> None:
        """DTC リストを表示する.

        Args:
            dtc_by_ecu: ECU 識別子をキー、DTC 情報辞書リストを値とする辞書.

        traces: FR-06b, FR-06c, FR-06d
        """
        self._dtc_table.setRowCount(0)

        total_dtc_count = 0
        for ecu_id, dtc_list in dtc_by_ecu.items():
            for dtc_info in dtc_list:
                row = self._dtc_table.rowCount()
                self._dtc_table.insertRow(row)
                self._dtc_table.setItem(
                    row, 0, QTableWidgetItem(ecu_id),
                )
                self._dtc_table.setItem(
                    row, 1, QTableWidgetItem(dtc_info.get("dtc_code", "")),
                )
                self._dtc_table.setItem(
                    row, 2, QTableWidgetItem(dtc_info.get("description", "")),
                )
                self._dtc_table.setItem(
                    row, 3, QTableWidgetItem(dtc_info.get("status", "")),
                )
                self._dtc_table.setItem(
                    row, 4, QTableWidgetItem(dtc_info.get("protocol", "")),
                )
                total_dtc_count += 1

        # FR-06d: DTC 0 件の場合
        if total_dtc_count == 0:
            self._dtc_count_label.setText("DTC なし")
        else:
            self._dtc_count_label.setText(f"DTC: {total_dtc_count} 件")

    def _on_read_clicked(self) -> None:
        """DTC 読取ボタンクリック時."""
        self.read_dtcs_requested.emit()

    def _on_clear_clicked(self) -> None:
        """DTC 消去ボタンクリック時."""
        self.clear_dtcs_requested.emit()
