"""ManageScanCacheUseCase: VIN キーでのキャッシュ管理.

traces: FR-04, FR-04a-f
"""

from __future__ import annotations

import logging
from typing import Any

from src.use_cases.protocols import ScanCacheRepository

logger = logging.getLogger(__name__)

# FR-04e: キャッシュ自動削除日数
CACHE_MAX_AGE_DAYS: int = 90


class ManageScanCacheUseCase:
    """スキャンキャッシュ管理ユースケース.

    VIN をキーとしたスキャン結果のキャッシュ保存・読込・有効期限管理を行う。

    Attributes:
        _cache_repository: キャッシュ永続化インターフェース.
    """

    def __init__(self, cache_repository: ScanCacheRepository) -> None:
        """ManageScanCacheUseCase を初期化する.

        Args:
            cache_repository: キャッシュ永続化インターフェース.
        """
        self._cache_repository = cache_repository

    def save_cache(
        self,
        cache_key: str,
        cache_payload: dict[str, Any],
    ) -> None:
        """スキャン結果をキャッシュに保存する.

        Args:
            cache_key: VIN またはユーザー入力の識別名.
            cache_payload: キャッシュデータ.
        """
        self._cache_repository.save(cache_key, cache_payload)
        logger.info(
            "Scan cache saved",
            extra={"cache_key": cache_key},
        )

    def load_cache(
        self,
        cache_key: str,
    ) -> dict[str, Any] | None:
        """キャッシュを読み込む.

        Args:
            cache_key: VIN またはユーザー入力の識別名.

        Returns:
            キャッシュデータ。存在しない場合は None.
        """
        cached = self._cache_repository.load(cache_key)
        if cached is not None:
            logger.info(
                "Scan cache loaded",
                extra={"cache_key": cache_key},
            )
        else:
            logger.info(
                "No scan cache found",
                extra={"cache_key": cache_key},
            )
        return cached

    def cache_exists(self, cache_key: str) -> bool:
        """キャッシュが存在するかを確認する.

        Args:
            cache_key: VIN またはユーザー入力の識別名.

        Returns:
            存在する場合 True.
        """
        return self._cache_repository.exists(cache_key)

    def invalidate_cache(self, cache_key: str) -> None:
        """キャッシュを無効化する.

        FR-04f: ECU 再スキャンの結果が前回キャッシュと異なる場合に使用。

        Args:
            cache_key: VIN またはユーザー入力の識別名.
        """
        # 空データで上書きして無効化
        self._cache_repository.save(cache_key, {})
        logger.info(
            "Scan cache invalidated",
            extra={"cache_key": cache_key},
        )

    def cleanup_expired_caches(self) -> int:
        """有効期限切れのキャッシュを削除する.

        FR-04e: 90 日間アクセスがないキャッシュファイルを自動削除。

        Returns:
            削除されたキャッシュファイル数.
        """
        deleted_count = self._cache_repository.delete_expired(
            CACHE_MAX_AGE_DAYS,
        )
        logger.info(
            "Expired caches cleaned up",
            extra={
                "deleted_count": deleted_count,
                "max_age_days": CACHE_MAX_AGE_DAYS,
            },
        )
        return deleted_count
