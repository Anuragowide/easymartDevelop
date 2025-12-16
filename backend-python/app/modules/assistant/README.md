# Easymart Assistant Module

Complete conversational AI assistant for Easymart furniture store, built with:
- **LLM**: Mistral-7B-Instruct-v0.2 via Hugging Face Inference API
- **Function Calling**: 8 tools for product search, specifications, cart, policies, and contact
- **Intent Detection**: Rule-based pattern matching for 15+ intents
- **Session Management**: In-memory conversation context with product reference resolution
- **Store Integration**: Easymart-specific policies, contact info, and furniture catalog

---

## Architecture

```
assistant/
├── handler.py               # Main orchestrator (EasymartAssistantHandler)
├── hf_llm_client.py        # Mistral-7B integration via HF API
├── tools.py                # 8 function implementations
├── intents.py              # Intent type definitions (Pydantic models)
├── intent_detector.py      # Pattern-based intent detection
├── prompts.py              # System prompt with store info
├── session_store.py        # Session management with context
└── __init__.py             # Module exports
```

### Flow

```
User Message
    ↓
Session Management (get/create session)
    ↓
Intent Detection (extract entities)
    ↓
LLM Call (Mistral-7B with function calling)
    ↓
Tool Execution (0+ function calls)
    ↓
LLM Call (generate final response)
    ↓
Session Update (messages, products, cart)
    ↓
Response to User
```

---

## Features

### 15+ Intent Types

| Intent | Description | Example |
|--------|-------------|---------|
| `product_search` | Search furniture by keywords, filters | "Show me office chairs under $300" |
| `product_spec_qa` | Ask about product specifications | "What are the dimensions of the first one?" |
| `cart_add` | Add items to cart | "Add it to my cart" |
| `cart_remove` | Remove items from cart | "Remove the chair from cart" |
| `cart_show` | View cart contents | "Show me my cart" |
| `cart_update_quantity` | Update item quantities | "Change quantity to 2" |
| `product_compare` | Compare products | "Compare the first and third chairs" |
| `product_availability` | Check stock status | "Is this available?" |
| `return_policy` | Returns information | "What's your return policy?" |
| `shipping_info` | Shipping costs and times | "How much is shipping?" |
| `payment_options` | Payment methods | "Do you accept Afterpay?" |
| `warranty_info` | Warranty details | "What warranty do you offer?" |
| `contact_info` | Contact details | "How can I contact you?" |
| `store_hours` | Business hours | "When are you open?" |
| `store_location` | Physical location | "Where is your store?" |
| `greeting` | Welcome messages | "Hello" |
| `general_help` | General assistance | "Help me find furniture" |
| `out_of_scope` | Non-furniture queries | "What's the weather?" |

### 8 Tool Functions

#### 1. **search_products**
Search furniture catalog with filters:
- `query`: Search keywords
- `category`: chair, table, sofa, bed, desk, shelf, stool, storage
- `material`: wood, metal, leather, fabric, glass, rattan
- `style`: modern, contemporary, industrial, minimalist, rustic, scandinavian
- `room_type`: office, bedroom, living_room, dining_room, outdoor
- `price_max`: Maximum price (AUD)

#### 2. **get_product_specs**
Get detailed specifications:
- `product_id`: SKU (e.g., "CHR-001")
- `question`: Optional Q&A search in specs
- **CRITICAL**: Never makes up specs - always uses real data or returns "not found"

#### 3. **check_availability**
Check stock status:
- `product_id`: SKU
- Returns: in_stock, quantity_available, estimated_delivery

#### 4. **compare_products**
Compare 2-4 products side-by-side:
- `product_ids`: List of 2-4 SKUs
- Returns: Products with specs and comparison summary

#### 5. **update_cart**
Cart operations (placeholder for Node.js integration):
- `action`: add, remove, update_quantity, view
- `product_id`: SKU
- `quantity`: Item quantity
- `session_id`: User session

#### 6. **get_policy_info**
Policy information:
- `policy_type`: returns, shipping, payment, warranty
- Returns: Formatted policy text and details

#### 7. **get_contact_info**
Contact information:
- `info_type`: all, phone, email, hours, location, chat
- Returns: Easymart contact details

#### 8. **calculate_shipping**
Shipping cost calculator:
- `order_total`: Subtotal (AUD)
- `postcode`: Australian postcode (optional)
- Returns: Shipping cost, free shipping eligibility, delivery time

---

## Usage

### Basic Usage

```python
from app.modules.assistant import get_assistant_handler, AssistantRequest

# Get handler instance (singleton)
handler = get_assistant_handler()

# Create request
request = AssistantRequest(
    message="Show me modern office chairs under $250",
    session_id=None,  # Auto-generated if not provided
    user_id="user_123"  # Optional
)

# Handle message
response = await handler.handle_message(request)

print(response.message)  # Assistant response
print(response.products)  # List of products (if any)
print(response.session_id)  # Session ID for continuity
```

### API Endpoint

