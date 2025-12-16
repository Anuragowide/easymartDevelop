"""
Event Tracking

Tracks user events for analytics and monitoring.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path


class EventType(str, Enum):
    """Event types for tracking"""
    SEARCH = "search"
    PRODUCT_VIEW = "product_view"
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    ERROR = "error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class EventTracker:
    """
    Event tracking for user actions and system events.
    Logs events to a local JSONL file and prints to console.
    """
    
    def __init__(self, log_file: str = "events.jsonl"):
        self.log_file = log_file
        # Ensure log file exists or can be created
        try:
            with open(self.log_file, 'a') as f:
                pass
        except Exception as e:
            print(f"Warning: Could not initialize event log file: {e}")
    
    async def track(
        self,
        event_type: EventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track an event.
        
        Args:
            event_type: Type of event
            user_id: User identifier
            session_id: Session identifier
            properties: Additional event properties
        
        Example:
            >>> tracker = EventTracker()
            >>> await tracker.track(
            ...     EventType.SEARCH,
            ...     session_id="sess123",
            ...     properties={"query": "leather wallet", "results": 5}
            ... )
        """
        # Handle both string and enum event types
        if isinstance(event_type, str):
            event_type_str = event_type
        else:
            event_type_str = event_type.value
            
        event = {
            "event_type": event_type_str,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "properties": properties or {}
        }
        
        # Log to file (async)
        await asyncio.to_thread(self._write_log, event)

        # Log to console
        print(f"[EVENT] {json.dumps(event)}")
    
    def _write_log(self, event: Dict[str, Any]) -> None:
        """Write event to log file synchronously (run in thread)"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            print(f"Error writing event to file: {e}")

    async def track_search(
        self,
        query: str,
        results_count: int,
        session_id: str,
        took_ms: float
    ) -> None:
        """Track a search event"""
        await self.track(
            EventType.SEARCH,
            session_id=session_id,
            properties={
                "query": query,
                "results_count": results_count,
                "took_ms": took_ms
            }
        )
    
    async def track_product_view(
        self,
        sku: str,
        session_id: str,
        source: Optional[str] = None
    ) -> None:
        """Track a product view event"""
        await self.track(
            EventType.PRODUCT_VIEW,
            session_id=session_id,
            properties={
                "sku": sku,
                "source": source
            }
        )
    
    async def track_message(
        self,
        message: str,
        intent: Optional[str],
        session_id: str,
        direction: str = "received"  # received or sent
    ) -> None:
        """Track a message event"""
        event_type = EventType.MESSAGE_RECEIVED if direction == "received" else EventType.MESSAGE_SENT
        await self.track(
            event_type,
            session_id=session_id,
            properties={
                "message_length": len(message),
                "intent": intent
            }
        )
    
    async def track_error(
        self,
        error_type: str,
        error_message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track an error event"""
        await self.track(
            EventType.ERROR,
            session_id=session_id,
            properties={
                "error_type": error_type,
                "error_message": error_message,
                "context": context
            }
        )
