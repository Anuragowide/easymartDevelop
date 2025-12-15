# C4 Component Diagram

Container: backend-node (Node.js)
Components:

modules/web/
  • ChatController (routes/chat.route.ts)
  • HealthController
  • WidgetController (ui/chat-widget.js)
  • WebModule Registrar

modules/shopify_adapter/
  • client.ts (Shopify API wrapper)
  • products.ts
  • cart.ts
  • index.ts (public API)

modules/observability/
  • logger.ts

utils/
  • httpClient.ts (internal axios wrapper)
  • session.ts

config/
  • env.ts

Responsibilities:
Acts as UI-facing API gateway.
Forwards chat messages to Python.
Handles Shopify operations (add to cart, get PDP details).
Serves chat widget script.

###
Container: backend-python (Assistant, Retrieval, Catalog)
Components:
modules/assistant/
  • handle_message.py
  • intents.py
  • tools.py      (search, spec, cart proxy calls)
  • session_store.py
  • assistant.py

modules/retrieval/
  • product_search.py
  • spec_search.py
  • index_store_client.py
  • retrieval.py

modules/catalog_index/
  • models/product.py
  • models/spec_doc.py
  • load_catalog.py
  • catalog.py (lookup, normalization)

modules/observability/
  • logger.py
  • events.py

api/
  • assistant_api.py (POST /assistant/message)
  • health_api.py

Responsibilities:
Interpret user intent with LLM.
Execute tool functions (search, cart).
Perform hybrid BM25 + vector retrieval.
Answer spec-based questions grounded in product specs.
Maintain session context.
Provide structured logs.
##
Container: Retrieval Index Store
Components

products_index (text + embeddings)

product_specs_index (snippets + embeddings)

Responsibilities:
Fast hybrid search
Snippet scoring for Q&A
##
Container: Shopify
Components

Admin API

Storefront API

Responsibilities:
Real product catalog
Metafields/specs (if stored here)
Cart CRUD
PDP URL generation