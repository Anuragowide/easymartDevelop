"""
Assistant API endpoints.
Main chatbot interaction endpoint with Easymart Assistant integration.
"""

from fastapi import APIRouter, HTTPException, Depends
from app.core.schemas import MessageRequest, MessageResponse, ErrorResponse
from app.core.dependencies import get_session_id
from app.core.exceptions import EasymartException
from app.modules.assistant import get_assistant_handler, AssistantRequest
from datetime import datetime
import time

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
                    "url": p.get("product_url", f"/products/{p.get('id')}")  # Use actual Shopify URL
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
