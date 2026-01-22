"""
FastAPI application entry point.
"""

from fastapi import FastAPI
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.config import get_settings
from app.modules.observability.logging_config import setup_logging
from app.api import health_router, assistant_router

settings = get_settings()

# Initialize logging
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Easymart AI Assistant Backend (LangChain) - Hybrid Search + Tool Calling",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(assistant_router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.on_event("startup")
async def startup_event():
    print(f"[{settings.APP_NAME}] Starting up...")
    print(f"  Version: {settings.APP_VERSION}")
    print(f"  Environment: {settings.ENVIRONMENT}")
    print(f"  Debug: {settings.DEBUG}")
    print(f"  Host: {settings.HOST}:{settings.PORT}")

    from app.modules.catalog_index.catalog import CatalogIndexer
    from app.modules.catalog_index.sync import get_catalog_sync_service
    from app.modules.catalog_index.indexing.advanced_hybrid_search import get_global_encoder
    
    # PRELOAD embedding model at startup (takes ~3-5 seconds, but only ONCE)
    print("[Embeddings] Preloading sentence transformer model...")
    get_global_encoder()
    print("[Embeddings] Model loaded and cached!")
    
    try:
        indexer = CatalogIndexer()
        product_count = indexer.get_product_count()
        if product_count > 0:
            print(f"[Catalog] Ready with {product_count} products indexed")
        else:
            print("[Catalog] No products indexed. Run: python -m app.modules.catalog_index.load_catalog")
    except Exception as e:
        print(f"[Catalog] Error checking catalog: {e}")

    if settings.CATALOG_SYNC_ENABLED:
        sync_service = get_catalog_sync_service()
        asyncio.create_task(sync_service.run_loop())
        print(f"[CatalogSync] Enabled (interval: {settings.CATALOG_SYNC_INTERVAL_MINUTES} minutes)")

    print(f"[{settings.APP_NAME}] Ready!")


@app.on_event("shutdown")
async def shutdown_event():
    print(f"[{settings.APP_NAME}] Shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
