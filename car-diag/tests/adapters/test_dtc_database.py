"""JsonDtcDatabase のユニットテスト.

DTC 説明文の検索機能をテストする。
"""

from __future__ import annotations

from src.adapters.dtc_database import JsonDtcDatabase


class TestLookup:
    """DTC 説明文検索のテスト."""

    def test_known_dtc_returns_description(self) -> None:
        """既知の DTC コードは説明文を返す."""
        db = JsonDtcDatabase()
        description = db.lookup("P0300")
        assert description == "Random/Multiple Cylinder Misfire Detected"

    def test_unknown_dtc_returns_unknown(self) -> None:
        """未知の DTC コードは 'Unknown' を返す."""
        db = JsonDtcDatabase()
        description = db.lookup("P1234")
        assert description == "Unknown"

    def test_uds_dtc_with_suffix(self) -> None:
        """UDS DTC コード (P0143-07) のサフィックスを除去して検索する."""
        db = JsonDtcDatabase()
        description = db.lookup("P0143-07")
        assert description != "Unknown"
        assert "O2 Sensor" in description

    def test_case_insensitive_lookup(self) -> None:
        """大小文字を区別せずに検索する."""
        db = JsonDtcDatabase()
        description = db.lookup("p0300")
        assert description == "Random/Multiple Cylinder Misfire Detected"

    def test_additional_descriptions(self) -> None:
        """追加辞書のエントリが検索可能."""
        additional = {"P1500": "Custom Manufacturer DTC"}
        db = JsonDtcDatabase(additional_descriptions=additional)
        assert db.lookup("P1500") == "Custom Manufacturer DTC"

    def test_dtc_count_builtin(self) -> None:
        """内蔵辞書に50件以上の DTC が登録されている."""
        db = JsonDtcDatabase()
        assert db.dtc_count >= 50

    def test_powertrain_dtc_coverage(self) -> None:
        """P0001-P0499 の主要 DTC がカバーされている."""
        db = JsonDtcDatabase()
        # 各カテゴリの代表的な DTC を確認
        assert db.lookup("P0100") != "Unknown"  # MAF
        assert db.lookup("P0171") != "Unknown"  # Lean
        assert db.lookup("P0301") != "Unknown"  # Misfire Cyl 1
        assert db.lookup("P0420") != "Unknown"  # Catalyst
