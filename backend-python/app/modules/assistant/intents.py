"""
Intent definitions for Easymart furniture assistant.
Extended with store policy and information intents.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported intent types for Easymart"""
    
    # Product-related intents
    PRODUCT_SEARCH = "product_search"
    PRODUCT_SPEC_QA = "product_spec_qa"
    PRODUCT_COMPARE = "product_compare"
    PRODUCT_AVAILABILITY = "product_availability"
    FIND_SIMILAR = "find_similar"
    
    # Cart-related intents
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    CART_CLEAR = "cart_clear"
    CART_SHOW = "cart_show"
    CART_UPDATE_QUANTITY = "cart_update_quantity"
    
    # Store policy intents
    RETURN_POLICY = "return_policy"
    SHIPPING_INFO = "shipping_info"
    PAYMENT_OPTIONS = "payment_options"
    WARRANTY_INFO = "warranty_info"
    PROMOTIONS = "promotions"
    
    # Contact & Support intents
    CONTACT_INFO = "contact_info"
    STORE_HOURS = "store_hours"
    STORE_LOCATION = "store_location"
    
    # General intents
    GREETING = "greeting"
    GENERAL_HELP = "general_help"
    OUT_OF_SCOPE = "out_of_scope"


class ProductSearchIntent(BaseModel):
    """Product search intent for furniture"""
    intent: IntentType = IntentType.PRODUCT_SEARCH
    query_text: str = Field(..., description="User's search query")
    
    # Furniture-specific filters
    category: Optional[str] = Field(
        None, 
        description="Furniture category: chairs, tables, stools, shelves, lockers, desks, sofas, beds, storage"
    )
    room_type: Optional[str] = Field(
        None,
        description="Room type: living_room, bedroom, office, dining_room, kitchen, outdoor"
    )
    material: Optional[str] = Field(
        None,
        description="Material: wood, metal, fabric, leather, glass, rattan"
    )
    color: Optional[str] = Field(None, description="Color preference")
    style: Optional[str] = Field(
        None,
        description="Style: modern, contemporary, industrial, minimalist, rustic, scandinavian"
    )
    price_min: Optional[float] = Field(None, description="Minimum price")
    price_max: Optional[float] = Field(None, description="Maximum price")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "intent": "product_search",
                "query_text": "ergonomic office chair",
                "category": "chairs",
                "room_type": "office",
                "material": "fabric",
                "price_max": 500.0,
                "style": "modern"
            }
        }
    }


class ProductSpecQAIntent(BaseModel):
    """Product specification question intent"""
    intent: IntentType = IntentType.PRODUCT_SPEC_QA
    product_reference: Optional[str] = Field(None, description="Product reference")
    reference_type: Optional[str] = Field(None, description="sku|index|name")
    question: str = Field(..., description="The specification question")


class CartAddIntent(BaseModel):
    """Add item to cart"""
    intent: IntentType = IntentType.CART_ADD
    product_reference: str = Field(..., description="Product reference")
    quantity: int = Field(default=1, ge=1, description="Quantity")
    reference_type: str = Field(..., description="sku|index|name")


class CartRemoveIntent(BaseModel):
    """Remove item from cart"""
    intent: IntentType = IntentType.CART_REMOVE
    product_reference: str = Field(..., description="Product reference")
    quantity: Optional[int] = Field(None, description="Quantity to remove")
    reference_type: str = Field(..., description="sku|index|name")


class CartShowIntent(BaseModel):
    """Show cart contents"""
    intent: IntentType = IntentType.CART_SHOW


class ReturnPolicyIntent(BaseModel):
    """Return policy question"""
    intent: IntentType = IntentType.RETURN_POLICY


class ShippingInfoIntent(BaseModel):
    """Shipping information question"""
    intent: IntentType = IntentType.SHIPPING_INFO
    postcode: Optional[str] = Field(None, description="Postcode for delivery estimate")


class ContactInfoIntent(BaseModel):
    """Contact information request"""
    intent: IntentType = IntentType.CONTACT_INFO


class PromotionsIntent(BaseModel):
    """Promotions and discounts request"""
    intent: IntentType = IntentType.PROMOTIONS


# Union type for all intents
IntentData = (
    ProductSearchIntent | CartAddIntent | CartRemoveIntent | CartShowIntent | 
    ProductSpecQAIntent | ReturnPolicyIntent | ShippingInfoIntent | ContactInfoIntent |
    PromotionsIntent
)
