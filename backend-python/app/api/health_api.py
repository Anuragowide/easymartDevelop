"""
Health check API endpoints.
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from app.core.schemas import HealthResponse
from app.core.config import get_settings, Settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Health check endpoint.
    Returns service status and dependent service health.
    """
    
    # Check database
    db_status = "healthy"
    try:
        from app.modules.catalog_index.indexing import DatabaseManager
        db = DatabaseManager()
        # Database is accessible if no error
    except Exception as e:
        db_status = "unhealthy"
    
    # Check vector index
    vector_status = "healthy"
    try:
        from app.modules.catalog_index.config import index_config
        # Check if chroma directory exists
        if not index_config.chroma_dir.exists():
            vector_status = "degraded"
    except Exception as e:
        vector_status = "unhealthy"
    
    # Check Node.js backend (optional)
    node_status = "unknown"
    try:
        import httpx
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{settings.NODE_BACKEND_URL}/health")
            node_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        node_status = "degraded"
    
    # Determine overall status
    services = {
        "database": db_status,
        "vector_index": vector_status,
        "node_backend": node_status
    }
    
    overall_status = "healthy"
    if "unhealthy" in services.values():
        overall_status = "degraded" if db_status == "healthy" else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        services=services
    )


@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"status": "pong", "timestamp": datetime.utcnow()}
