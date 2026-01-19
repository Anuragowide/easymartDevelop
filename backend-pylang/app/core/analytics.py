"""
Conversation Analytics for Production Monitoring
Tracks metrics, errors, and user engagement.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from collections import defaultdict
import json
import asyncio

logger = logging.getLogger(__name__)


class ConversationAnalytics:
    """Track and analyze conversation metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.response_times: List[float] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.popular_queries: Dict[str, int] = defaultdict(int)
        self.intent_counts: Dict[str, int] = defaultdict(int)
        self.conversion_funnel = {
            "sessions_started": 0,
            "products_viewed": 0,
            "products_added_to_cart": 0,
            "checkouts_initiated": 0,
        }
        self.daily_active_sessions: Dict[str, set] = defaultdict(set)
    
    def track_request(
        self,
        session_id: str,
        intent: str,
        query: str,
        response_time_ms: float,
        products_returned: int,
        success: bool
    ):
        """Track a conversation request"""
        today = datetime.now().strftime("%Y-%m-%d")
        hour = datetime.now().strftime("%H")
        
        # Track by day
        self.metrics[today]["total_requests"] += 1
        self.metrics[today][f"intent_{intent}"] += 1
        self.intent_counts[intent] += 1
        
        # Track unique sessions per day
        self.daily_active_sessions[today].add(session_id)
        self.metrics[today]["unique_sessions"] = len(self.daily_active_sessions[today])
        
        # Track by hour for peak analysis
        self.metrics[f"{today}_{hour}"]["requests"] += 1
        
        # Track response time
        self.response_times.append(response_time_ms)
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
        
        # Track popular queries (categorized for privacy)
        query_category = self._categorize_query(query)
        self.popular_queries[query_category] += 1
        
        # Track success/failure
        if success:
            self.metrics[today]["successful_requests"] += 1
        else:
            self.metrics[today]["failed_requests"] += 1
        
        # Track products shown
        if products_returned > 0:
            self.conversion_funnel["products_viewed"] += 1
            self.metrics[today]["products_shown"] += products_returned
        
        logger.debug(f"[ANALYTICS] Tracked: intent={intent}, products={products_returned}, time={response_time_ms:.0f}ms")
    
    def track_cart_action(self, action: str, product_id: str, quantity: int = 1):
        """Track cart-related actions"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if action == "add":
            self.conversion_funnel["products_added_to_cart"] += 1
            self.metrics[today]["cart_adds"] += 1
        elif action == "remove":
            self.metrics[today]["cart_removes"] += 1
        elif action == "checkout":
            self.conversion_funnel["checkouts_initiated"] += 1
            self.metrics[today]["checkouts"] += 1
        
        logger.debug(f"[ANALYTICS] Cart action: {action}, product={product_id}, qty={quantity}")
    
    def track_error(self, error_type: str, details: str = ""):
        """Track errors for monitoring"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.error_counts[f"{today}_{error_type}"] += 1
        self.metrics[today]["errors"] += 1
        
        # Alert if error rate is high
        total_today = self.metrics[today]["total_requests"]
        errors_today = self.metrics[today]["errors"]
        
        if total_today > 10 and errors_today / total_today > 0.1:
            logger.warning(f"[ANALYTICS] ⚠️ High error rate: {errors_today}/{total_today} ({errors_today/total_today*100:.1f}%)")
        
        logger.info(f"[ANALYTICS] Error tracked: {error_type} - {details[:100]}")
    
    def track_session_start(self, session_id: str):
        """Track new session"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.conversion_funnel["sessions_started"] += 1
        self.metrics[today]["sessions_started"] += 1
    
    def get_dashboard_metrics(self) -> Dict:
        """Get metrics for dashboard display"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        p95_response_time = 0
        if self.response_times:
            sorted_times = sorted(self.response_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
        
        total_requests = self.metrics[today]["total_requests"]
        successful = self.metrics[today]["successful_requests"]
        
        return {
            "today": {
                "total_requests": total_requests,
                "successful_requests": successful,
                "failed_requests": self.metrics[today]["failed_requests"],
                "success_rate": (successful / total_requests * 100) if total_requests > 0 else 100,
                "unique_sessions": self.metrics[today]["unique_sessions"],
                "products_shown": self.metrics[today]["products_shown"],
                "cart_adds": self.metrics[today]["cart_adds"],
            },
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "p95_response_time_ms": round(p95_response_time, 2),
            },
            "conversion_funnel": self.conversion_funnel,
            "top_intents": dict(sorted(self.intent_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_query_categories": dict(sorted(self.popular_queries.items(), key=lambda x: x[1], reverse=True)[:10]),
        }
    
    def _categorize_query(self, query: str) -> str:
        """Categorize query for analytics (privacy-preserving)"""
        query_lower = query.lower()
        
        categories = {
            "chair_search": ["chair", "seat", "stool", "office chair", "gaming chair"],
            "desk_search": ["desk", "workstation", "office desk", "standing desk"],
            "table_search": ["table", "dining table", "coffee table"],
            "sofa_search": ["sofa", "couch", "lounge", "sectional"],
            "bed_search": ["bed", "mattress", "bedroom"],
            "storage_search": ["storage", "cabinet", "shelf", "locker", "wardrobe"],
            "price_query": ["under", "budget", "cheap", "expensive", "price", "affordable"],
            "color_query": ["black", "white", "blue", "red", "grey", "color", "brown"],
            "spec_query": ["dimension", "size", "weight", "material", "specs", "specifications"],
            "stock_query": ["stock", "available", "inventory", "in stock"],
            "cart_action": ["cart", "add", "remove", "buy", "purchase", "checkout"],
            "comparison": ["compare", "difference", "vs", "versus", "better"],
            "policy_query": ["return", "shipping", "delivery", "warranty", "policy"],
        }
        
        for category, keywords in categories.items():
            if any(kw in query_lower for kw in keywords):
                return category
        
        return "general"


# Global analytics instance
analytics = ConversationAnalytics()


def get_analytics() -> ConversationAnalytics:
    """Get the global analytics instance"""
    return analytics
