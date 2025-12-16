"""
FastAPI dependency injection functions.
"""

from fastapi import Depends, HTTPException, status
from typing import Optional
from app.core.config import get_settings, Settings
from app.modules.catalog_index.catalog import CatalogIndexer

# Global catalog instance
_catalog_indexer: Optional[CatalogIndexer] = None


def get_catalog_indexer() -> CatalogIndexer:
    """Get or create catalog indexer instance"""
    global _catalog_indexer
    if _catalog_indexer is None:
        _catalog_indexer = CatalogIndexer()
    return _catalog_indexer


def get_current_settings() -> Settings:
    """Dependency to get current settings"""
    return get_settings()


def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify API key for protected endpoints.
    TODO: Implement actual API key verification.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # TODO: Verify against stored API keys
    return True


def get_session_id(session_id: str) -> str:
    """
    Validate and return session ID.
    """
    if not session_id or len(session_id) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )
    return session_id
