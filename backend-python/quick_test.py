"""Quick test for filter validation"""
import sys
sys.path.insert(0, '.')

from app.modules.assistant.filter_validator import FilterValidator

fv = FilterValidator()
queries = [
    "mma gloves",
    "show me mma gloves", 
    "boxing bag",
    "dog kennel",
    "dumbbells",
    "office chair",
    "chair",
    "treadmill",
    "cat tree",
    "electric scooter"
]

print("\n=== FILTER VALIDATION TEST ===")
print(f"MIN_FILTER_WEIGHT threshold: {fv.MIN_FILTER_WEIGHT}")
print("-" * 60)

for q in queries:
    result = fv.validate_filter_count({}, q)
    valid = result[0]
    weight = result[1]
    status = "PASS" if valid else "FAIL"
    print(f"{status} Query: {q:25} -> valid={valid}, weight={weight:.1f}")
