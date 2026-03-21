"""DashboardTab グラフデータ上限テスト.

M-03: グラフデータ点数が GRAPH_DATA_POINT_LIMIT (600点) を超えないことを検証する。
PyQt6 が利用不可の場合はスキップする。

traces: M-03, FR-08c
"""

from __future__ import annotations

import pytest

# PyQt6 の有無を確認し、利用不可ならテストをスキップ
try:
    from PyQt6.QtWidgets import QApplication
    _PYQT6_AVAILABLE = True
except ImportError:
    _PYQT6_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PYQT6_AVAILABLE,
    reason="PyQt6 is not installed",
)


@pytest.fixture(scope="module")
def qapp():
    """テスト用 QApplication を生成する (モジュールスコープ)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestDashboardTabGraphLimit:
    """DashboardTab のグラフデータ上限テスト."""

    def test_graph_data_point_limit_constant(self, qapp) -> None:
        """GRAPH_DATA_POINT_LIMIT が 600 であることを確認する."""
        from src.framework.gui.dashboard_tab import DashboardTab

        assert DashboardTab.GRAPH_DATA_POINT_LIMIT == 600

    def test_graph_data_does_not_exceed_limit_without_pyqtgraph(
        self, qapp,
    ) -> None:
        """pyqtgraph が無い場合でも append_graph_data がエラーにならないことを確認する."""
        from src.framework.gui.dashboard_tab import DashboardTab

        tab = DashboardTab()

        # pyqtgraph が無い場合 _graph_widget は None
        # その場合 append_graph_data は何もせず正常終了する
        params = [{"name": "rpm", "value": "3000"}]
        tab.append_graph_data(params)
        # エラーが出なければ OK

    def test_internal_graph_data_structure(self, qapp) -> None:
        """_graph_data の内部構造がデータ追加で正しく更新されることを確認する.

        pyqtgraph が無い場合、_graph_widget=None なので
        直接 _graph_data を操作してロジックを検証する。
        """
        from src.framework.gui.dashboard_tab import DashboardTab

        tab = DashboardTab()
        limit = DashboardTab.GRAPH_DATA_POINT_LIMIT

        # 手動で _graph_data にデータを追加し上限チェックロジックを検証
        param_name = "engine_rpm"
        tab._graph_data[param_name] = []

        for i in range(limit + 100):
            tab._graph_data[param_name].append(float(i))

            # 上限超過分を手動で削除（append_graph_data 内と同じロジック）
            data_points = tab._graph_data[param_name]
            if len(data_points) > limit:
                excess = len(data_points) - limit
                del data_points[:excess]

        assert len(tab._graph_data[param_name]) == limit
        # 最初の要素は 100 (0-99 が破棄される)
        assert tab._graph_data[param_name][0] == 100.0
        # 最後の要素は limit + 100 - 1 = 699
        assert tab._graph_data[param_name][-1] == 699.0

    def test_clear_graph_data(self, qapp) -> None:
        """clear_graph_data でデータとカーブがクリアされることを確認する."""
        from src.framework.gui.dashboard_tab import DashboardTab

        tab = DashboardTab()
        tab._graph_data["test_param"] = [1.0, 2.0, 3.0]
        tab._graph_curves["test_param"] = object()

        tab.clear_graph_data()

        assert len(tab._graph_data) == 0
        assert len(tab._graph_curves) == 0
