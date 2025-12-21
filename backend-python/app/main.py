"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api import health_router, assistant_router
from app.modules.catalog_index.load_catalog import load_all_products

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Easymart AI Assistant Backend - Hybrid BM25 + Vector Search with LLM Integration",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(health_router)
app.include_router(assistant_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print(f"[{settings.APP_NAME}] Starting up...")
    print(f"  Version: {settings.APP_VERSION}")
    print(f"  Environment: {settings.ENVIRONMENT}")
    print(f"  Debug: {settings.DEBUG}")
    print(f"  Host: {settings.HOST}:{settings.PORT}")
    
    # Trigger auto-indexing
    # Note: We await this to ensure catalog is ready before accepting requests.
    # If this takes too long, we should move it to a BackgroundTask or separate thread.
    try:
        await load_all_products()
    except Exception as e:
        print(f"[{settings.APP_NAME}] ⚠️ Auto-indexing failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print(f"[{settings.APP_NAME}] Shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
