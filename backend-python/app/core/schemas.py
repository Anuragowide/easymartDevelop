"""
Shared Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================================
# Assistant Schemas
# ============================================================================

class MessageRequest(BaseModel):
    """Request schema for /assistant/message endpoint"""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "user123_1234567890",
                "message": "Show me leather wallets",
                "context": {"cart_id": "cart_abc123"}
            }
        }
    }


class MessageResponse(BaseModel):
    """Response schema for /assistant/message endpoint"""
    session_id: str
    message: str = Field(..., description="Assistant response text")
    intent: Optional[str] = Field(default=None, description="Detected user intent")
    products: Optional[List[Dict[str, Any]]] = Field(default=None, description="Product results if applicable")
    suggested_actions: Optional[List[str]] = Field(default=None, description="Suggested follow-up actions")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional response metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "user123_1234567890",
                "message": "I found 3 leather wallets for you...",
                "intent": "product_search",
                "products": [{"sku": "WALLET-001", "title": "Classic Leather Wallet"}],
                "suggested_actions": ["View details", "Add to cart"],
                "metadata": {"search_time_ms": 45}
            }
        }
    }


# ============================================================================
# Product Schemas
# ============================================================================

class ProductSchema(BaseModel):
    """Product information schema"""
    sku: str
    handle: str
    title: str
    price: float
    currency: str
    image_url: Optional[str] = None
    vendor: str
    tags: List[str] = []
    description: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sku": "WALLET-001",
                "handle": "classic-leather-wallet",
                "title": "Classic Leather Wallet",
                "price": 49.99,
                "currency": "USD",
                "image_url": "https://example.com/wallet.jpg",
                "vendor": "Easymart",
                "tags": ["wallet", "leather", "accessories"],
                "description": "Premium leather wallet"
            }
        }
    }


class ProductSpecSchema(BaseModel):
    """Product specification schema"""
    sku: str
    section: str = Field(..., description="Spec section (dimensions, material, etc.)")
    spec_text: str = Field(..., description="Human-readable spec text")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Structured attributes")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sku": "WALLET-001",
                "section": "dimensions",
                "spec_text": "Dimensions: 4.5 x 3.5 x 0.5 inches",
                "attributes": {"length": 4.5, "width": 3.5, "height": 0.5}
            }
        }
    }


# ============================================================================
# Search Schemas
# ============================================================================

class SearchRequest(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "leather wallet",
                "limit": 5,
                "filters": {"price_max": 100}
            }
        }
    }


class SearchResult(BaseModel):
    """Single search result"""
    id: str
    score: float
    content: Dict[str, Any]
    highlights: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response schema"""
    query: str
    results: List[SearchResult]
    total: int
    took_ms: float
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "leather wallet",
                "results": [
                    {
                        "id": "WALLET-001",
                        "score": 0.95,
                        "content": {"title": "Classic Leather Wallet"},
                        "highlights": ["leather", "wallet"]
                    }
                ],
                "total": 3,
                "took_ms": 45.2
            }
        }
    }


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    version: str
    timestamp: datetime
    services: Dict[str, str] = Field(..., description="Status of dependent services")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-12-12T10:30:00Z",
                "services": {
                    "database": "healthy",
                    "vector_index": "healthy",
                    "node_backend": "healthy"
                }
            }
        }
    }


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: str  # Changed to string for JSON serialization
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request parameters",
                "details": {"field": "message", "error": "Field required"},
                "timestamp": "2025-12-12T10:30:00Z"
            }
        }
    }
