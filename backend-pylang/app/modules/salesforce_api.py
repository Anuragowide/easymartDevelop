# backend-pylang/app/api/salesforce_api.py
from fastapi import APIRouter, Request, HTTPException
from app.modules.salesforce_client import SalesforceClient
from app.modules.normalizer import normalize_product
import os, time

router = APIRouter()

client = SalesforceClient()
EXPORT_PAGE_SIZE = int(os.getenv("SALESFORCE_EXPORT_PAGE_SIZE", "50"))
THROTTLE_MS = int(os.getenv("SALESFORCE_EXPORT_THROTTLE_MS", "200"))

@router.post("/internal/salesforce/search")
async def search_endpoint(body: dict):
    query = body.get("query")
    page = body.get("page", 1)
    pageSize = body.get("pageSize", EXPORT_PAGE_SIZE)
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    status, resp = client.post_search({"query": query, "page": page, "pageSize": pageSize})

    # Accept both dict-wrapped responses and raw list responses from Apex
    if isinstance(resp, dict):
        products = resp.get("products") or resp.get("results") or []
        total_size = resp.get("totalSize", len(products))
    elif isinstance(resp, list):
        products = resp
        total_size = len(products)
    else:
        products = []
        total_size = 0

    normalized = [normalize_product(p) for p in products]
    return {"status": status, "totalSize": total_size, "page": page, "pageSize": pageSize, "products": normalized}

@router.get("/internal/salesforce/product/{product_id}")
async def product_endpoint(product_id: str):
    status, resp = client.get_product(product_id)
    if status >= 400:
        raise HTTPException(status_code=status, detail=resp)
    return {"status": status, "product": normalize_product(resp)}

@router.get("/internal/salesforce/export")
async def export_endpoint(page: int = 1, pageSize: int = EXPORT_PAGE_SIZE, query: str | None = None):
    # Simple paginated exporter: caller can loop page param to get all pages.
    payload = {"page": page, "pageSize": pageSize}
    if query:
        payload["query"] = query

    status, resp = client.post_search(payload)

    if isinstance(resp, dict):
        products = resp.get("products") or resp.get("results") or []
        total_size = resp.get("totalSize", len(products))
    elif isinstance(resp, list):
        products = resp
        total_size = len(products)
    else:
        products = []
        total_size = 0

    normalized = [normalize_product(p) for p in products]
    # throttle
    time.sleep(THROTTLE_MS / 1000.0)
    return {"page": page, "pageSize": pageSize, "totalSize": total_size, "products": normalized}