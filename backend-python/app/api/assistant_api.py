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
        
        # Check if there was a cart action
        session_store = get_session_store()
        session = session_store.get_or_create_session(assistant_response.session_id)
        cart_action = session.metadata.get("last_cart_action")
        
        # Store cart action in metadata instead of suggested_actions
        response_metadata = {
            "processing_time_ms": 0,  # Will be updated below
            "timestamp": datetime.utcnow().isoformat(),
            "function_calls": assistant_response.metadata.get("function_calls_made", 0),
        }
        
        # Map cart action to actions field for frontend
        actions = []
        if cart_action:
            actions.append(cart_action)
            # Clear the cart action after including it
            session.metadata.pop("last_cart_action", None)
        
        # Debug: Log products being returned
        logger.info(f"[API] Assistant response has {len(assistant_response.products) if assistant_response.products else 0} products")
        if assistant_response.products:
            logger.info(f"[API] Product names: {[p.get('name', 'UNNAMED') for p in assistant_response.products[:3]]}")
        
        # Build product list for response
        products_list = [
            {
                "id": p.get("id") if isinstance(p, dict) else None,
                "name": p.get("name") if isinstance(p, dict) else "Product",
                "price": p.get("price") if isinstance(p, dict) else 0.0,
                "description": p.get("description", "") if isinstance(p, dict) else "",
                "image_url": p.get("image_url") if isinstance(p, dict) else None,
                "url": (p.get("product_url") or f"/products/{p.get('id')}") if isinstance(p, dict) else "#"
            }
            for p in assistant_response.products
            if p is not None # Filter out None products
        ] if assistant_response.products else []
        
        logger.info(f"[API] Returning {len(products_list)} products in response")
        if products_list:
            logger.info(f"[API] First product: id={products_list[0]['id']}, name={products_list[0]['name']}")
        
        return MessageResponse(
            session_id=assistant_response.session_id,
            message=assistant_response.message,
            intent=intent,
            products=products_list if products_list else None,
            actions=actions if actions else None,
            suggested_actions=suggested_actions,
            metadata=response_metadata
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
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error handling message: {str(e)}\n{error_detail}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="InternalServerError",
                message="An unexpected error occurred processing your message",
                details={"error": str(e), "traceback": error_detail if not False else "Hidden"},
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
    actions = []
    
    # CRITICAL: Always add "search_results" when products exist
    # This triggers the product card display in the frontend via Node middleware
    if products and len(products) > 0:
        actions.append("search_results")
    
    # Add context-specific suggested actions
    if intent == "product_search":
        if products:
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
        
        if not product_id and action not in ["view", "clear"]:
            raise ValueError(f"product_id is required for action: {action}")
        
        if not session_id:
            raise ValueError("session_id is required")
        
        # Get the tools instance
        from app.modules.assistant.tools import get_assistant_tools
        tools = get_assistant_tools()
        
        # Call update_cart method with skip_sync=True to prevent recursion
        # since this endpoint is called BY the Node.js backend
        result = await tools.update_cart(
            action=action,
            product_id=product_id,
            quantity=quantity,
            session_id=session_id,
            skip_sync=True
        )
        
        logger.info(f"Cart update result success: {result.get('success')}")
        
        if not result.get("success"):
            return JSONResponse(
                status_code=400,
                content=result
            )

        return result
        
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
        
        # Get the tools instance
        from app.modules.assistant.tools import get_assistant_tools
        tools = get_assistant_tools()
        
        # Call update_cart with 'view' action
        result = await tools.update_cart(
            action="view",
            session_id=session_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Get cart error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
