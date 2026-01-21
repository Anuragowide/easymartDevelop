"""
Test script for context recovery fix.
Tests that user follow-up responses like "give me bundle" recover the original shopping context.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.modules.assistant.session_store import SessionStore


class MockSession:
    """Mock session for testing context recovery."""
    def __init__(self):
        self.metadata = {}
        self.session_id = "test-session"


def test_save_shopping_context():
    """Test that shopping context is saved correctly."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    # Test saving context
    handler._save_shopping_context(session, "puppy supplies $250 budget")
    
    assert "shopping_context" in session.metadata
    assert session.metadata["shopping_context"]["original_query"] == "puppy supplies $250 budget"
    print("✅ Test 1 PASSED: Shopping context saved correctly")


def test_save_context_does_not_overwrite():
    """Test that existing context is not overwritten."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    # Save initial context
    handler._save_shopping_context(session, "first query")
    
    # Try to save another context
    handler._save_shopping_context(session, "second query")
    
    # Should still have first query
    assert session.metadata["shopping_context"]["original_query"] == "first query"
    print("✅ Test 2 PASSED: Existing context not overwritten")


def test_clear_shopping_context():
    """Test that shopping context is cleared correctly."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    # Save and then clear context
    handler._save_shopping_context(session, "test query")
    handler._clear_shopping_context(session)
    
    assert "shopping_context" not in session.metadata
    print("✅ Test 3 PASSED: Shopping context cleared correctly")


def test_recover_context_give_me_bundle():
    """Test recovery with 'give me bundle' follow-up."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    # Save original context
    session.metadata["shopping_context"] = {
        "original_query": "puppy supplies $250 budget",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Test recovery
    result = handler._recover_shopping_context(session, "give me bundle")
    
    assert "puppy supplies $250 budget" in result
    assert "give me bundle" in result
    assert "shopping_context" not in session.metadata  # Should be cleared after use
    print("✅ Test 4 PASSED: Context recovered for 'give me bundle'")


def test_recover_context_just_pick():
    """Test recovery with 'just pick for me' follow-up."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    session.metadata["shopping_context"] = {
        "original_query": "new puppy starter kit $300",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = handler._recover_shopping_context(session, "just pick for me")
    
    assert "new puppy starter kit $300" in result
    assert "just pick for me" in result
    print("✅ Test 5 PASSED: Context recovered for 'just pick for me'")


def test_recover_context_you_choose():
    """Test recovery with 'you choose' follow-up."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    session.metadata["shopping_context"] = {
        "original_query": "getting a kitten need supplies",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = handler._recover_shopping_context(session, "you choose")
    
    assert "getting a kitten need supplies" in result
    assert "you choose" in result
    print("✅ Test 6 PASSED: Context recovered for 'you choose'")


def test_recover_context_yes():
    """Test recovery with short 'yes' follow-up."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    session.metadata["shopping_context"] = {
        "original_query": "puppy supplies under $200",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = handler._recover_shopping_context(session, "yes")
    
    assert "puppy supplies under $200" in result
    assert "yes" in result
    print("✅ Test 7 PASSED: Context recovered for 'yes'")


def test_no_recovery_for_new_queries():
    """Test that new shopping queries are NOT combined with old context."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    session.metadata["shopping_context"] = {
        "original_query": "puppy supplies $250",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # This is a new specific query, should NOT be combined
    result = handler._recover_shopping_context(session, "show me some dog beds under $100")
    
    # Should remain unchanged
    assert result == "show me some dog beds under $100"
    # Context should still be there (not consumed)
    assert "shopping_context" in session.metadata
    print("✅ Test 8 PASSED: New queries not combined with old context")


def test_no_recovery_without_context():
    """Test that nothing happens when there's no saved context."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    # No context saved
    result = handler._recover_shopping_context(session, "give me bundle")
    
    assert result == "give me bundle"
    print("✅ Test 9 PASSED: No recovery without context")


def test_short_bundle_keyword():
    """Test recovery with short messages containing bundle keywords."""
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    handler = EasymartAssistantHandler()
    session = MockSession()
    
    session.metadata["shopping_context"] = {
        "original_query": "need starter supplies for new puppy",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = handler._recover_shopping_context(session, "bundle please")
    
    assert "need starter supplies for new puppy" in result
    print("✅ Test 10 PASSED: Short bundle keyword triggers recovery")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Context Recovery Fix")
    print("="*60 + "\n")
    
    test_save_shopping_context()
    test_save_context_does_not_overwrite()
    test_clear_shopping_context()
    test_recover_context_give_me_bundle()
    test_recover_context_just_pick()
    test_recover_context_you_choose()
    test_recover_context_yes()
    test_no_recovery_for_new_queries()
    test_no_recovery_without_context()
    test_short_bundle_keyword()
    
    print("\n" + "="*60)
    print("✅ All 10 tests PASSED!")
    print("="*60 + "\n")
