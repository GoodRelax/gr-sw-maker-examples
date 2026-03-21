"""JsonScanCacheRepository のユニットテスト.

tmpdir を使用してキャッシュの保存/読込/削除をテストする。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.adapters.scan_cache_repository import JsonScanCacheRepository


@pytest.fixture()
def cache_dir(tmp_path: Path) -> Path:
    """テスト用キャッシュディレクトリ."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture()
def repository(cache_dir: Path) -> JsonScanCacheRepository:
    """JsonScanCacheRepository フィクスチャ."""
    return JsonScanCacheRepository(cache_dir=cache_dir)


class TestSave:
    """キャッシュ保存のテスト."""

    def test_save_creates_json_file(
        self,
        cache_dir: Path,
        repository: JsonScanCacheRepository,
    ) -> None:
        """保存するとJSON ファイルが作成される."""
        repository.save("TEST_VIN_123", {"ecus": ["7E0", "7E1"]})

        cache_file = cache_dir / "TEST_VIN_123.json"
        assert cache_file.exists()

        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["cache_key"] == "TEST_VIN_123"
        assert data["payload"]["ecus"] == ["7E0", "7E1"]

    def test_save_overwrites_existing(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """同じキーで保存すると上書きされる."""
        repository.save("VIN_A", {"version": 1})
        repository.save("VIN_A", {"version": 2})

        loaded = repository.load("VIN_A")
        assert loaded is not None
        assert loaded["version"] == 2


class TestLoad:
    """キャッシュ読込のテスト."""

    def test_load_returns_payload(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """保存したデータを読み込める."""
        payload = {"ecus": ["7E0"], "did_count": 42}
        repository.save("VIN_LOAD", payload)

        loaded = repository.load("VIN_LOAD")
        assert loaded is not None
        assert loaded["ecus"] == ["7E0"]
        assert loaded["did_count"] == 42

    def test_load_nonexistent_returns_none(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """存在しないキーは None を返す."""
        assert repository.load("NONEXISTENT") is None

    def test_load_corrupted_file_returns_none(
        self,
        cache_dir: Path,
        repository: JsonScanCacheRepository,
    ) -> None:
        """破損ファイルは None を返す."""
        corrupted_file = cache_dir / "CORRUPTED.json"
        corrupted_file.write_text("{invalid json", encoding="utf-8")

        assert repository.load("CORRUPTED") is None


class TestDeleteExpired:
    """有効期限切れキャッシュ削除のテスト."""

    def test_delete_expired_removes_old_files(
        self,
        cache_dir: Path,
        repository: JsonScanCacheRepository,
    ) -> None:
        """期限切れファイルが削除される."""
        # 古いキャッシュファイルを作成
        old_file = cache_dir / "OLD_VIN.json"
        old_file.write_text('{"cache_key":"OLD_VIN","payload":{}}', encoding="utf-8")

        # 91日前のタイムスタンプに設定
        old_epoch = time.time() - (91 * 86400)
        import os
        os.utime(old_file, (old_epoch, old_epoch))

        deleted = repository.delete_expired(max_age_days=90)
        assert deleted == 1
        assert not old_file.exists()

    def test_delete_expired_keeps_recent_files(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """最近のファイルは削除されない."""
        repository.save("RECENT_VIN", {"data": "fresh"})

        deleted = repository.delete_expired(max_age_days=90)
        assert deleted == 0
        assert repository.exists("RECENT_VIN")


class TestExists:
    """キャッシュ存在確認のテスト."""

    def test_exists_returns_true(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """保存済みキーは True を返す."""
        repository.save("EXISTS_VIN", {})
        assert repository.exists("EXISTS_VIN") is True

    def test_exists_returns_false(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """未保存キーは False を返す."""
        assert repository.exists("NOT_EXISTS") is False


class TestInvalidate:
    """キャッシュ無効化のテスト."""

    def test_invalidate_removes_file(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """無効化するとファイルが削除される."""
        repository.save("INVAL_VIN", {"data": "test"})
        assert repository.exists("INVAL_VIN")

        repository.invalidate("INVAL_VIN")
        assert not repository.exists("INVAL_VIN")


class TestCacheKeyValidation:
    """キャッシュキーバリデーションのテスト."""

    def test_invalid_key_raises_error(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """不正なキーはエラーを発生させる."""
        with pytest.raises(ValueError, match="Invalid cache key"):
            repository.save("../evil", {})

    def test_valid_keys_accepted(
        self,
        repository: JsonScanCacheRepository,
    ) -> None:
        """有効なキーは受け入れられる."""
        repository.save("WBAPH5C55BA123456", {"vin": True})
        repository.save("my-car-2024", {"custom": True})
        repository.save("test_key_123", {"underscore": True})
        assert repository.exists("WBAPH5C55BA123456")
