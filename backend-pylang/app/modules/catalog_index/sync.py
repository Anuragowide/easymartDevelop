"""
Catalog sync service for scheduled indexing from the Node.js adapter.
"""

import asyncio
from datetime import datetime
from typing import Optional

from app.core.config import get_settings
from app.modules.observability.logging_config import get_logger
from app.modules.catalog_index.load_catalog import load_all_products

logger = get_logger(__name__)


class CatalogSyncService:
    def __init__(self):
        self.settings = get_settings()
        self._lock = asyncio.Lock()
        self._last_sync: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

    @property
    def last_sync(self) -> Optional[datetime]:
        return self._last_sync

    async def run_once(self, allow_csv_fallback: Optional[bool] = None) -> bool:
        if self._lock.locked():
            logger.info("[CatalogSync] Sync already in progress; skipping.")
            return False

        allow_csv = self.settings.CATALOG_SYNC_ALLOW_CSV_FALLBACK if allow_csv_fallback is None else allow_csv_fallback

        async with self._lock:
            try:
                await load_all_products(allow_csv_fallback=allow_csv)
                self._last_sync = datetime.utcnow()
                logger.info("[CatalogSync] Sync completed.")
                return True
            except Exception as exc:
                logger.error(f"[CatalogSync] Sync failed: {exc}")
                return False

    async def run_loop(self):
        interval_minutes = max(int(self.settings.CATALOG_SYNC_INTERVAL_MINUTES), 1)
        logger.info(f"[CatalogSync] Starting loop with interval {interval_minutes} minutes.")
        while True:
            await self.run_once()
            await asyncio.sleep(interval_minutes * 60)


_catalog_sync_service: Optional[CatalogSyncService] = None


def get_catalog_sync_service() -> CatalogSyncService:
    global _catalog_sync_service
    if _catalog_sync_service is None:
        _catalog_sync_service = CatalogSyncService()
    return _catalog_sync_service
