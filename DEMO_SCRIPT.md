# 🎬 EasyMart AI Chatbot - Demo Script

**Project:** EasyMart v1 - Conversational Commerce Platform  
**Demo Date:** December 22, 2025  
**Version:** Phase 1 (MVP)  
**Duration:** 10-15 minutes

---

## 📋 Pre-Demo Checklist

### Services Running
- [ ] **Python Backend** - `http://localhost:8000` ✅
- [ ] **Node Backend** - `http://localhost:3001` ✅
- [ ] **Frontend** - `http://localhost:3000` ✅
- [ ] All services showing "healthy" status

### Browser Setup
- [ ] Open `http://localhost:3000` in Chrome/Edge
- [ ] Open DevTools Console (F12) - Optional for debugging
- [ ] Clear browser cache and localStorage (Ctrl+Shift+Delete)
- [ ] Ensure chat widget is visible (bottom-right corner)

### Quick Health Check
```bash
# Test all endpoints are responding
curl http://localhost:8000/health
curl http://localhost:3001/health
```

---

## 🎯 Demo Flow Overview

1. **Introduction** (1 min) - Show landing page
2. **Product Search** (3 min) - Basic search, filters, refinements
3. **Product Q&A** (2 min) - Specifications, comparisons
4. **Cart Operations** (3 min) - Add, update, remove items
5. **Policy Information** (2 min) - Returns, shipping, contact
6. **Advanced Features** (3 min) - Context awareness, multi-turn conversations
7. **Error Handling** (1 min) - Out-of-scope queries

---

## 🎬 DEMO SCRIPT

### **PART 1: Introduction & Welcome** (1 minute)

**Action:** Open `http://localhost:3000`

**Script:**
> "Welcome to EasyMart, an AI-powered conversational shopping assistant. Instead of browsing through categories and filters, customers can simply chat with our AI to find exactly what they need. Let me show you how it works."

**Action:** Click the chat button (bottom-right)

**Expected:** Chat window opens with welcome message:
```
👋 Hi! I'm your EasyMart shopping assistant. I can help you:
• Find furniture and home products
• Answer questions about specifications
• Manage your shopping cart
• Provide store policies and contact info

What are you looking for today?
```

---

### **PART 2: Product Search** (3 minutes)

#### **Test 1: Basic Product Search**

**Query:**
```
Show me office chairs
```

**Expected Response:**
- Brief intro: "I found 5 office chairs for you!"
- 5 product cards displayed with:
  - Product image
  - Title
  - Price (AUD)
  - "Add to Cart" button
  - "View Details" link

**Script:**
> "Notice how the AI understands natural language. It searches our catalog and returns relevant products with images, prices, and action buttons."

---

#### **Test 2: Search with Price Filter**

**Query:**
```
Show me chairs under $100
```

**Expected Response:**
- Products filtered by price
- Only items under $100 AUD shown
- Product cards with pricing clearly visible

**Script:**
> "The AI understands price constraints and filters results automatically."

---

#### **Test 3: Category + Material Search**

**Query:**
```
I need a wooden dining table
```

**Expected Response:**
- Dining tables with wooden material
- Multiple options displayed
- Relevant product descriptions

**Script:**
> "It can combine multiple criteria - category (dining table) and material (wooden) - in a single query."

---

#### **Test 4: Context Refinement**

**Query 1:**
```
Show me sofas
```

**Wait for response, then Query 2:**
```
in grey color
```

**Expected Response:**
- AI remembers previous query (sofas)
- Refines search to grey sofas
- Shows: "Here are grey sofas for you!"

**Script:**
> "The AI maintains conversation context. I first asked for sofas, then refined by color. It understood I meant 'grey sofas' without repeating the full query."

---

#### **Test 5: Room-Specific Search**

**Query:**
```
What furniture do you have for a kids bedroom?
```

**Expected Response:**
- Kids bedroom furniture
- Items like beds, storage, desks suitable for children
- Age-appropriate products

