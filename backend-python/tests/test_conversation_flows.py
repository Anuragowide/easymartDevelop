import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.modules.assistant.hf_llm_client import FunctionCall, LLMResponse

client = TestClient(app)

class MockLLMClient:
    async def chat(self, messages, tools=None, **kwargs):
        last_msg = messages[-1].content.lower()
        
        # Pure Search
        if "office chairs" in last_msg:
            return LLMResponse(
                content="I found some office chairs for you.",
                function_calls=[
                    FunctionCall(
                        name='search_products',
                        arguments={'query': 'office chair', 'category': 'chair'}
                    )
                ]
            )
        
        # Refine
        elif "under $200" in last_msg:
             return LLMResponse(
                content="Here are some chairs under $200.",
                function_calls=[
                    FunctionCall(
                        name='search_products',
                        arguments={'query': 'office chair', 'price_max': 200}
                    )
                ]
            )
        
        # Add to Cart
        elif "add the first one" in last_msg:
             return LLMResponse(
                content="Added to cart.",
                function_calls=[
                    FunctionCall(
                        name='update_cart',
                        arguments={'action': 'add', 'product_id': 'CHR-001', 'quantity': 1}
                    )
                ]
            )
            
        # Show Cart
        elif "show me my cart" in last_msg:
             return LLMResponse(
                content="Here is your cart.",
                function_calls=[]
            )

        # Spec QA
        elif "dimensions" in last_msg:
             return LLMResponse(
                content="The dimensions are 50x50cm.",
                function_calls=[
                    FunctionCall(
                        name='get_product_specs',
                        arguments={'product_id': 'CHR-001', 'question': 'dimensions'}
                    )
                ]
            )
        
        # Default
        return LLMResponse(content="I can help with that.")

@pytest.fixture(autouse=True)
def setup_mocks():
    # Patch create_llm_client in the source module
    with patch("app.modules.assistant.hf_llm_client.create_llm_client", new_callable=AsyncMock) as mock_create:
        mock_client = MockLLMClient()
        mock_create.return_value = mock_client
        
        # Reset the singleton handler's client to ensure it uses our mock
        from app.modules.assistant.handler import get_assistant_handler
        handler = get_assistant_handler()
        handler.llm_client = None
        
        yield mock_client

class TestConversationFlows:
    
    def test_flow_pure_search(self):
        """
        Flow: Pure Search
        User asks for a product -> Assistant returns results.
        """
        print("\n=== Flow: Pure Search ===")
        
        # 1. Search
        response = client.post("/assistant/message", json={
            "session_id": "flow-search-001",
            "message": "Show me office chairs"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["intent"] == "product_search"
        # With the mock, we simulate a search_products call. 
        # However, the actual tool execution runs against the real DB/Index.
        # So we need to ensure the DB has data or the tool handles empty results gracefully.
        # If the DB is empty, products might be empty list, but NOT None.
        assert data["products"] is not None
        # We can't guarantee products > 0 unless we seed the DB, but we can check the structure.
        print(f"✓ Search returned {len(data['products'])} products")

    def test_flow_search_refine(self):
        """
        Flow: Search -> Refine
        User searches -> User adds filter (e.g., "under $200").
        """
        print("\n=== Flow: Search -> Refine ===")
        session_id = "flow-refine-001"
        
        # 1. Initial Search
        client.post("/assistant/message", json={
            "session_id": session_id,
            "message": "Show me office chairs"
        })
        
        # 2. Refine
        response = client.post("/assistant/message", json={
            "session_id": session_id,
            "message": "I want one under $200"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["intent"] == "product_search"
        print("✓ Refinement processed")

    def test_flow_search_cart_add_show(self):
        """
        Flow: Search -> Add to Cart -> Show Cart
        """
        print("\n=== Flow: Search -> Add -> Show Cart ===")
        session_id = "flow-cart-001"
        
        # 1. Search
        client.post("/assistant/message", json={
            "session_id": session_id,
            "message": "Show me leather wallets"
        })
        
        # 2. Add to Cart ("add the first one")
        response = client.post("/assistant/message", json={
            "session_id": session_id,
            "message": "Add the first one to my cart"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "cart_add"
        
        # 3. Show Cart
        response = client.post("/assistant/message", json={
            "session_id": session_id,
            "message": "Show me my cart"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "cart_show"
        print("✓ Cart flow completed")

    def test_flow_spec_qa(self):
        """
        Flow: Spec Q&A
        User asks about a specific product's specs.
        """
        print("\n=== Flow: Spec Q&A ===")
        session_id = "flow-spec-001"
        
        # 1. Search to establish context
        client.post("/assistant/message", json={
            "session_id": session_id,
            "message": "Show me wallets"
        })
        
        # 2. Ask Spec Question ("what are the dimensions of the first one?")
        response = client.post("/assistant/message", json={
            "session_id": session_id,
            "message": "What are the dimensions of the first one?"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["intent"] == "product_spec_qa"
        print("✓ Spec Q&A processed")

    def test_flow_out_of_scope(self):
        """
        Flow: Out of Scope
        User asks something irrelevant.
        """
        print("\n=== Flow: Out of Scope ===")
        response = client.post("/assistant/message", json={
            "session_id": "flow-oos-001",
            "message": "What is the weather in Tokyo?"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["intent"] != "product_search"
        print("✓ Out of scope handled")
