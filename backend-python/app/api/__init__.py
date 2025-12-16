"""
API route handlers.
"""

from .health_api import router as health_router
from .assistant_api import router as assistant_router

__all__ = ["health_router", "assistant_router"]
