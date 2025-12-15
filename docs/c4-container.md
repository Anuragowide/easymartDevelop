# C4 Container Diagram

Container Diagram (Based on Your Directory Structure)

┌──────────────────────────────────────────────────────────────────────────┐
│                    Easymart Conversational Platform                      │
│                          (Multi-container Monolith)                      │
└──────────────────────────────────────────────────────────────────────────┘

Containers:

1. FRONTEND (Optional Next.js)
   • Location: /frontend
   • Displays demo UI (if needed)
   • Not required for embedded chat widget
   • Communicates → backend-node

2. NODE BACKEND (API Gateway + Web Layer + Shopify Adapter)
   • Location: /backend-node
   • Responsibilities:
       - Serve chat widget script
       - Handle /api/chat requests from widget
       - Forward chat messages → Python assistant
       - Manage Shopify API (products, cart)
       - Logging
   • Communicates:
       - Calls backend-python (assistant API)
       - Calls Shopify Admin API
       - Serves widget to storefront

3. PYTHON BACKEND (Assistant + Retrieval + Catalog)
   • Location: /backend-python
   • Responsibilities:
       - LLM orchestration (intent detection)
       - Tool call execution
       - Retrieval search (BM25 + vector)
       - Product spec search
       - Catalog model + product normalization
       - Session memory
   • Communicates:
       - Calls LLM provider API
       - Calls Retrieval Index Store

4. RETRIEVAL INDEX STORE
   • Location: /infra/search-index
   • Responsibilities:
       - Store product embeddings + BM25 index
       - Support search and spec Q&A

5. SHOPIFY (External)
   • Shopify Admin API
   • Shopify Storefront API
   • Provides:
       - Product data
       - PDP URLs
       - Cart operations

6. USERS & SHOPIFY STOREFRONT
   • Users interact with your chat widget
   • Widget connects to backend-node

