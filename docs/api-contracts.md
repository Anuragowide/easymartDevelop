# API Contracts


docs/api-contracts.md — human-readable API contract

Create easymart-v1/docs/api-contracts.md with this content:
# API Contracts — Easymart v1

This document lists the HTTP APIs and payload contracts between components:
- Node backend (frontend-facing, Shopify adapter)
- Python assistant (LLM orchestration)
- Chat widget (front-end script)

---

## 1. POST /api/chat
**Path:** `POST /api/chat` (Node)

**Purpose:** Receive message from chat widget, forward to Python assistant, and return assistant response suitable for widget rendering.

**Request JSON:**
```json
{
  "sessionId": "string (optional)",
  "message": "string"
}

Response JSON (example):
{
  "replyText": "string",
  "cards": [
    {
      "id": "sku-123",
      "title": "ErgoTask Office Chair",
      "imageUrl": "https://...",
      "price": 9999,
      "currency": "INR",
      "shortDescription": "Comfortable office chair...",
      "productUrl": "https://easymart.myshopify.com/products/ergo"
    }
  ],
  "action": "none | show_cards | show_spec | ask_clarify",
  "meta": { "rawAssistantPayload": {} }
}
Notes:

Node backend acts as a proxy. It may enrich response with local product URLs or transform card shape.

2. Python Assistant API — Node → Python

Path: POST /assistant/message

Purpose: Main orchestration endpoint used by Node to get a structured assistant reply.

Request JSON:
{
  "sessionId": "string",
  "message": "string"
}

Response JSON:
{
  "replyText": "string",
  "intent": "PRODUCT_SEARCH | CART_ADD | CART_REMOVE | CART_SHOW | PRODUCT_SPEC_QA | NONE",
  "cards": [ /* ProductCard */ ],
  "ask": null,
  "toolCalls": [ /* optional - tool invocation trace */ ],
  "error": null
}

3. Shopify Adapter Called Locally (internal Node)

These functions are internal to Node and not exposed externally but have defined shapes:

getProductDetails(productId: string) => Promise<Product>

searchProducts(query: string) => Promise<Product[]>

addToCart(sessionId: string, productId: string, quantity: number) => Promise<Cart>

getCart(sessionId: string) => Promise<Cart>

Product / Cart shapes are given in the shared schemas (see docs/shared-schemas.md).

4. Widget Static Assets:
GET /widget/static/chat-widget.js
GET /widget/static/chat-widget.css
They are static files served by Node. Widget calls POST /api/chat.

5. Health Checks:
GET /health (Node)
GET /api/health (Node module)

6. Error Handling:
All endpoints return 4xx/5xx on errors with body
{ "error": "string", "details": {} }

Integration notes

SessionId is primary way to map lastShownProducts for index references.

Node validates request shape and forwards to Python. Python returns structured payload that Node then returns to widget.\

---

# 3) `docker-compose.yml` for Node + Python + Elasticsearch

Create `easymart-v1/infra/docker-compose.yml`:

```yaml
version: "3.8"

services:
  node:
    build:
      context: ../backend-node
    env_file:
      - ../backend-node/.env
    volumes:
      - ../backend-node:/usr/src/app
      - /usr/src/app/node_modules
    ports:
      - "3001:3001"
    depends_on:
      - python
      - elasticsearch
    networks:
      - easymart-net

  python:
    build:
      context: ../backend-python
    env_file:
      - ../backend-python/.env
    volumes:
      - ../backend-python:/app
    ports:
      - "8000:8000"
    networks:
      - easymart-net

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.2
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
      - "xpack.security.enabled=false"
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - esdata:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - easymart-net

volumes:
  esdata:
    driver: local

networks:
  easymart-net:
    driver: bridge
Notes:
If your retrieval stack uses Weaviate or Qdrant, swap the elasticsearch service accordingly.
For production or CI, tune memory and persistence.

4) OpenAPI contract between Node ⇄ Python (YAML)
Create easymart-v1/docs/openapi-assistant.yaml:
openapi: 3.0.3
info:
  title: Easymart Assistant API
  version: "1.0.0"
  description: API used by Node backend to call the Python assistant.

servers:
  - url: http://localhost:8000
    description: Local Python assistant

paths:
  /assistant/message:
    post:
      summary: Send a user message to assistant
      operationId: postAssistantMessage
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AssistantRequest'
      responses:
        '200':
          description: Assistant response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssistantResponse'
        '400':
          description: Bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:
    AssistantRequest:
      type: object
      required:
        - sessionId
        - message
      properties:
        sessionId:
          type: string
          example: "sess-abc123"
        message:
          type: string
          example: "Show me ergonomic office chairs under 10000"
        meta:
          type: object
          description: Optional metadata (user locale, device)
    AssistantResponse:
      type: object
      properties:
        replyText:
          type: string
          description: Plain text primary reply
        intent:
          type: string
          description: Inferred intent name
          example: "PRODUCT_SEARCH"
        cards:
          type: array
          items:
            $ref: '#/components/schemas/ProductCard'
        action:
          type: string
          example: "show_cards"
        toolCalls:
          type: array
          items:
            type: object
            description: Trace of tool calls executed by assistant (optional)
        error:
          type: object
          nullable: true
    ProductCard:
      type: object
      required: ["id","title","productUrl"]
      properties:
        id: { type: string }
        title: { type: string }
        subtitle: { type: string }
        imageUrl: { type: string }
        price:
          type: number
        currency:
          type: string
        shortDescription:
          type: string
        productUrl:
          type: string
    ErrorResponse:
      type: object
      properties:
        error:
          type: string
        details:
          type: object


Save this file and use it to align Node and Python teams.

5) Shared schemas (TypeScript + Pydantic + JSON Schema)

Create docs/shared-schemas.md (or add to docs/).

TypeScript interfaces (for Node)
Create src/types/shared.ts (or docs copy):
export interface AssistantRequest {
  sessionId: string;
  message: string;
  meta?: Record<string, any>;
}

export interface ProductCard {
  id: string;
  title: string;
  subtitle?: string;
  imageUrl?: string;
  price?: number;
  currency?: string;
  shortDescription?: string;
  productUrl: string;
}

export interface AssistantResponse {
  replyText?: string;
  intent?: "PRODUCT_SEARCH" | "CART_ADD" | "CART_REMOVE" | "CART_SHOW" | "PRODUCT_SPEC_QA" | "NONE";
  cards?: ProductCard[];
  action?: string;
  toolCalls?: any[];
  error?: { message: string; code?: string };
}

Pydantic models (for Python assistant)

Create backend-python/app/core/schemas.py (or update existing):
from pydantic import BaseModel
from typing import List, Optional, Any

class AssistantRequest(BaseModel):
    sessionId: str
    message: str
    meta: Optional[dict] = None

class ProductCard(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    imageUrl: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    shortDescription: Optional[str] = None
    productUrl: str

class AssistantResponse(BaseModel):
    replyText: Optional[str] = None
    intent: Optional[str] = None
    cards: Optional[List[ProductCard]] = None
    action: Optional[str] = None
    toolCalls: Optional[List[Any]] = None
    error: Optional[dict] = None

JSON Schema (optional) — docs/schemas.json snippet
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "AssistantRequest": {
      "type": "object",
      "required": ["sessionId", "message"],
      "properties": {
        "sessionId": { "type": "string" },
        "message": { "type": "string" }
      }
    },
    "ProductCard": {
      "type": "object",
      "required": ["id", "title", "productUrl"],
      "properties": {
        "id": { "type": "string" },
        "title": { "type": "string" },
        "productUrl": { "type": "string" }
      }
    }
  }
}

