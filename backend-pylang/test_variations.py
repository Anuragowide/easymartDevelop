"""Test query variations beyond the exact examples"""
from app.modules.assistant.vague_query_handler import VagueQueryHandler

handler = VagueQueryHandler()

# Test variations NOT in the examples
test_queries = [
    # Back pain variations
    "my back hurts so bad",
    "sitting all day is destroying my posture",
    "I have terrible back pain",
    
    # Space variations  
    "tiny apartment",
    "small room",
    "need something compact",
    
    # Budget variations
    "on a tight budget",
    "cheap furniture please",
    "I have no money",
    "affordable options",
    
    # Style variations
    "modern look",
    "rustic vibes",
    "farmhouse style",
    "mid century modern",
    
    # Pet variations
    "I have a dog",
    "pet proof furniture",
    "my puppy chews everything",
    
    # Work from home
    "I work from home",
    "need a home office setup",
    "remote worker",
    
    # Negations
    "no plastic please",
    "anything but fabric",
    "not too expensive",
    
    # Random vague ones
    "something cozy",
    "need to organize my stuff",
    "just moved in",
    "having guests over",
    
    # More lifestyle
    "I nap a lot",
    "movie night setup",
    "parties every weekend",
]

print("=" * 70)
print("TESTING QUERY VARIATIONS (not exact examples)")
print("=" * 70)

detected = 0
not_detected = 0

for q in test_queries:
    result = handler.analyze(q)
    status = "✅" if result.is_vague else "❌"
    print(f'{status} "{q}"')
    if result.is_vague:
        detected += 1
        print(f"   → {result.category.value}: {result.suggested_query}")
    else:
        not_detected += 1
        print(f"   → Not detected as vague")
    print()

print("=" * 70)
print(f"SUMMARY: {detected} detected as vague, {not_detected} not detected")
print("=" * 70)