```bash
# Send message
POST /assistant/message
{
  "message": "Show me office chairs",
  "session_id": "abc-123",  # Optional
  "context": {"user_id": "user_123"}  # Optional
}

# Response
{
  "session_id": "abc-123",
  "message": "Here are 3 office chairs I found...",
  "intent": "product_search",
  "products": [...],
  "suggested_actions": ["Ask about specifications", "Add to cart"],
  "metadata": {
    "processing_time_ms": 1234,
    "function_calls": 1
  }
}

# Get greeting
GET /assistant/greeting?session_id=abc-123

# Get session info
GET /assistant/session/abc-123

# Clear session
DELETE /assistant/session/abc-123
```

---

## Configuration

### Environment Variables

```bash
# Required
HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxx

# Optional (defaults provided)
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
HUGGINGFACE_BASE_URL=https://api-inference.huggingface.co/models
HUGGINGFACE_TIMEOUT=30
HUGGINGFACE_MAX_RETRIES=3
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=512
SESSION_TIMEOUT_MINUTES=30
```

### Getting Hugging Face API Key

1. Sign up at https://huggingface.co/
2. Go to Settings → Access Tokens
3. Create new token (read access sufficient)
4. Add to `.env` file

---

## Store Information

### Easymart Details
- **Name**: Easymart
- **Website**: https://easymart.com.au
- **Tagline**: Quality Furniture for Modern Living
- **Location**: 123 Furniture Drive, Sydney NSW 2000
- **Phone**: 1300 327 962
- **Email**: support@easymart.com.au
- **Hours**: Mon-Fri 9AM-6PM, Sat 10AM-4PM AEST

### Policies
- **Returns**: 30 days, unused items, original packaging
- **Shipping**: FREE over $199, otherwise $15 (5-10 business days)
- **Express**: $35 (2-5 business days)
- **Payment**: Visa, Mastercard, Amex, PayPal, Afterpay, Zip
- **Warranty**: 12 months manufacturing defects

---

## Product Reference Resolution

The assistant tracks up to 10 recently shown products for easy reference:

```
User: "Show me office chairs"
Assistant: "Here are 3 office chairs:
1. Modern Mesh Chair - $199
2. Executive Leather Chair - $349
3. Ergonomic Task Chair - $279"

User: "What are the dimensions of the first one?"
Assistant: [Resolves "first one" → "Modern Mesh Chair" (CHR-001)]
          "The Modern Mesh Chair measures 60cm W x 58cm D x 95cm H..."

User: "Add the second one to my cart"
Assistant: [Resolves "second one" → "Executive Leather Chair" (CHR-002)]
          "Great! Added Executive Leather Chair to your cart. Total: $349"
```

Reference types:
- **Index**: "first one", "second", "third", "1", "2", "3"
- **SKU**: "CHR-001", "TBL-005"
- **Name**: "mesh chair", "leather"

---

## Testing

### Quick Test

```python
import asyncio
from app.modules.assistant import get_assistant_handler, AssistantRequest

async def test_assistant():
    handler = get_assistant_handler()
    
    # Test 1: Product search
    request = AssistantRequest(message="Show me office chairs under $200")
    response = await handler.handle_message(request)
    print(f"Response: {response.message}")
    print(f"Products found: {len(response.products)}")
    
    # Test 2: Spec question (using same session)
    request2 = AssistantRequest(
        message="What are the dimensions of the first one?",
        session_id=response.session_id
    )
    response2 = await handler.handle_message(request2)
    print(f"Spec answer: {response2.message}")
    
    # Test 3: Policy question
    request3 = AssistantRequest(
        message="What's your return policy?",
        session_id=response.session_id
    )
    response3 = await handler.handle_message(request3)
    print(f"Policy: {response3.message}")

asyncio.run(test_assistant())
```

### Conversation Scenarios

1. **Office Chair Search**
   - "Show me ergonomic office chairs under $300"
   - "What are the dimensions of the second one?"
   - "Add it to my cart"

2. **Dining Table with Specs**
   - "I need a dining table for 6 people"
   - "What material is it made of?"
   - "Do you have it in oak?"

3. **Return Policy**
   - "What's your return policy?"
   - "Can I return if I change my mind?"
   - "How do I initiate a return?"

4. **Shipping Inquiry**
   - "How much is shipping?"
   - "Do you offer free shipping?"
   - "How long does delivery take?"

5. **Contact Information**
   - "How can I contact you?"
   - "What are your hours?"
   - "Do you have a physical store?"

---

## Advanced Features

### Product Memory
```python
session.update_shown_products([
    {"id": "CHR-001", "name": "Office Chair"},
    {"id": "TBL-005", "name": "Dining Table"}
])

# Resolve references
product_id = session.resolve_product_reference("1", "index")
# → "CHR-001"
```

### Cart Management (Local State)
```python
session.add_to_cart("CHR-001", quantity=2)
session.remove_from_cart("CHR-001")
session.clear_cart()
```

