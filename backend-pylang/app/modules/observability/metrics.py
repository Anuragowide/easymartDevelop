"""
Metrics Collection

Collects application metrics for monitoring and performance analysis.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import time


class MetricsCollector:
    """
    Collects and aggregates application metrics.
    
    TODO: Implement actual metrics export to monitoring system
    (e.g., Prometheus, CloudWatch, Datadog)
    """
    
    def __init__(self):
        # In-memory metrics storage (for development)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = defaultdict(list)
    
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to increment by
            tags: Optional tags for the metric
        
        Example:
            >>> metrics = MetricsCollector()
            >>> metrics.increment("search.requests", tags={"status": "success"})
        """
        key = self._make_key(metric_name, tags)
        self.counters[key] += value
    
    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric (current value).
        
        Args:
            metric_name: Name of the metric
            value: Current value
            tags: Optional tags
        """
        key = self._make_key(metric_name, tags)
        self.gauges[key] = value
    
    def histogram(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a histogram value (for timing, sizes, etc.).
        
        Args:
            metric_name: Name of the metric
            value: Value to record
            tags: Optional tags
        """
        key = self._make_key(metric_name, tags)
        self.histograms[key].append(value)
    
    def timing(self, metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timing metric.
        
        Args:
            metric_name: Name of the metric
            duration_ms: Duration in milliseconds
            tags: Optional tags
        """
        self.histogram(f"{metric_name}.duration_ms", duration_ms, tags)
    
    def _make_key(self, metric_name: str, tags: Optional[Dict[str, str]]) -> str:
        """Make metric key from name and tags"""
        if not tags:
            return metric_name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.
        
        Returns:
            Dictionary of all metrics
        """
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                k: {
                    "count": len(v),
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                    "avg": sum(v) / len(v) if v else 0
                }
                for k, v in self.histograms.items()
            }
        }
    
    def reset(self) -> None:
        """Reset all metrics (useful for testing)"""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()


# Context manager for timing
class Timer:
    """
    Context manager for timing operations.
    
    Example:
        >>> metrics = MetricsCollector()
        >>> with Timer(metrics, "search.duration"):
        ...     # Do search operation
        ...     pass
    """
    
    def __init__(self, metrics: MetricsCollector, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.metrics = metrics
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.metrics.timing(self.metric_name, duration_ms, self.tags)
