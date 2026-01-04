"""Test the merge clarification function with various scenarios"""
from app.modules.assistant.intent_detector import IntentDetector

d = IntentDetector()

tests = [
    # (original_entities, clarification, vague_type, expected_query)
    ({'category': 'chair'}, 'for office', 'category_only', 'chair for office'),
    ({'category': 'desk'}, 'wooden', 'category_only', 'desk wood'),  # normalizes wooden -> wood
    ({'category': 'sofa'}, 'red', 'category_only', 'sofa red'),
    ({'category': 'bed'}, 'for kids', 'category_only', 'bed for kids'),
    ({'category': 'table'}, 'under 500', 'category_only', 'table under $500'),
    ({'category': 'locker'}, 'office', 'category_only', 'locker for office'),
    ({'category': 'shelf'}, 'bedroom', 'category_only', 'shelf for bedroom'),
    ({'category': 'stool'}, 'metal', 'category_only', 'stool metal'),
    ({'category': 'chair'}, 'living room', 'category_only', 'chair for living_room'),  # normalizes spaces
    ({'category': 'cabinet'}, 'for storage', 'category_only', 'cabinet for storage'),
    ({'category': 'locker'}, 'for gym', 'category_only', 'locker for gym'),
]

print("Testing merge_clarification_response:\n")
all_pass = True
for original, clarification, vague_type, expected in tests:
    result = d.merge_clarification_response(original.copy(), clarification, vague_type)
    actual = result['query']
    status = "✓" if actual == expected else "✗"
    if actual != expected:
        all_pass = False
        print(f"  {status} {original} + \"{clarification}\"")
        print(f"      Expected: \"{expected}\"")
        print(f"      Got:      \"{actual}\"")
    else:
        print(f"  {status} {original} + \"{clarification}\" -> \"{actual}\"")

print()
if all_pass:
    print("All tests PASSED!")
else:
    print("Some tests FAILED!")
