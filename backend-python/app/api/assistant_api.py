"""
Assistant API endpoints.
Main chatbot interaction endpoint with Easymart Assistant integration.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from app.core.schemas import MessageRequest, MessageResponse, ErrorResponse
from app.core.dependencies import get_session_id
from app.core.exceptions import EasymartException
from app.modules.assistant import get_assistant_handler, AssistantRequest
from app.modules.assistant.session_store import get_session_store
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/message", response_model=MessageResponse)
async def handle_message(
    request: MessageRequest
):
    """
    Main assistant endpoint with Easymart AI integration.
    
    Processes user message through:
    1. Session management
    2. Intent detection
    3. LLM-based conversation (Mistral-7B)
    4. Function calling (8 tools)
    5. Response generation
    
    Returns:
        MessageResponse with assistant message, products, cart summary
    """
    
    start_time = time.time()
    
    try:
        # Get assistant handler
        handler = get_assistant_handler()
        
        # Create assistant request
        assistant_request = AssistantRequest(
            message=request.message,
            session_id=request.session_id,
            user_id=request.context.get("user_id") if request.context else None
        )
        
        # Handle message
        assistant_response = await handler.handle_message(assistant_request)
        
        # Extract intent from metadata
        intent = assistant_response.metadata.get("intent", "general_query")
        
        # Build suggested actions based on intent
        suggested_actions = _get_suggested_actions(intent, assistant_response.products)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return MessageResponse(
            session_id=assistant_response.session_id,
            message=assistant_response.message,
            intent=intent,
            products=[
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "price": p.get("price"),
                    "description": p.get("description", ""),
                    "image_url": p.get("image_url"),
                    "url": p.get("product_url") or f"/products/{p.get('id')}"
                }
                for p in assistant_response.products
            ] if assistant_response.products else None,
            suggested_actions=suggested_actions,
            metadata={
                "processing_time_ms": round(elapsed_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "function_calls": assistant_response.metadata.get("function_calls_made", 0),
                "cart_items": assistant_response.cart_summary.get("item_count") if assistant_response.cart_summary else 0
            }
        )
        
    except EasymartException as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=type(e).__name__,
                message=e.message,
                details=e.details,
                timestamp=datetime.utcnow().isoformat()
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="InternalServerError",
                message="An unexpected error occurred processing your message",
                details={"error": str(e)},
                timestamp=datetime.utcnow().isoformat()
            ).model_dump()
        )


def _get_suggested_actions(intent: str, products: list) -> list:
    """
    Get suggested actions based on intent and context.
    
    Args:
        intent: Detected intent
        products: Products in response (if any)
    
    Returns:
        List of suggested action strings
    """
    # Add "search_results" action to trigger product card display
    actions = []
    
    if intent == "product_search":
        if products:
            # Trigger product cards in frontend
            actions.append("search_results")
            actions.extend(["Ask about specifications", "Add to cart", "Compare products", "Refine search"])
        else:
            actions.extend(["Try different keywords", "Browse categories", "Get help"])
    
    elif intent == "product_spec_qa":
        actions.extend(["Add to cart", "Compare with others", "Check availability", "View similar products"])
    
    elif intent in ["cart_add", "cart_update_quantity"]:
        actions.extend(["View cart", "Continue shopping", "Proceed to checkout", "Apply discount"])
    
    elif intent == "cart_show":
        actions.extend(["Update quantities", "Remove items", "Proceed to checkout", "Continue shopping"])
    
    elif intent in ["return_policy", "shipping_info", "payment_options", "warranty_info"]:
        actions.extend(["Contact support", "Browse products", "Check order status"])
    
    elif intent in ["contact_info", "store_hours", "store_location"]:
        actions.extend(["Call us", "Visit showroom", "Browse products", "Get shipping info"])
    
    else:
        actions.extend(["Search products", "View policies", "Contact us", "Get help"])
    
    return actions


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Get session information.
    Returns conversation history and context.
    """
    try:
        from app.modules.assistant import get_session_store
        
        store = get_session_store()
        session = store.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return {
            "session_id": session.session_id,
            "status": "active",
            "message_count": len(session.messages),
            "cart_items": len(session.cart_items),
            "last_activity": session.last_activity.isoformat(),
            "created_at": session.created_at.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving session: {str(e)}")


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear session data and conversation history.
    """
    try:
        handler = get_assistant_handler()
        await handler.clear_session(session_id)
        
        return {
            "session_id": session_id,
            "status": "cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")


@router.get("/greeting")
async def get_greeting(session_id: str = Depends(get_session_id)):
    """
    Get welcome greeting for new conversation.
    """
    try:
        handler = get_assistant_handler()
        response = await handler.get_greeting(session_id=session_id)
        
        return {
            "session_id": response.session_id,
            "message": response.message,
            "suggested_actions": ["Search products", "View policies", "Contact us", "Get shipping info"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting greeting: {str(e)}")


@router.post("/cart")
async def update_cart_endpoint(request: Request):
    """
    Add/update/remove items from cart
    """
    try:
        body = await request.json()
        product_id = body.get("product_id")
        quantity = body.get("quantity", 1)
        action = body.get("action", "add")  # add, remove, set
        session_id = body.get("session_id")
        
        logger.info(f"Cart request: product_id={product_id}, quantity={quantity}, action={action}, session_id={session_id}")
        
        if not product_id:
            raise ValueError("product_id is required")
        
        if not session_id:
            raise ValueError("session_id is required")
        
        # Get the tools instance
        from app.modules.assistant.tools import EasymartAssistantTools
        tools = EasymartAssistantTools()
        
        # Call update_cart method
        result = await tools.update_cart(
            action=action,
            product_id=product_id,
            quantity=quantity,
            session_id=session_id
        )
        
        logger.info(f"Cart update result: {result}")
        
        # Get updated cart from session
        from app.modules.assistant.session_store import get_session_store
        from app.core.dependencies import get_catalog_indexer
        
        session_store = get_session_store()
        session = session_store.get_session(session_id)
        catalog = get_catalog_indexer()
        
        # Build cart items from session with product details
        cart_items = []
        if session and session.cart_items:
            for item in session.cart_items:
                pid = item.get("product_id")
                # Fetch product details from catalog
                product = catalog.getProductById(pid)
                if product:
                    cart_items.append({
                        "product_id": pid,
                        "id": pid,  # Add 'id' for frontend compatibility
                        "title": product.get("title") or product.get("name", "Unknown Product"),  # Frontend expects 'title'
                        "name": product.get("title") or product.get("name", "Unknown Product"),
                        "price": product.get("price", 0.0),
                        "image_url": product.get("image_url", ""),
                        "image": product.get("image_url", ""),  # Frontend expects 'image'
                        "inventory_quantity": product.get("inventory_quantity", 0),
                        "quantity": item.get("quantity", 1),
                        "added_at": item.get("added_at")
                    })
                else:
                    # Product not found, keep basic info
                    cart_items.append({
                        "product_id": pid,
                        "id": pid,
                        "title": "Unknown Product",
                        "quantity": item.get("quantity", 1)
                    })
        
        # Calculate total
        total = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart_items)
        
        response_data = {
            "success": True,
            "message": result.get("message", "Cart updated"),
            "cart": {
                "items": cart_items,
                "item_count": len(cart_items),
                "total": total
            }
        }
        
        logger.info(f"Returning cart response: {response_data}")
        return response_data
        
    except Exception as e:
        logger.error(f"Cart update error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/cart")
async def get_cart_endpoint(session_id: str):
    """
    Get cart contents for a session without triggering LLM.
    Direct session store query for efficient cart retrieval.
    """
    try:
        logger.info(f"Getting cart for session: {session_id}")
        
        # Get session from session store
        from app.core.dependencies import get_catalog_indexer
        
        session_store = get_session_store()
        session = session_store.get_session(session_id)
        catalog = get_catalog_indexer()
        
        # Build cart items with product details
        cart_items = []
        if session and session.cart_items:
            for item in session.cart_items:
                pid = item.get("product_id")
                # Fetch product details from catalog
                product = catalog.getProductById(pid)
                if product:
                    cart_items.append({
                        "product_id": pid,
                        "id": pid,  # Add 'id' for frontend compatibility
                        "title": product.get("title") or product.get("name", "Unknown Product"),  # Frontend expects 'title'
                        "name": product.get("title") or product.get("name", "Unknown Product"),
                        "price": product.get("price", 0.0),
                        "image_url": product.get("image_url", ""),
                        "image": product.get("image_url", ""),  # Frontend expects 'image'
                        "inventory_quantity": product.get("inventory_quantity", 0),
                        "quantity": item.get("quantity", 1),
                        "added_at": item.get("added_at")
                    })
                else:
                    # Product not found, keep basic info
                    cart_items.append({
                        "product_id": pid,
                        "id": pid,
                        "title": "Unknown Product",
                        "quantity": item.get("quantity", 1)
                    })
        
        # Calculate total
        total = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart_items)
        
        response_data = {
            "success": True,
            "cart": {
                "items": cart_items,
                "item_count": len(cart_items),
                "total": total
            }
        }
        
        logger.info(f"Returning cart with {len(cart_items)} items")
        return response_data
        
    except Exception as e:
        logger.error(f"Get cart error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
