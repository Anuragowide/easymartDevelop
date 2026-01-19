"""
Rate Limiting Middleware for Production
Prevents abuse and ensures fair usage.
"""

from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting to prevent abuse"""
    
    def __init__(
        self,
        requests_per_minute: int = 30,
        requests_per_hour: int = 300,
        burst_limit: int = 5
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        self.minute_counts: Dict[str, List[datetime]] = defaultdict(list)
        self.hour_counts: Dict[str, List[datetime]] = defaultdict(list)
        self.last_request: Dict[str, float] = defaultdict(float)
        self._cleanup_task = None
    
    async def start_cleanup_task(self):
        """Start the background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_entries())
    
    async def check_rate_limit(self, request: Request) -> bool:
        """Check if request should be rate limited"""
        
        # Get client identifier (IP or session)
        client_id = self._get_client_id(request)
        now = datetime.now()
        
        # Check burst limit (requests too fast)
        last = self.last_request.get(client_id, 0)
        if now.timestamp() - last < 0.5:  # Less than 500ms between requests
            burst_count = sum(1 for t in self.minute_counts[client_id] if (now - t).seconds < 5)
            if burst_count >= self.burst_limit:
                logger.warning(f"[RATE_LIMIT] Burst limit exceeded for {client_id}")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "TooManyRequests",
                        "message": "Too many requests. Please slow down.",
                        "retry_after": 5
                    }
                )
        
        self.last_request[client_id] = now.timestamp()
        
        # Check per-minute limit
        minute_ago = now - timedelta(minutes=1)
        self.minute_counts[client_id] = [t for t in self.minute_counts[client_id] if t > minute_ago]
        
        if len(self.minute_counts[client_id]) >= self.requests_per_minute:
            logger.warning(f"[RATE_LIMIT] Per-minute limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "TooManyRequests",
                    "message": "Rate limit exceeded. Please wait a moment before trying again.",
                    "retry_after": 60
                }
            )
        
        # Check per-hour limit
        hour_ago = now - timedelta(hours=1)
        self.hour_counts[client_id] = [t for t in self.hour_counts[client_id] if t > hour_ago]
        
        if len(self.hour_counts[client_id]) >= self.requests_per_hour:
            logger.warning(f"[RATE_LIMIT] Per-hour limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "TooManyRequests",
                    "message": "Hourly limit exceeded. Please try again later.",
                    "retry_after": 3600
                }
            )
        
        # Record this request
        self.minute_counts[client_id].append(now)
        self.hour_counts[client_id].append(now)
        
        return True
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get session_id from body (for POST requests)
        # Note: We can't read body here without consuming it, so use query params or headers
        
        # Check for session ID in query params
        session_id = request.query_params.get("session_id")
        if session_id:
            return f"session_{session_id}"
        
        # Check for session ID in headers
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return f"session_{session_id}"
        
        # Use IP with forwarded header support
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip_{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip_{client_host}"
    
    async def _cleanup_old_entries(self):
        """Periodically clean up old rate limit entries"""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            
            # Clean up old entries
            clients_to_remove = []
            for client_id in list(self.hour_counts.keys()):
                self.hour_counts[client_id] = [
                    t for t in self.hour_counts[client_id] if t > hour_ago
                ]
                if not self.hour_counts[client_id]:
                    clients_to_remove.append(client_id)
            
            for client_id in clients_to_remove:
                del self.hour_counts[client_id]
                self.minute_counts.pop(client_id, None)
                self.last_request.pop(client_id, None)
            
            logger.debug(f"[RATE_LIMIT] Cleaned up, tracking {len(self.hour_counts)} clients")


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(request: Request):
    """Dependency for rate limiting"""
    await rate_limiter.check_rate_limit(request)
