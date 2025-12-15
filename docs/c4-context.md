# C4 Context Diagram

System Context Diagram (Text Version):

System: Easymart Conversational Commerce Platform (Your Application)

Primary Users:
  • Shopify Shoppers
    - Browse store
    - Use chat widget to search products, ask questions, add to cart
  • Store Admins
    - Install the app
    - Manage API keys, Shopify permissions

External Systems:
  • Shopify Storefront API
    - Product pages (PDP URLs)
    - Cart operations via Storefront API
  • Shopify Admin API
    - Get product data
    - Fetch metafields/specs
    - Manage carts if needed
  • Retrieval Index Store
    - products_index
    - product_specs_index
  • LLM API (Mistral AI, OpenAI, Anthropic, etc.)
    - Intent detection
    - Tool call orchestration

Your System:
  • frontend/ (optional)
  • backend-node/
  • backend-python/
  • infra/

Relationships:
  • Users → Shopify Storefront → Embedded Chat Widget → backend-node → backend-python → retrieval + Shopify.

