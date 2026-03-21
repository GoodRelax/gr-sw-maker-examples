"""DashboardTab: ダッシュボードタブ (パラメータ値 + グラフ).

traces: FR-08a, FR-08b, FR-08c, FR-08d
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import (
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    _PYQT6_AVAILABLE = True
except ImportError:
    _PYQT6_AVAILABLE = False
    QWidget = object  # type: ignore[assignment, misc]

try:
    import pyqtgraph as pg

    _PYQTGRAPH_AVAILABLE = True
except ImportError:
    _PYQTGRAPH_AVAILABLE = False


class DashboardTab(QWidget if _PYQT6_AVAILABLE else object):  # type: ignore[misc]
    """ダッシュボードタブウィジェット.

    リアルタイムパラメータ値とグラフを表示する。

    Attributes:
        _start_button: モニタリング開始ボタン.
        _stop_button: モニタリング停止ボタン.
        _param_table: パラメータ値テーブル.
        _graph_widget: pyqtgraph グラフウィジェット.
        GRAPH_DATA_POINT_LIMIT: グラフデータ点数の上限 (5分分 = 600点).
    """

    if _PYQT6_AVAILABLE:
        start_monitoring_requested = pyqtSignal()
        stop_monitoring_requested = pyqtSignal()

    # M-03: グラフデータ点数の上限 (ポーリング間隔 0.5s x 5分 = 600点)
    GRAPH_DATA_POINT_LIMIT: int = 600

    _PARAM_TABLE_COLUMNS = ["パラメータ", "値", "単位", "ECU"]

    def __init__(self, parent: QWidget | None = None) -> None:
        """DashboardTab を初期化する.

        Args:
            parent: 親ウィジェット.
        """
        if not _PYQT6_AVAILABLE:
            logger.error("PyQt6 is not installed")
            return

        super().__init__(parent)
        self._graph_data: dict[str, list[float]] = {}
        self._graph_curves: dict[str, object] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI コンポーネントを構築する."""
        layout = QVBoxLayout(self)

        # 操作ボタン
        button_layout = QHBoxLayout()
        self._start_button = QPushButton("モニタリング開始")
        self._start_button.setEnabled(False)
        self._start_button.clicked.connect(self._on_start_clicked)
        button_layout.addWidget(self._start_button)

        self._stop_button = QPushButton("モニタリング停止")
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._on_stop_clicked)
        button_layout.addWidget(self._stop_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # スプリッター: テーブル + グラフ
        splitter = QSplitter()

        # パラメータ値テーブル
        self._param_table = QTableWidget()
        self._param_table.setColumnCount(len(self._PARAM_TABLE_COLUMNS))
        self._param_table.setHorizontalHeaderLabels(self._PARAM_TABLE_COLUMNS)
        self._param_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers,
        )
        # パラメータ列を内容に合わせて伸縮させる (CR-001)
        header = self._param_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.resizeSection(0, 250)  # パラメータ名
        header.resizeSection(1, 120)  # 値
        header.resizeSection(2, 60)   # 単位
        splitter.addWidget(self._param_table)

        # グラフ領域 (FR-08c)
        if _PYQTGRAPH_AVAILABLE:
            self._graph_widget = pg.PlotWidget()
            self._graph_widget.setLabel("bottom", "Time", units="s")
            self._graph_widget.setLabel("left", "Value")
            self._graph_widget.addLegend()
            splitter.addWidget(self._graph_widget)
        else:
            graph_placeholder = QLabel("pyqtgraph が未インストールです")
            splitter.addWidget(graph_placeholder)
            self._graph_widget = None

        layout.addWidget(splitter)

    def set_enabled(self, enabled: bool) -> None:
        """操作ボタンの有効/無効を切り替える.

        Args:
            enabled: 有効にする場合 True.
        """
        self._start_button.setEnabled(enabled)

    def set_monitoring_state(self, monitoring: bool) -> None:
        """モニタリング状態に応じて UI を更新する.

        Args:
            monitoring: モニタリング中の場合 True.
        """
        self._start_button.setEnabled(not monitoring)
        self._stop_button.setEnabled(monitoring)

    def update_parameters(
        self,
        parameters: list[dict[str, str]],
    ) -> None:
        """パラメータ値を更新する.

        Args:
            parameters: パラメータ情報辞書のリスト.

        traces: FR-08b
        """
        self._param_table.setRowCount(len(parameters))
        for row, param in enumerate(parameters):
            self._param_table.setItem(
                row, 0, QTableWidgetItem(param.get("name", "")),
            )
            self._param_table.setItem(
                row, 1, QTableWidgetItem(param.get("value", "")),
            )
            self._param_table.setItem(
                row, 2, QTableWidgetItem(param.get("unit", "")),
            )
            self._param_table.setItem(
                row, 3, QTableWidgetItem(param.get("ecu", "")),
            )

    def append_graph_data(
        self,
        parameters: list[dict[str, str]],
    ) -> None:
        """グラフにデータ点を追加する.

        GRAPH_DATA_POINT_LIMIT (600点 = 5分分) を超えた古いデータは破棄する。

        Args:
            parameters: パラメータ情報辞書のリスト.

        traces: FR-08c
        """
        if self._graph_widget is None:
            return

        colors = ["r", "g", "b", "y", "c", "m", "w"]
        for idx, param in enumerate(parameters):
            param_name = param.get("name", "")
            value_str = param.get("value", "")
            if not param_name or not value_str:
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            if param_name not in self._graph_data:
                self._graph_data[param_name] = []
                color = colors[idx % len(colors)]
                curve = self._graph_widget.plot(
                    [], [], pen=color, name=param_name,
                )
                self._graph_curves[param_name] = curve

            data_points = self._graph_data[param_name]
            data_points.append(value)

            # M-03: 上限 600 点を超えた古いデータを破棄
            if len(data_points) > self.GRAPH_DATA_POINT_LIMIT:
                excess = len(data_points) - self.GRAPH_DATA_POINT_LIMIT
                del data_points[:excess]

            curve = self._graph_curves[param_name]
            x_values = list(range(len(data_points)))
            curve.setData(x_values, data_points)  # type: ignore[union-attr]

    def clear_graph_data(self) -> None:
        """グラフデータをクリアする."""
        self._graph_data.clear()
        self._graph_curves.clear()
        if self._graph_widget is not None:
            self._graph_widget.clear()
            self._graph_widget.addLegend()

    def _on_start_clicked(self) -> None:
        """モニタリング開始ボタンクリック時."""
        self.start_monitoring_requested.emit()

    def _on_stop_clicked(self) -> None:
        """モニタリング停止ボタンクリック時."""
        self.stop_monitoring_requested.emit()
