"""
EasyMart Chatbot Demo Test Script
=================================
Tests all major features to verify they're working before demo.
Logs all responses to JSON for review.
"""
import asyncio
import sys
import os
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

# Suppress verbose initialization logs
import logging
logging.getLogger().setLevel(logging.WARNING)

async def test_feature(handler, session_id: str, query: str, feature_name: str, expect_products: bool = True):
    """Test a single feature and return pass/fail with full response data"""
    from app.modules.assistant.handler import AssistantRequest
    
    request = AssistantRequest(
        session_id=session_id,
        user_id="demo-user",
        message=query
    )
    
    result_data = {
        "feature": feature_name,
        "query": query,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "passed": False,
        "products_count": 0,
        "products": [],
        "response": "",
        "error": None
    }
    
    try:
        response = await handler.handle_message(request)
        products = len(response.products)
        has_response = bool(response.message and len(response.message) > 20)
        
        result_data["products_count"] = products
        result_data["response"] = response.message
        result_data["products"] = [
            {"name": p.get("name", "N/A"), "price": p.get("price", 0), "sku": p.get("sku") or p.get("id")}
            for p in response.products[:5]
        ]
        result_data["cart_summary"] = response.cart_summary
        result_data["metadata"] = response.metadata
        
        # Determine pass/fail based on feature type
        if expect_products:
            passed = products > 0
        else:
            passed = has_response
        
        result_data["passed"] = passed
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {feature_name}")
        print(f"       Query: {query}")
        if expect_products:
            print(f"       Products: {products}")
            if products > 0:
                print(f"       First: {response.products[0].get('name', 'N/A')[:50]}")
        else:
            print(f"       Response: {response.message[:80]}...")
        print()
        return passed, result_data
    except Exception as e:
        result_data["error"] = str(e)
        print(f"❌ ERROR | {feature_name}")
        print(f"       Query: {query}")
        print(f"       Error: {str(e)[:100]}")
        print()
        return False, result_data

async def main():
    from app.modules.assistant.handler import EasymartAssistantHandler
    
    print("="*70)
    print("EASYMART CHATBOT COMPREHENSIVE FEATURE TEST")
    print("="*70)
    print()
    
    handler = EasymartAssistantHandler()
    
    # Define test cases: (session_id, query, feature_name, expect_products)
    tests = [
        # ============ PRODUCT SEARCH ============
        ("search-1", "show me grey sofas", "1. Color Search (Grey Sofas)", True),
        ("search-2", "I need a black office chair", "2. Color + Category Search", True),
        ("search-3", "wooden desks under $500", "3. Material + Price Filter", True),
        ("search-4", "gaming chair", "4. Gaming Furniture", True),
        ("search-5", "outdoor patio furniture", "5. Outdoor Furniture", True),
        ("search-6", "bed frame queen size", "6. Bed Frame Search", True),
        
        # ============ PET PRODUCTS ============
        ("pet-1", "dog beds", "7. Dog Beds Search", True),
        ("pet-2", "cat scratching post", "8. Cat Supplies Search", True),
        ("pet-3", "bird cage", "9. Bird Cage Search", True),
        ("pet-4", "fish tank accessories", "10. Fish Supplies Search", True),
        
        # ============ BUNDLE PLANNER ============
        ("bundle-1", "parrot starter bundle under $150", "11. Bird Bundle", True),
        ("bundle-2", "puppy starter kit under $200", "12. Puppy Bundle", True),
        ("bundle-3", "home office setup with desk and chair under $800", "13. Office Bundle", True),
        ("bundle-4", "kitten starter supplies under $100", "14. Kitten Bundle", True),
        
        # ============ VAGUE QUERIES ============
        ("vague-1", "I need something for my back pain", "15. Vague Query (Back Pain)", True),
        ("vague-2", "help me set up my home office", "16. Vague Query (Home Office)", True),
        ("vague-3", "something comfortable to sit on", "17. Vague Query (Seating)", True),
        
        # ============ POLICY & INFO ============
        ("policy-1", "what is your return policy?", "18. Return Policy", False),
        ("policy-2", "how much is shipping?", "19. Shipping Info", False),
        ("policy-3", "do you offer warranty?", "20. Warranty Policy", False),
        ("policy-4", "what payment methods do you accept?", "21. Payment Methods", False),
        ("policy-5", "how can I contact support?", "22. Contact Info", False),
        
        # ============ CART OPERATIONS ============
        # First search for a product, then add to cart
        ("cart-1", "show me office chairs", "23. Cart - Search First", True),
        ("cart-1", "add the first one to cart", "24. Cart - Add Item", False),
        ("cart-1", "view my cart", "25. Cart - View Cart", False),
        ("cart-1", "add 2 more of the same", "26. Cart - Update Quantity", False),
        ("cart-1", "clear my cart", "27. Cart - Clear Cart", False),
        
        # ============ OFF-TOPIC / OUT OF SCOPE ============
        ("offtopic-1", "what's the weather today?", "28. Off-Topic (Weather)", False),
        ("offtopic-2", "tell me a joke", "29. Off-Topic (Joke)", False),
        ("offtopic-3", "who is the president?", "30. Off-Topic (Politics)", False),
        
        # ============ PRODUCT DETAILS & COMPARISON ============
        ("detail-1", "show me standing desks", "31. Search for Comparison", True),
        ("detail-1", "compare the first two options", "32. Product Comparison", False),
        ("detail-1", "tell me more about option 1", "33. Product Details", False),
        
        # ============ FOLLOW-UP & CONTEXT ============
        ("context-1", "show me red chairs", "34. Initial Search", True),
        ("context-1", "show me in blue instead", "35. Color Refinement", True),
        ("context-1", "under $200", "36. Price Refinement", True),
    ]
    
    passed = 0
    failed = 0
    all_results = []
    
    for session_id, query, feature_name, expect_products in tests:
        result, result_data = await test_feature(handler, session_id, query, feature_name, expect_products)
        all_results.append(result_data)
        if result:
            passed += 1
        else:
            failed += 1
    
    # Save results to JSON
    log_file = f"demo_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_run": datetime.now().isoformat(),
            "summary": {
                "total": len(tests),
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed/len(tests))*100:.1f}%"
            },
            "results": all_results
        }, f, indent=2, ensure_ascii=False, default=str)
    
    print("="*70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print(f"Pass Rate: {(passed/len(tests))*100:.1f}%")
    print(f"Results saved to: {log_file}")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 All tests passed! Ready for demo.")
    elif failed <= 5:
        print(f"\n⚠️  {failed} test(s) need attention. Review {log_file}")
    else:
        print(f"\n❌ {failed} tests failed. Fix issues before demo.")

if __name__ == "__main__":
    asyncio.run(main())
