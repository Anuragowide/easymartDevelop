# API Contracts

## Internal Catalog Export API

**Consumer**: Python Backend (Catalog Indexer)  
**Provider**: Node.js Backend (Shopify Adapter)

### Endpoint
`GET /api/internal/catalog/export`

### Description
Returns a normalized list of all active products from the Shopify store. This data is used to build the vector and keyword search indexes in the Python backend.

### Response Format
**Content-Type**: `application/json`

**Body**: Array of `Product` objects.

```json
[
  {
    "sku": "SNOW-BOARD-001",
    "title": "Premium Snowboard",
    "description": "A high-performance snowboard for all terrains.",
    "price": 450.00,
    "currency": "AUD",
    "category": "Winter Sports",
    "tags": ["snow", "winter", "sports", "outdoor"],
    "image_url": "https://cdn.shopify.com/s/files/.../snowboard.jpg",
    "vendor": "Burton",
    "handle": "premium-snowboard"
  },
  {
    "sku": "SKI-GOGGLES-X",
    "title": "Anti-Fog Ski Goggles",
    "description": "Clear vision in all weather conditions.",
    "price": 89.99,
    "currency": "AUD",
    "category": "Accessories",
    "tags": ["goggles", "skiing", "safety"],
    "image_url": "https://cdn.shopify.com/s/files/.../goggles.jpg",
    "vendor": "Oakley",
    "handle": "anti-fog-ski-goggles"
  }
]
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sku` | String | Yes | Unique Stock Keeping Unit. Used as the primary ID. |
| `title` | String | Yes | Product display name. |
| `description` | String | Yes | Full product description (HTML stripped preferred). |
| `price` | Number | Yes | Current selling price. |
| `currency` | String | Yes | Currency code (e.g., "AUD"). |
| `category` | String | No | Main product category. |
| `tags` | Array<String> | No | List of tags for filtering. |
| `image_url` | String | No | URL to the main product image. |
| `vendor` | String | No | Brand or manufacturer name. |
| `handle` | String | Yes | Shopify handle (slug) for generating links. |

### Error Handling
- **500 Internal Server Error**: If the adapter cannot fetch data from Shopify.
- **Timeout**: The Python client has a 30-second timeout.
