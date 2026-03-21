"""JsonScanCacheRepository: ScanCacheRepository Protocol の JSON ファイル実装.

~/.car-diag/cache/ 配下に VIN キーで JSON ファイルを保存・読込する。

traces: FR-04, FR-04a ~ FR-04f
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# キャッシュファイル拡張子
_CACHE_FILE_EXTENSION = ".json"

# キャッシュキーに許可する文字 (英数字・ハイフン・アンダースコア)
_VALID_CACHE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")

# デフォルトのキャッシュディレクトリ
_DEFAULT_CACHE_DIR = Path.home() / ".car-diag" / "cache"


class JsonScanCacheRepository:
    """JSON ベースのスキャンキャッシュリポジトリ.

    VIN をキーとして ~/.car-diag/cache/ 配下に JSON ファイルとして保存する。

    Attributes:
        _cache_dir: キャッシュディレクトリのパス.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        """JsonScanCacheRepository を初期化する.

        Args:
            cache_dir: キャッシュディレクトリ。None の場合はデフォルト.
        """
        self._cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """キャッシュディレクトリを作成する."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.exception(
                "Failed to create cache directory",
                extra={"cache_dir": str(self._cache_dir)},
            )

    def _cache_file_path(self, cache_key: str) -> Path:
        """キャッシュキーからファイルパスを生成する.

        Args:
            cache_key: VIN またはユーザー識別名.

        Returns:
            キャッシュファイルのパス.

        Raises:
            ValueError: キャッシュキーに不正な文字が含まれている場合.
        """
        if not _VALID_CACHE_KEY_PATTERN.match(cache_key):
            msg = (
                f"Invalid cache key: {cache_key!r}. "
                "Only alphanumeric, hyphen, underscore allowed."
            )
            raise ValueError(msg)

        return self._cache_dir / f"{cache_key}{_CACHE_FILE_EXTENSION}"

    def save(self, cache_key: str, cache_payload: dict[str, Any]) -> None:
        """キャッシュを保存する.

        Args:
            cache_key: VIN またはユーザー識別名.
            cache_payload: キャッシュデータ.

        traces: FR-04a
        """
        file_path = self._cache_file_path(cache_key)

        # メタデータを付加
        wrapped_payload: dict[str, Any] = {
            "cache_key": cache_key,
            "saved_at_epoch": time.time(),
            "payload": cache_payload,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as cache_file:
                json.dump(wrapped_payload, cache_file, ensure_ascii=False, indent=2)

            logger.info(
                "Cache saved",
                extra={
                    "cache_key": cache_key,
                    "file_path": str(file_path),
                },
            )
        except OSError:
            logger.exception(
                "Failed to save cache",
                extra={
                    "cache_key": cache_key,
                    "file_path": str(file_path),
                },
            )

    def load(self, cache_key: str) -> dict[str, Any] | None:
        """キャッシュを読み込む.

        Args:
            cache_key: VIN またはユーザー識別名.

        Returns:
            キャッシュデータ。存在しない場合は None.

        traces: FR-04b
        """
        file_path = self._cache_file_path(cache_key)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as cache_file:
                wrapped = json.load(cache_file)

            payload = wrapped.get("payload")
            if not isinstance(payload, dict):
                logger.warning(
                    "Cache payload is not a dict",
                    extra={"cache_key": cache_key},
                )
                return None

            # アクセス時刻を更新 (有効期限計算用)
            self._touch_file(file_path)

            logger.info(
                "Cache loaded",
                extra={
                    "cache_key": cache_key,
                    "file_path": str(file_path),
                },
            )
            return payload

        except (OSError, json.JSONDecodeError):
            logger.exception(
                "Failed to load cache",
                extra={
                    "cache_key": cache_key,
                    "file_path": str(file_path),
                },
            )
            return None

    def delete_expired(self, max_age_days: int) -> int:
        """有効期限切れのキャッシュを削除する.

        Args:
            max_age_days: キャッシュの最大保持日数.

        Returns:
            削除されたキャッシュファイル数.

        traces: FR-04e
        """
        deleted_count = 0
        cutoff_epoch = time.time() - (max_age_days * 86400)

        if not self._cache_dir.exists():
            return 0

        for cache_file in self._cache_dir.glob(f"*{_CACHE_FILE_EXTENSION}"):
            try:
                file_mtime = cache_file.stat().st_mtime
                if file_mtime < cutoff_epoch:
                    cache_file.unlink()
                    deleted_count += 1
                    logger.info(
                        "Expired cache deleted",
                        extra={
                            "file_path": str(cache_file),
                            "file_mtime": file_mtime,
                            "cutoff_epoch": cutoff_epoch,
                        },
                    )
            except OSError:
                logger.exception(
                    "Failed to delete expired cache",
                    extra={"file_path": str(cache_file)},
                )

        logger.info(
            "Expired cache cleanup completed",
            extra={
                "deleted_count": deleted_count,
                "max_age_days": max_age_days,
            },
        )
        return deleted_count

    def exists(self, cache_key: str) -> bool:
        """キャッシュが存在するかを確認する.

        Args:
            cache_key: VIN またはユーザー識別名.

        Returns:
            存在する場合 True.
        """
        try:
            file_path = self._cache_file_path(cache_key)
            return file_path.exists()
        except ValueError:
            return False

    def invalidate(self, cache_key: str) -> None:
        """キャッシュを無効化 (削除) する.

        Args:
            cache_key: VIN またはユーザー識別名.

        traces: FR-04f
        """
        try:
            file_path = self._cache_file_path(cache_key)
            if file_path.exists():
                file_path.unlink()
                logger.info(
                    "Cache invalidated",
                    extra={
                        "cache_key": cache_key,
                        "file_path": str(file_path),
                    },
                )
        except (ValueError, OSError):
            logger.exception(
                "Failed to invalidate cache",
                extra={"cache_key": cache_key},
            )

    @staticmethod
    def _touch_file(file_path: Path) -> None:
        """ファイルのアクセス時刻を更新する.

        Args:
            file_path: 対象ファイルパス.
        """
        try:
            os.utime(file_path, None)
        except OSError:
            pass
