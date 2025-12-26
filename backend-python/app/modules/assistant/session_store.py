"""
Session Store

Manages conversation state and context for each user session.
Tracks shown products, cart items, filters, and conversation history.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid


@dataclass
class SessionContext:
    """
    Conversation context for a user session.
    
    Tracks:
    - Conversation history (messages)
    - Last shown products (for product references like "first one", "second one")
    - Cart items
    - Active filters
    - Last search query
    """
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Conversation history
    messages: List[Dict[str, str]] = field(default_factory=list)
    
    # Product context (for references)
    last_shown_products: List[Dict[str, Any]] = field(default_factory=list)  # Up to 10
    
    # Cart state (if managing locally, otherwise from Node.js)
    cart_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # Search context
    last_query: Optional[str] = None
    active_filters: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata (for storing temporary data like cart actions)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    user_id: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """Add message to history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
    
    def update_shown_products(self, products: List[Dict[str, Any]]):
        """
        Update last shown products.
        Keep up to 10 most recent products for reference resolution.
        """
        self.last_shown_products = products[:10]
        self.last_activity = datetime.now()
    
    def resolve_product_reference(
        self,
        reference: str,
        reference_type: str = "index",
        source: str = "shown"  # "shown" or "cart"
    ) -> Optional[str]:
        """
        Resolve product reference to product ID.
        
        Args:
            reference: Product reference ("1", "first", SKU, or name fragment)
            reference_type: "index", "sku", or "name"
            source: "shown" (last search results) or "cart" (items currently in cart)
        
        Returns:
            Product ID (SKU) or None if not found
        """
        target_list = self.last_shown_products if source == "shown" else self.cart_items
        
        if not target_list:
            # Fallback to other list if preferred is empty
            target_list = self.cart_items if source == "shown" else self.last_shown_products
            if not target_list:
                return None
        
        if reference_type == "index":
            # Convert index to 0-based
            try:
                # Handle common ordinals
                ordinals = {
                    'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
                    'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
                    '1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5,
                    'last': -1, 'previous': -1
                }
                
                ref_lower = reference.lower().strip()
                if ref_lower in ordinals:
                    idx_val = ordinals[ref_lower]
                    if idx_val == -1:
                        idx = len(target_list) - 1
                    else:
                        idx = idx_val - 1
                else:
                    # Handle numeric strings (e.g., "1", "option 2")
                    idx_str = "".join(filter(str.isdigit, reference))
                    if not idx_str:
                        return None
                    idx = int(idx_str) - 1
                
                if 0 <= idx < len(target_list):
                    item = target_list[idx]
                    return item.get("product_id") or item.get("id")
            except (ValueError, IndexError):
                pass
        
        elif reference_type == "sku":
            # Find by SKU
            for item in target_list:
                pid = item.get("product_id") or item.get("id")
                if pid == reference:
                    return pid
        
        elif reference_type == "name":
            # Find by name fragment (case-insensitive)
            reference_lower = reference.lower()
            for item in target_list:
                name = (item.get("name") or item.get("title") or "").lower()
                if reference_lower in name:
                    return item.get("product_id") or item.get("id")
        
        return None
    
    def add_to_cart(self, product_id: str, quantity: int = 1):
        """Add item to cart (local state)"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[ADD_TO_CART] product_id={product_id}, quantity={quantity}")
        
        # Check if already in cart
        for item in self.cart_items:
            if item["product_id"] == product_id or item.get("id") == product_id:
                logger.info(f"[ADD_TO_CART] Found existing item, adding {quantity} to current {item['quantity']}")
                item["quantity"] += quantity
                self.last_activity = datetime.now()
                return
        
        # Add new item
        self.cart_items.append({
            "product_id": product_id,
            "id": product_id, # Store both for consistency
            "quantity": quantity,
            "added_at": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
    
    def remove_from_cart(self, product_id: str):
        """Remove item from cart"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[REMOVE_FROM_CART] product_id={product_id}")
        logger.info(f"[REMOVE_FROM_CART] Current cart_items: {self.cart_items}")
        
        original_count = len(self.cart_items)
        self.cart_items = [
            item for item in self.cart_items
            if item["product_id"] != product_id and item.get("id") != product_id
        ]
        
        if len(self.cart_items) < original_count:
            logger.info(f"[REMOVE_FROM_CART] Successfully removed item. New count: {len(self.cart_items)}")
        else:
            logger.warning(f"[REMOVE_FROM_CART] Item not found in cart: {product_id}")
            
        self.last_activity = datetime.now()
    
    def clear_cart(self):
        """Clear cart"""
        self.cart_items = []
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """
        Check if session has expired due to inactivity.
        
        Args:
            timeout_minutes: Inactivity timeout in minutes
        
        Returns:
            True if expired
        """
        threshold = datetime.now() - timedelta(minutes=timeout_minutes)
        return self.last_activity < threshold


class SessionStore:
    """
    In-memory session store.
    
    Manages multiple user sessions with automatic expiration.
    
    TODO: Replace with Redis or database for production scalability.
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize session store.
        
        Args:
            session_timeout_minutes: Session expiration timeout
        """
        self.sessions: Dict[str, SessionContext] = {}
        self.session_timeout_minutes = session_timeout_minutes
    
    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> SessionContext:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Optional session ID (generates if not provided)
            user_id: Optional user ID to associate with session
        
        Returns:
            SessionContext instance
        
        Example:
            >>> store = SessionStore()
            >>> session = store.get_or_create_session()
            >>> print(session.session_id)
            "abc123..."
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Clean up expired sessions periodically
        self._cleanup_expired_sessions()
        
        # Get or create session
        if session_id not in self.sessions:
            session = SessionContext(
                session_id=session_id,
                user_id=user_id
            )
            self.sessions[session_id] = session
            return session
        
        # Update existing session
        session = self.sessions[session_id]
        session.last_activity = datetime.now()
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
        
        Returns:
            SessionContext or None if not found or expired
        """
        session = self.sessions.get(session_id)
        
        if not session:
            return None
        
        # Check if expired
        if session.is_expired(self.session_timeout_minutes):
            del self.sessions[session_id]
            return None
        
        session.last_activity = datetime.now()
        return session
    
    def delete_session(self, session_id: str):
        """
        Delete session by ID.
        
        Args:
            session_id: Session ID to delete
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def clear_all_sessions(self):
        """Clear all sessions (for testing)"""
        self.sessions.clear()
    
    def get_session_count(self) -> int:
        """Get count of active sessions"""
        return len(self.sessions)
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions from store"""
        expired_ids = [
            session_id
            for session_id, session in self.sessions.items()
            if session.is_expired(self.session_timeout_minutes)
        ]
        
        for session_id in expired_ids:
            del self.sessions[session_id]


# Global session store instance
_session_store = None


def get_session_store() -> SessionStore:
    """
    Get global session store instance (singleton).
    
    Returns:
        Global SessionStore instance
    
    Example:
        >>> store = get_session_store()
        >>> session = store.get_or_create_session()
    """
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
