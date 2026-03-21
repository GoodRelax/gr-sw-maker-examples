"""ManageScanCacheUseCase のテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.use_cases.manage_scan_cache import (
    CACHE_MAX_AGE_DAYS,
    ManageScanCacheUseCase,
)


class TestManageScanCacheUseCase:
    """ManageScanCacheUseCase のテスト."""

    def test_save_and_load_cache(self) -> None:
        """キャッシュの保存と読込."""
        cache_repo = MagicMock()
        cache_repo.load.return_value = {"ecus": ["7E0"]}

        use_case = ManageScanCacheUseCase(cache_repo)
        use_case.save_cache("JT12345", {"ecus": ["7E0"]})
        cache_repo.save.assert_called_once_with("JT12345", {"ecus": ["7E0"]})

        result = use_case.load_cache("JT12345")
        assert result == {"ecus": ["7E0"]}

    def test_load_nonexistent_cache(self) -> None:
        """存在しないキャッシュの読込は None."""
        cache_repo = MagicMock()
        cache_repo.load.return_value = None

        use_case = ManageScanCacheUseCase(cache_repo)
        result = use_case.load_cache("UNKNOWN_VIN")

        assert result is None

    def test_cache_exists(self) -> None:
        """キャッシュ存在確認."""
        cache_repo = MagicMock()
        cache_repo.exists.return_value = True

        use_case = ManageScanCacheUseCase(cache_repo)
        assert use_case.cache_exists("JT12345") is True

    def test_invalidate_cache(self) -> None:
        """キャッシュ無効化は空データで上書き."""
        cache_repo = MagicMock()

        use_case = ManageScanCacheUseCase(cache_repo)
        use_case.invalidate_cache("JT12345")

        cache_repo.save.assert_called_once_with("JT12345", {})

    def test_cleanup_expired_caches(self) -> None:
        """期限切れキャッシュの削除."""
        cache_repo = MagicMock()
        cache_repo.delete_expired.return_value = 3

        use_case = ManageScanCacheUseCase(cache_repo)
        deleted = use_case.cleanup_expired_caches()

        assert deleted == 3
        cache_repo.delete_expired.assert_called_once_with(CACHE_MAX_AGE_DAYS)