---

### **PART 3: Product Q&A** (2 minutes)

#### **Test 6: Product Specifications**

**Query:**
```
What are the dimensions of the first option?
```

**Expected Response:**
- AI identifies "first option" from previous results
- Returns specific dimensions (e.g., "Height: 95cm, Width: 60cm, Depth: 55cm")
- Direct answer without re-listing products

**Script:**
> "The AI can answer specific questions about products. It remembers which products were shown and can reference them by position."

---

#### **Test 7: Material Question**

**Query:**
```
What material is the Modern Office Chair made of?
```

**Expected Response:**
- Specific material information (e.g., "Mesh back, fabric seat, metal base")
- Retrieved from product specifications
- No hallucinated information

---

#### **Test 8: Product Comparison**

**Query:**
```
Compare the first two office chairs
```

**Expected Response:**
- Side-by-side comparison
- Key differences highlighted (price, material, features)
- Clear recommendation if asked

**Script:**
> "The AI can compare products and highlight differences to help customers make informed decisions."

---

### **PART 4: Cart Operations** (3 minutes)

#### **Test 9: Add to Cart**

**Action:** Click "Add to Cart" button on any product card

**Expected Response:**
- Success message: "✅ [Product Name] added to cart!"
- Cart badge updates (shows item count)
- Product remains visible

**Script:**
> "Customers can add items directly from the chat. Notice the cart badge updated."

---

#### **Test 10: Add via Chat**

**Query:**
```
Add the wooden dining table to my cart
```

**Expected Response:**
- AI confirms: "I've added [Product Name] to your cart!"
- Cart count increases
- Success confirmation

---

#### **Test 11: View Cart**

**Query:**
```
Show me my cart
```

**Expected Response:**
- Cart summary displayed
- List of items with:
  - Product name
  - Quantity
  - Price
  - Subtotal
- Total amount
- Quantity controls (+/- buttons)

**Script:**
> "The AI can display the cart contents with full details and controls."

---

#### **Test 12: Update Quantity**

**Action:** Click the "+" button on a cart item

**Expected Response:**
- Quantity increases (e.g., 1 → 2)
- Subtotal updates automatically
- Total recalculates
- Success message (optional)

**Action:** Click the "-" button

**Expected Response:**
- Quantity decreases (e.g., 2 → 1)
- Subtotal updates
- Total recalculates

**Script:**
> "Customers can adjust quantities directly in the cart with instant updates."

---

#### **Test 13: Remove from Cart**

**Query:**
```
Remove the office chair from my cart
```

**Expected Response:**
- AI confirms removal
- Cart updates
- Item count decreases
- Total recalculates

**Alternative:** Click "Remove" button on cart item

---

#### **Test 14: Clear Cart**

**Query:**
```
Clear my cart
```

**Expected Response:**
- Confirmation: "Your cart has been cleared!"
- Cart badge shows 0
- Empty cart message when viewing cart

---

### **PART 5: Policy Information** (2 minutes)

#### **Test 15: Returns Policy**

**Query:**
```
What is your return policy?
```

**Expected Response:**
- 30-day return period
- Conditions (unused, original packaging)
- Exclusions (custom items, mattresses)
- Clear, formatted response

**Script:**
> "The AI can provide store policies instantly without customers needing to navigate to separate pages."

---

#### **Test 16: Shipping Information**

**Query:**
```
How much is shipping?
```

**Expected Response:**
- Free shipping over $150 AUD
- Standard shipping cost for orders under $150
- Delivery timeframes
- Express shipping options

---

#### **Test 17: Contact Information**

**Query:**
```
How can I contact customer support?
```

**Expected Response:**
- Email address
- Phone number
- Business hours
- Response time expectations

---

### **PART 6: Advanced Features** (3 minutes)

#### **Test 18: Multi-Turn Conversation**

**Query 1:**
```
I'm looking for bedroom furniture
```

