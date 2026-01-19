"""
Session Store

Manages conversation state and context for each user session.
Tracks shown products, cart items, filters, and conversation history.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import pickle
from pathlib import Path
import logging
from app.core.config import get_settings

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None

logger = logging.getLogger(__name__)

# Session persistence
SESSIONS_FILE = Path("data/sessions.pkl")


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
    current_product: Optional[Dict[str, Any]] = None  # The product user is currently asking about
    
    # Cart state (if managing locally, otherwise from Node.js)
    cart_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # Search context
    last_query: Optional[str] = None
    active_filters: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata (for storing temporary data like cart actions)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Pending clarification state
    pending_clarification: Optional[Dict[str, Any]] = None
    
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

    def to_langchain_messages(self, limit: int = 10):
        """
        Convert stored messages to LangChain message objects.

        Args:
            limit: Max number of recent messages to include
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        msgs = []
        for msg in self.messages[-limit:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                msgs.append(AIMessage(content=content))
            elif role == "system":
                msgs.append(SystemMessage(content=content))
        return msgs
    
    def update_shown_products(self, products: List[Dict[str, Any]]):
        """
        Update last shown products.
        Keep up to 10 most recent products for reference resolution.
        """
        # If we already have products and we're adding a single one (e.g. from specs),
        # prepend it to the list instead of replacing the whole list
        if len(products) == 1 and self.last_shown_products:
            new_product = products[0]
            # Check if it's already there
            exists = any(p.get("id") == new_product.get("id") for p in self.last_shown_products)
            if not exists:
                self.last_shown_products = (products + self.last_shown_products)[:10]
        else:
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
    
    def add_to_cart(
        self,
        product_id: str,
        quantity: int = 1,
        source: str = "unknown",
        price: Optional[float] = None,
        name: Optional[str] = None,
        image_url: Optional[str] = None
    ):
        """Add item to cart (local state)
        
        Args:
            product_id: Product SKU/ID to add
            quantity: Quantity to add
            source: Source of the add request ('button', 'assistant', 'unknown')
        """
        import logging
        from datetime import datetime, timedelta
        logger = logging.getLogger(__name__)
        
        logger.info(f"[SESSION.ADD_TO_CART] ======= ADDING TO SESSION CART =======")
        logger.info(f"[SESSION.ADD_TO_CART] product_id={product_id}, quantity={quantity}, source={source}")
        logger.info(f"[SESSION.ADD_TO_CART] Current cart BEFORE add: {self.cart_items}")
        
        # Check if already in cart
        for item in self.cart_items:
            if item["product_id"] == product_id or item.get("id") == product_id:
                # DEBOUNCE: Check if item was just added in last 5 seconds
                # This prevents double-add from user clicking button AND typing "add this"
                last_added = item.get("added_at")
                if last_added:
                    try:
                        last_added_time = datetime.fromisoformat(last_added)
                        time_since_add = datetime.now() - last_added_time
                        if time_since_add < timedelta(seconds=5):
                            logger.warning(f"[SESSION.ADD_TO_CART] DEBOUNCE: Skipping add - item was just added {time_since_add.total_seconds():.1f}s ago")
                            logger.info(f"[SESSION.ADD_TO_CART] ======= END SESSION ADD (DEBOUNCED) =======")
                            return
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Could not parse last_added timestamp: {e}")
                
                # Add to existing quantity
                logger.info(f"[SESSION.ADD_TO_CART] Found existing item, adding {quantity} to current {item['quantity']}")
                item["quantity"] += quantity
                if price is not None:
                    item["price"] = price
                if name:
                    item["name"] = name
                if image_url:
                    item["image_url"] = image_url
                item["added_at"] = datetime.now().isoformat()  # Update timestamp
                self.last_activity = datetime.now()
                logger.info(f"[SESSION.ADD_TO_CART] Updated cart AFTER add: {self.cart_items}")
                logger.info(f"[SESSION.ADD_TO_CART] ======= END SESSION ADD =======")
                return
        
        # Add new item
        logger.info(f"[SESSION.ADD_TO_CART] Adding new item to cart")
        self.cart_items.append({
            "product_id": product_id,
            "id": product_id, # Store both for consistency
            "quantity": quantity,
            "price": price,
            "name": name,
            "image_url": image_url,
            "added_at": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
        logger.info(f"[SESSION.ADD_TO_CART] Cart AFTER adding new item: {self.cart_items}")
        logger.info(f"[SESSION.ADD_TO_CART] ======= END SESSION ADD =======")
    
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
    
    def set_pending_clarification(
        self,
        vague_type: str,
        partial_entities: Dict[str, Any],
        original_query: str
    ):
        """
        Set pending clarification state.
        
        Args:
            vague_type: Type of vague query
            partial_entities: Partial information extracted
            original_query: Original vague query
        """
        self.pending_clarification = {
            "vague_type": vague_type,
            "partial_entities": partial_entities,
            "original_query": original_query,
            "clarification_count": 0,
            "timestamp": datetime.now()
        }
        self.last_activity = datetime.now()
    
    def get_pending_clarification(self) -> Optional[Dict[str, Any]]:
        """Get pending clarification state."""
        return self.pending_clarification
    
    def increment_clarification_count(self):
        """Increment clarification count."""
        if self.pending_clarification:
            self.pending_clarification["clarification_count"] += 1
            self.last_activity = datetime.now()
    
    def clear_pending_clarification(self):
        """Clear pending clarification state."""
        self.pending_clarification = None
        self.last_activity = datetime.now()


class SessionStore:
    """
    In-memory session store with file persistence backup.
    
    Manages multiple user sessions with automatic expiration.
    Sessions are saved to disk periodically to prevent data loss on restart.
    
    TODO: Migrate to Redis for production scalability and multi-instance support.
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize session store.
        
        Args:
            session_timeout_minutes: Session expiration timeout
        """
        self.sessions: Dict[str, SessionContext] = {}
        self.session_timeout_minutes = session_timeout_minutes
        self._load_sessions()
    
    def _save_sessions(self):
        """Persist sessions to disk to prevent data loss on restart"""
        try:
            SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SESSIONS_FILE, 'wb') as f:
                pickle.dump(self.sessions, f)
            logger.info(f"[SESSION_STORE] Saved {len(self.sessions)} sessions to disk")
        except Exception as e:
            logger.error(f"[SESSION_STORE] Failed to save sessions: {e}", exc_info=True)
    
    def _load_sessions(self):
        """Load sessions from disk on startup"""
        try:
            if SESSIONS_FILE.exists():
                with open(SESSIONS_FILE, 'rb') as f:
                    self.sessions = pickle.load(f)
                logger.info(f"[SESSION_STORE] Loaded {len(self.sessions)} sessions from disk")
            else:
                logger.info("[SESSION_STORE] No existing sessions file found, starting fresh")
        except Exception as e:
            logger.error(f"[SESSION_STORE] Failed to load sessions: {e}, starting fresh", exc_info=True)
            self.sessions = {}
    
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
                user_id=user_id,
                metadata={"user_preferences": {}, "topic_history": []}
            )
            self.sessions[session_id] = session
            logger.info(f"Created new session: {session_id}")
            
            # Save to disk for persistence
            self._save_sessions()
            
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


class RedisSessionStore:
    """
    Redis-backed session store for production deployments.
    Stores SessionContext objects as pickled blobs with TTL.
    """

    def __init__(self, redis_url: str, session_timeout_minutes: int = 30):
        if not redis:
            raise RuntimeError("redis package is required for RedisSessionStore")
        self.session_timeout_minutes = session_timeout_minutes
        self.ttl_seconds = session_timeout_minutes * 60
        self.client = redis.Redis.from_url(redis_url, decode_responses=False)

    def _make_key(self, session_id: str) -> str:
        return f"easymart:session:{session_id}"

    def _save_session(self, session: SessionContext):
        payload = pickle.dumps(session)
        self.client.setex(self._make_key(session.session_id), self.ttl_seconds, payload)

    def _load_session(self, session_id: str) -> Optional[SessionContext]:
        raw = self.client.get(self._make_key(session_id))
        if not raw:
            return None
        try:
            return pickle.loads(raw)
        except Exception:
            return None

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> SessionContext:
        if not session_id:
            session_id = str(uuid.uuid4())

        session = self._load_session(session_id)
        if session is None:
            session = SessionContext(
                session_id=session_id,
                user_id=user_id,
                metadata={"user_preferences": {}, "topic_history": []}
            )

        session.last_activity = datetime.now()
        self._save_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        session = self._load_session(session_id)
        if not session:
            return None
        session.last_activity = datetime.now()
        self._save_session(session)
        return session

    def delete_session(self, session_id: str):
        self.client.delete(self._make_key(session_id))

    def clear_all_sessions(self):
        for key in self.client.scan_iter("easymart:session:*"):
            self.client.delete(key)

    def get_session_count(self) -> int:
        return sum(1 for _ in self.client.scan_iter("easymart:session:*"))


# Global session store instance
_session_store = None


def get_session_store():
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
        settings = get_settings()
        if settings.REDIS_URL:
            _session_store = RedisSessionStore(
                redis_url=settings.REDIS_URL,
                session_timeout_minutes=settings.SESSION_TIMEOUT_MINUTES
            )
        else:
            _session_store = SessionStore(session_timeout_minutes=settings.SESSION_TIMEOUT_MINUTES)
    return _session_store
