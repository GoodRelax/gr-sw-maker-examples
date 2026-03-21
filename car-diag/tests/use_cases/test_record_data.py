"""RecordDataUseCase のテスト."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.entities.vehicle_parameter import VehicleParameter
from src.use_cases.record_data import RecordDataUseCase


class TestRecordDataUseCase:
    """RecordDataUseCase のテスト."""

    def test_start_recording_creates_header(self) -> None:
        """記録開始時に TSV ヘッダー行が書き込まれる."""
        use_case = RecordDataUseCase()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False,
        ) as tmp:
            tmp_path = tmp.name

        try:
            use_case.start_recording(tmp_path, ["RPM", "Speed"])
            assert use_case.is_recording
            use_case.stop_recording()

            with open(tmp_path, encoding="utf-8") as f:
                header = f.readline().strip()
            assert header == "timestamp\tRPM\tSpeed"
        finally:
            os.unlink(tmp_path)

    def test_write_row_increments_count(self) -> None:
        """行書き込みで row_count が増加する."""
        use_case = RecordDataUseCase()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False,
        ) as tmp:
            tmp_path = tmp.name

        try:
            use_case.start_recording(tmp_path, ["RPM"])
            params = [
                VehicleParameter("RPM", "1A F8", 1726.0, "rpm", "7E8", 1.0),
            ]
            use_case.write_row("2026-03-21T00:00:00", params)
            assert use_case.row_count == 1

            use_case.write_row("2026-03-21T00:00:01", params)
            assert use_case.row_count == 2

            use_case.stop_recording()

            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            # header + 2 data rows
            assert len(lines) == 3
        finally:
            os.unlink(tmp_path)

    def test_stop_recording_closes_file(self) -> None:
        """記録停止後は is_recording が False."""
        use_case = RecordDataUseCase()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False,
        ) as tmp:
            tmp_path = tmp.name

        try:
            use_case.start_recording(tmp_path, ["RPM"])
            use_case.stop_recording()
            assert not use_case.is_recording
        finally:
            os.unlink(tmp_path)

    def test_write_row_with_missing_parameter(self) -> None:
        """パラメータが欠損している場合は空文字."""
        use_case = RecordDataUseCase()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False,
        ) as tmp:
            tmp_path = tmp.name

        try:
            use_case.start_recording(tmp_path, ["RPM", "Speed"])
            # RPM のみ、Speed なし
            params = [
                VehicleParameter("RPM", "1A F8", 1726.0, "rpm", "7E8", 1.0),
            ]
            use_case.write_row("2026-03-21T00:00:00", params)
            use_case.stop_recording()

            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            data_row = lines[1].rstrip("\n")
            # "timestamp\t1726.0\t" (Speed is empty)
            assert data_row == "2026-03-21T00:00:00\t1726.0\t"
        finally:
            os.unlink(tmp_path)

    def test_flush_for_comm_loss(self) -> None:
        """通信断時のフラッシュ処理."""
        use_case = RecordDataUseCase()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False,
        ) as tmp:
            tmp_path = tmp.name

        try:
            use_case.start_recording(tmp_path, ["RPM"])
            params = [
                VehicleParameter("RPM", "00 00", 0.0, "rpm", "7E8", 1.0),
            ]
            use_case.write_row("2026-03-21T00:00:00", params)
            use_case.flush_for_comm_loss()

            assert not use_case.is_recording
            # File should exist with data
            assert os.path.exists(tmp_path)
            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2  # header + 1 row
        finally:
            os.unlink(tmp_path)