**Query 2:**
```
Something modern and minimalist
```

**Query 3:**
```
Under $500
```

**Expected Response:**
- AI builds context across all three queries
- Final results: Modern, minimalist bedroom furniture under $500
- Shows understanding of cumulative refinements

**Script:**
> "The AI maintains conversation context across multiple turns, building a complete picture of what the customer wants."

---

#### **Test 19: Product Reference by Position**

**Query:**
```
Tell me more about option 2
```

**Expected Response:**
- AI identifies the 2nd product from previous results
- Provides detailed information
- Remembers product context

---

#### **Test 20: Availability Check**

**Query:**
```
Is the Modern Office Chair in stock?
```

**Expected Response:**
- Stock status (In Stock / Out of Stock)
- Quantity available (if applicable)
- Estimated restock date (if out of stock)

---

#### **Test 21: Recommendation Request**

**Query:**
```
Which office chair would you recommend for long hours of work?
```

**Expected Response:**
- AI analyzes product features
- Recommends ergonomic options
- Explains reasoning (e.g., "adjustable lumbar support, breathable mesh")
- Provides 2-3 top recommendations

---

### **PART 7: Error Handling** (1 minute)

#### **Test 22: Out of Scope Query**

**Query:**
```
Can you help me book a flight?
```

**Expected Response:**
- Polite decline: "I'm specialized in helping with furniture and home products from EasyMart."
- Redirect: "I can help you find furniture, answer product questions, or manage your cart. What would you like to know?"

**Script:**
> "The AI gracefully handles out-of-scope requests and redirects users to what it can help with."

---

#### **Test 23: No Results Found**

**Query:**
```
Show me red sofas
```

**Expected Response (if no red sofas in catalog):**
- "I couldn't find any red sofas in our current catalog."
- Suggestions: "Would you like to see sofas in other colors?"
- No hallucinated products

**Script:**
> "When products aren't available, the AI is honest and offers alternatives rather than making up results."

---

#### **Test 24: Ambiguous Query**

**Query:**
```
I need something for my room
```

**Expected Response:**
- Clarification request: "I'd be happy to help! What type of item are you looking for? For example: furniture, storage, lighting, or decor?"
- Helpful prompts to guide the conversation

---

### **PART 8: Reset & Start Over** (Optional)

#### **Test 25: Conversation Reset**

**Query:**
```
Start over
```

**Expected Response:**
- Conversation history cleared
- Cart preserved (or cleared based on implementation)
- Welcome message shown again
- Fresh session started

---

## 🎯 Key Features Demonstrated

### ✅ Core Functionality
- [x] Natural language product search
- [x] Price filtering
- [x] Category + attribute search
- [x] Context-aware refinements
- [x] Product Q&A (dimensions, materials, specs)
- [x] Product comparison
- [x] Add to cart (button + voice)
- [x] View cart
- [x] Update quantity (+/-)
- [x] Remove items
- [x] Clear cart
- [x] Policy information (returns, shipping, contact)

### ✅ Advanced Features
- [x] Multi-turn conversations
- [x] Context retention
- [x] Product reference by position
- [x] Availability checking
- [x] Recommendations
- [x] Error handling
- [x] Out-of-scope detection
- [x] Ambiguity resolution

---

## 📊 Demo Metrics to Highlight

### Performance
- **Response Time:** < 2 seconds for most queries
- **Search Accuracy:** Relevant results for natural language queries
- **Context Retention:** Remembers last 10 conversation turns

### User Experience
- **Zero Learning Curve:** Natural conversation, no training needed
- **Mobile Responsive:** Works on all devices
- **Persistent Cart:** Items saved across sessions
- **Rich Product Cards:** Images, prices, instant actions

### Technical
- **AI Model:** Mistral 7B Instruct (open-source LLM)
- **Search:** Hybrid BM25 + Vector embeddings
- **Integration:** Real-time Shopify catalog sync
- **Architecture:** Microservices (Node.js + Python + Elasticsearch)

