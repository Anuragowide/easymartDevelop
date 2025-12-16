import pytest
import os
import json
from app.modules.observability.events import EventTracker, EventType
from app.modules.observability.metrics import MetricsCollector

@pytest.mark.asyncio
class TestObservability:
    async def test_event_tracker(self, tmp_path):
        # Use a temporary file for logging
        log_file = tmp_path / "test_events.jsonl"
        tracker = EventTracker(log_file=str(log_file))
        
        await tracker.track(
            EventType.SEARCH,
            session_id="test-session",
            properties={"query": "test"}
        )
        
        # Verify file content
        assert log_file.exists()
        content = log_file.read_text()
        event = json.loads(content.strip())
        assert event["event_type"] == "search"
        assert event["session_id"] == "test-session"

    def test_metrics_collector(self):
        metrics = MetricsCollector()
        metrics.increment("test.counter")
        metrics.gauge("test.gauge", 42.0)
        
        data = metrics.get_metrics()
        assert data["counters"]["test.counter"] == 1
        assert data["gauges"]["test.gauge"] == 42.0
