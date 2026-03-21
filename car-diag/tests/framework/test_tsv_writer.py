"""TsvFileWriter のユニットテスト.

TSV ファイルの書き込み、ヘッダー行出力、fsync、エラーハンドリングをテストする。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.framework.tsv_writer import TsvFileWriter


@pytest.fixture()
def writer() -> TsvFileWriter:
    """TsvFileWriter フィクスチャ."""
    return TsvFileWriter()


class TestOpenFile:
    """ファイルオープンのテスト."""

    def test_open_creates_file_with_header(
        self,
        tmp_path: Path,
        writer: TsvFileWriter,
    ) -> None:
        """ファイルを開くとヘッダー行が書き込まれる."""
        file_path = str(tmp_path / "test.tsv")
        writer.open_file(file_path, ["timestamp", "rpm", "speed"])
        writer.close_file()

        content = Path(file_path).read_text(encoding="utf-8")
        assert content.startswith("timestamp\trpm\tspeed\n")

    def test_open_creates_parent_dirs(
        self,
        tmp_path: Path,
        writer: TsvFileWriter,
    ) -> None:
        """親ディレクトリが存在しない場合は作成される."""
        file_path = str(tmp_path / "subdir" / "nested" / "test.tsv")
        writer.open_file(file_path, ["col1"])
        writer.close_file()

        assert Path(file_path).exists()

    def test_is_open_property(
        self,
        tmp_path: Path,
        writer: TsvFileWriter,
    ) -> None:
        """is_open プロパティが正しく動作する."""
        assert not writer.is_open

        file_path = str(tmp_path / "test.tsv")
        writer.open_file(file_path, ["col1"])
        assert writer.is_open

        writer.close_file()
        assert not writer.is_open


class TestWriteRow:
    """行書き込みのテスト."""

    def test_write_rows(
        self,
        tmp_path: Path,
        writer: TsvFileWriter,
    ) -> None:
        """データ行を正しく書き込める."""
        file_path = str(tmp_path / "test.tsv")
        writer.open_file(file_path, ["timestamp", "rpm", "speed"])

        writer.write_row(["2024-01-01T00:00:00", "3000", "60"])
        writer.write_row(["2024-01-01T00:00:01", "3100", "65"])
        writer.close_file()

        lines = Path(file_path).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows
        assert lines[1] == "2024-01-01T00:00:00\t3000\t60"
        assert lines[2] == "2024-01-01T00:00:01\t3100\t65"

    def test_row_count_tracked(
        self,
        tmp_path: Path,
        writer: TsvFileWriter,
    ) -> None:
        """行数カウントが正しい."""
        file_path = str(tmp_path / "test.tsv")
        writer.open_file(file_path, ["col1"])

        assert writer.row_count == 0
        writer.write_row(["val1"])
        assert writer.row_count == 1
        writer.write_row(["val2"])
        assert writer.row_count == 2

        writer.close_file()

    def test_write_to_closed_file_is_noop(
        self,
        writer: TsvFileWriter,
    ) -> None:
        """閉じたファイルへの書き込みは何もしない."""
        writer.write_row(["test"])
        assert writer.row_count == 0


class TestCloseFile:
    """ファイルクローズのテスト."""

    def test_close_is_idempotent(
        self,
        tmp_path: Path,
        writer: TsvFileWriter,
    ) -> None:
        """close_file は冪等."""
        file_path = str(tmp_path / "test.tsv")
        writer.open_file(file_path, ["col1"])
        writer.close_file()
        writer.close_file()  # 2回目も例外なし


class TestEmergencyFlush:
    """緊急フラッシュのテスト."""

    def test_emergency_flush_preserves_data(
        self,
        tmp_path: Path,
        writer: TsvFileWriter,
    ) -> None:
        """緊急フラッシュでデータが保全される."""
        file_path = str(tmp_path / "test.tsv")
        writer.open_file(file_path, ["timestamp", "value"])
        writer.write_row(["T1", "100"])
        writer.write_row(["T2", "200"])

        writer.flush_for_emergency()

        content = Path(file_path).read_text(encoding="utf-8")
        assert "T1\t100" in content
        assert "T2\t200" in content
        assert not writer.is_open


class TestDiskFullHandling:
    """ディスクフルエラーハンドリングのテスト."""

    def test_open_invalid_device_path_raises_oserror(
        self,
        writer: TsvFileWriter,
    ) -> None:
        """書き込み不可パスでは OSError が発生する."""
        # NUL デバイスのサブパスなど、OS が拒否するパスを使用
        import sys
        if sys.platform == "win32":
            invalid_path = "Z:\\__nonexistent_drive__\\file.tsv"
        else:
            invalid_path = "/dev/null/impossible/file.tsv"

        with pytest.raises(OSError):
            writer.open_file(invalid_path, ["col1"])