### Session Expiration
Sessions expire after 30 minutes of inactivity (configurable).

---

## Integration Points

### Node.js Backend
Cart operations need integration with Node.js cart service:

```python
# In tools.py update_cart method
async def update_cart(self, action, product_id, quantity, session_id):
    # TODO: HTTP POST to Node.js
    response = await httpx.post(
        f"{settings.NODE_BACKEND_URL}/cart/{action}",
        json={"product_id": product_id, "quantity": quantity},
        headers={"Session-ID": session_id}
    )
    return response.json()
```

### Shopify Catalog
Product data sourced from Shopify via catalog indexing:
- Products indexed in ChromaDB + BM25
- Specs stored as documents
- Search via hybrid retrieval

---

## Performance

- **LLM Latency**: ~1-2s per request (Hugging Face Inference API)
- **Tool Execution**: <100ms (local search/policies), varies for cart (Node.js)
- **Session Lookup**: <1ms (in-memory)
- **Total Response Time**: ~1.5-3s typical

### Optimization
- Use larger HF endpoints for faster inference
- Cache policy/contact responses
- Implement Redis for session store (production)
- Batch tool calls when possible

---

## Limitations & TODOs

### Current Limitations
1. **In-Memory Sessions**: Not suitable for multi-instance deployment
   - **Solution**: Implement Redis session store

2. **Mock Cart Integration**: Cart operations not connected to Node.js
   - **Solution**: HTTP API calls to Node.js backend

3. **Rule-Based Intent Detection**: May misclassify complex queries
   - **Solution**: Fine-tune ML intent classifier

4. **No Inventory Integration**: Stock checks return mock data
   - **Solution**: Connect to Shopify inventory API

5. **Context Window**: Limited to 8K tokens (Mistral-7B)
   - **Solution**: Implement context pruning or upgrade to larger model

### Future Enhancements
- [ ] Redis session store for scalability
- [ ] Node.js cart API integration
- [ ] ML-based intent classification
- [ ] Shopify inventory integration
- [ ] Multi-turn dialogue state tracking
- [ ] Conversation analytics dashboard
- [ ] A/B testing for prompt variations
- [ ] Support for images in responses
- [ ] Voice input/output support

---

## Error Handling

The assistant handles errors gracefully:

```python
try:
    response = await handler.handle_message(request)
except Exception as e:
    # Returns user-friendly error message
    # Logs full error for debugging
    # Tracks error event for monitoring
```

Common errors:
- **Model Loading (503)**: HF API loading model, auto-retries 3x
- **Invalid API Key (401)**: Check HUGGINGFACE_API_KEY in .env
- **Timeout (504)**: Increase HUGGINGFACE_TIMEOUT setting
- **Session Not Found (404)**: Session expired or invalid ID

---

## Monitoring

Events tracked via `EventTracker`:
- `assistant_request`: User message received
- `assistant_response_success`: Response generated
- `assistant_error`: Error occurred
- `function_call`: Tool executed

Metrics tracked via `MetricsCollector`:
- Response time
- Function calls per request
- Session count
- Error rate

---

## Example Conversations

### Conversation 1: Office Chair Purchase

```
User: Hi, I need an office chair
Assistant: G'day! Welcome to Easymart. I can help you find the perfect office chair. 
          What's your budget, and do you have any style preferences (modern, ergonomic, executive)?

User: Something ergonomic under $250
Assistant: Great choice! Here are 3 ergonomic office chairs under $250:
          1. Modern Mesh Chair - $199 (breathable mesh back, adjustable height)
          2. Ergonomic Task Chair - $229 (lumbar support, 120kg capacity)
          3. Budget Ergo Chair - $149 (basic ergonomic design)
          Would you like more details on any of these?

User: What are the dimensions of the first one?
Assistant: The Modern Mesh Chair (CHR-001) measures:
          - Width: 60cm
          - Depth: 58cm
          - Height: 95cm (adjustable 85-105cm)
          - Seat height: 45-55cm
          - Weight capacity: 120kg
          Perfect for standard desks!

User: Add it to my cart
Assistant: Excellent choice! I've added the Modern Mesh Chair ($199) to your cart.
          Your current total is $199. Just so you know, add $1 more for free shipping! 😊
          Would you like to continue shopping or proceed to checkout?
```

### Conversation 2: Return Policy

```
User: What's your return policy?
Assistant: **Returns Policy:**
          - Return period: 30 days from purchase
          - Condition: Items must be unused, in original packaging with all tags
          - Process: Contact our customer service to initiate return. Return shipping may apply.
          - Refund: Original payment method within 5-10 business days
          - Exclusions: Custom items, final sale items, and mattresses cannot be returned
          
          Change of mind returns are accepted within 30 days with return shipping fee.
          Need help with a return?
```

---

## Support

For issues or questions:
- Check logs: `backend-python/logs/`
- Review error events in observability module
- Contact: support@easymart.com.au
- GitHub Issues: [repository URL]

---

**Built with ❤️ for Easymart by the AI Team**