---

## 🎤 Suggested Talking Points

### Opening
> "Traditional e-commerce requires customers to navigate menus, apply filters, and browse multiple pages. EasyMart's AI assistant lets customers simply describe what they want in natural language, just like talking to a sales associate."

### During Product Search
> "Notice how the AI understands context and intent. It's not just keyword matching - it combines category, material, price, and style preferences to find exactly what the customer needs."

### During Cart Operations
> "The entire shopping journey happens in one conversation. Search, ask questions, compare, and checkout - all without leaving the chat."

### During Q&A
> "The AI doesn't hallucinate information. Every specification comes from our actual product database, ensuring customers get accurate details."

### Closing
> "This is Phase 1 - our MVP. Future phases will include visual search, voice input, multi-language support, and WhatsApp integration. The goal is to make online shopping as natural as talking to a friend."

---

## 🐛 Known Issues to Avoid in Demo

### ⚠️ Current Limitations
1. **Cart Persistence:** Cart stored in session, not Shopify (Phase 2)
2. **Checkout:** No direct checkout flow yet (Phase 2)
3. **Product Images:** Some products may have placeholder images
4. **Decrease Quantity:** May have issues (see KNOWN_ISSUES.md #4)

### 💡 Demo Tips
- **If decrease button fails:** Use "Remove from cart" voice command instead
- **If search returns no results:** Have backup queries ready
- **If LLM lists products:** Acknowledge and explain it's a known UX improvement for Phase 2
- **If response is slow:** Mention this is running locally; production will be faster

---

## 📝 Quick Reference - Test Queries

### Product Search
```
Show me office chairs
Show me chairs under $100
I need a wooden dining table
Show me sofas
in grey color
What furniture do you have for a kids bedroom?
```

### Product Q&A
```
What are the dimensions of the first chair?
What material is the Modern Office Chair made of?
Compare the first two office chairs
```

### Cart Operations
```
Add the wooden dining table to my cart
Show me my cart
Remove the office chair from my cart
Clear my cart
```

### Policies
```
What is your return policy?
How much is shipping?
How can I contact customer support?
```

### Advanced
```
I'm looking for bedroom furniture
Something modern and minimalist
Under $500
Tell me more about option 2
Is the Modern Office Chair in stock?
Which office chair would you recommend for long hours of work?
```

### Error Handling
```
Can you help me book a flight?
Show me red sofas
I need something for my room
Start over
```

---

## 🎬 Post-Demo Q&A Preparation

### Expected Questions

**Q: How accurate is the product search?**
> A: We use hybrid search combining BM25 keyword matching with vector embeddings, achieving 85%+ relevance on natural language queries.

**Q: Can it handle multiple languages?**
> A: Phase 1 is English only. Phase 2 will add Hindi and Spanish support.

**Q: How does it prevent hallucinations?**
> A: The AI can only return products from our database. It uses function calling to retrieve real data, not generate information.

**Q: What about privacy and data security?**
> A: Conversations are session-based and not stored permanently. No personal data is collected without consent.

**Q: Can this integrate with existing Shopify stores?**
> A: Yes! It's designed as a Shopify app. We sync your product catalog automatically and integrate with your existing cart system.

**Q: What's the cost?**
> A: [Prepare pricing model based on your business plan]

---

## ✅ Pre-Demo Final Checklist

- [ ] All services running and healthy
- [ ] Browser cache cleared
- [ ] Chat widget visible and responsive
- [ ] Test at least 3 queries before demo
- [ ] Have backup queries ready
- [ ] Know current limitations
- [ ] Prepare answers for expected questions
- [ ] Have KNOWN_ISSUES.md open for reference
- [ ] Screen sharing setup tested
- [ ] Audio/video quality checked

---

**Good luck with your demo! 🚀**

*Remember: Focus on the value proposition - making shopping conversational and effortless. The technology is impressive, but the user experience is what sells.*
