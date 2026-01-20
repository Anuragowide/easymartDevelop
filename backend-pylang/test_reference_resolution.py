"""
Test product reference resolution functionality
"""
from app.modules.assistant.session_store import SessionStore
from app.modules.assistant.handler import EasymartAssistantHandler

def main():
    # Initialize session store
    session_store = SessionStore()

    # Create test session
    session_id = "test-reference-resolution"
    session = session_store.get_or_create_session(session_id, "test-user")

    # Simulate products shown from a previous search
    test_products = [
        {
            "id": "SKU-CHAIR-001",
            "sku": "SKU-CHAIR-001",
            "name": "Artiss Office Chair",
            "title": "Artiss Office Chair Ergonomic Computer Desk Chair Black",
            "price": 149.99,
            "category": "Chairs"
        },
        {
            "id": "SKU-CHAIR-002",
            "sku": "SKU-CHAIR-002",
            "name": "Artiss Gaming Chair",
            "title": "Artiss Gaming Chair Racing Chair Executive Office Computer Chairs",
            "price": 199.99,
            "category": "Chairs"
        }
    ]

    # Update session with shown products
    session.update_shown_products(test_products)

    print("✓ Session initialized with 2 products")
    print(f"  Product 1: {test_products[0]['name']} ({test_products[0]['sku']})")
    print(f"  Product 2: {test_products[1]['name']} ({test_products[1]['sku']})")
    print()

    # Initialize handler
    handler = EasymartAssistantHandler()

    # Test cases for reference resolution
    test_cases = [
        "tell me about option 1",
        "add the first one to cart",
        "compare option 1 and option 2",
        "what's the price of the second chair",
        "show me details of product 1",
        "I want the first chair",
    ]

    print("Testing reference resolution:")
    print("=" * 80)

    for test_message in test_cases:
        resolved = handler._resolve_product_references(session, test_message)
        print(f"Original: {test_message}")
        print(f"Resolved: {resolved}")
        
        # Check if resolution worked
        if "SKU-" in resolved and resolved != test_message:
            print("✓ PASS - Reference resolved successfully")
        else:
            print("✗ FAIL - Reference not resolved")
        print()

    print("=" * 80)
    print("✓ Reference resolution test complete!")

if __name__ == "__main__":
    main()
