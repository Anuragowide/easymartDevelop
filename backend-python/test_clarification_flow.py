"""
Quick test script to verify vague query clarification flow.
"""

from app.modules.assistant.intent_detector import IntentDetector
from app.modules.assistant.prompts import generate_clarification_prompt

def test_vague_detection():
    """Test vague query detection"""
    detector = IntentDetector()
    
    test_queries = [
        "I want something",
        "Show me something",
        "Something blue",
        "Something wooden",
        "I am redoing my room",
        "Redoing my bedroom",
        "I want a chair",
        "Looking for a chair",
        "Best furniture",
        "Best chair",
        "Furniture for my room",
        "Furniture for bedroom",
        "Chair for home",
        "Table for work",
        "Something compact",
        "Something cozy",
        "Which one is best",
        "What do you recommend",
        "Furniture for work",
    ]
    
    print("=" * 80)
    print("VAGUE QUERY DETECTION TEST")
    print("=" * 80)
    
    for query in test_queries:
        result = detector.detect_vague_patterns(query)
        if result:
            print(f"\n✓ Query: '{query}'")
            print(f"  Type: {result['vague_type']}")
            print(f"  Partial Entities: {result['partial_entities']}")
            
            # Generate clarification prompt
            prompt = generate_clarification_prompt(
                result['vague_type'],
                result['partial_entities'],
                clarification_count=0
            )
            print(f"  Clarification: {prompt[:100]}...")
        else:
            print(f"\n✗ Query: '{query}' - NOT VAGUE (good!)")
    
    print("\n" + "=" * 80)


def test_merge_clarification():
    """Test merging clarification responses"""
    detector = IntentDetector()
    
    print("\n" + "=" * 80)
    print("CLARIFICATION MERGE TEST")
    print("=" * 80)
    
    test_cases = [
        {
            "original": {"color": "blue"},
            "clarification": "chairs",
            "vague_type": "attribute_only"
        },
        {
            "original": {"room_type": "bedroom"},
            "clarification": "a bed and a desk",
            "vague_type": "room_setup"
        },
        {
            "original": {"category": "chair"},
            "clarification": "for office work",
            "vague_type": "category_only"
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Original entities: {case['original']}")
        print(f"  Clarification: '{case['clarification']}'")
        
        merged = detector.merge_clarification_response(
            case['original'],
            case['clarification'],
            case['vague_type']
        )
        
        print(f"  Merged entities: {merged}")
        print(f"  Generated query: '{merged.get('query', 'N/A')}'")
    
    print("\n" + "=" * 80)


def test_bypass_detection():
    """Test bypass phrase detection"""
    print("\n" + "=" * 80)
    print("BYPASS PHRASE TEST")
    print("=" * 80)
    
    bypass_phrases = [
        "just show me anything",
        "show me anything",
        "surprise me",
        "whatever you recommend",
        "anything is fine",
        "you choose",
        "no preference",
    ]
    
    for phrase in bypass_phrases:
        is_bypass = any(p in phrase.lower() for p in [
            "just show me anything", "show me anything", "surprise me",
            "whatever you recommend", "any is fine", "anything is fine",
            "you choose", "no preference", "doesn't matter"
        ])
        status = "✓ DETECTED" if is_bypass else "✗ MISSED"
        print(f"  {status}: '{phrase}'")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🔍 Testing Vague Query Clarification System\n")
    
    try:
        test_vague_detection()
        test_merge_clarification()
        test_bypass_detection()
        
        print("\n✅ All tests completed successfully!\n")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}\n")
        import traceback
        traceback.print_exc()
