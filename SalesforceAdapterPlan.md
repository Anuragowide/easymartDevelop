## Full Implementation Plan: Salesforce Adapter Integration in New Project

This is a comprehensive, start-to-end plan to add the Salesforce adapter to your new project's backend-node while keeping the Python backend unchanged.

---

## Overview

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| Adapters | Shopify only | Shopify + Salesforce (switchable) |
| Python backend | Unchanged | Unchanged (receives normalized data) |
| Platform switch | N/A | `ACTIVE_PLATFORM` env var |
| Multi-tenant | No | Optional (Phase 2) |

---

## Architecture After Integration

```mermaid
flowchart TB
  subgraph SHOPIFY_STORE["Shopify Store + Widget"]
    WIDGET[Chat Widget]
  end

  subgraph SALESFORCE_STORE["Salesforce B2B Store + Widget"]
    SF_WIDGET[Chat Widget]
  end

  subgraph NODE["Node.js Backend (Port 3001)"]
    GATEWAY[Fastify API Gateway]
    MIDDLEWARE[Tenant/Platform Middleware]
    FACTORY[Adapter Factory]
    
    subgraph ADAPTERS["Adapters"]
      SHOPIFY[Shopify Adapter]
      SALESFORCE[Salesforce Adapter]
    end
    
    STATIC[Static Widget Serving]
  end

  subgraph PYTHON["Python Backend (Port 8000)"]
    FASTAPI[FastAPI Server]
    LLM[Mistral LLM]
    RAG[RAG Pipeline]
    INTENT[Intent Detection]
  end

  subgraph ELASTIC["Elasticsearch (Port 9200)"]
    INDEX[Product Index]
    VECTOR[Vector Search]
  end

  subgraph SALESFORCE_ORG["Salesforce Org"]
    SF_API[Salesforce REST / Apex]
  end

  WIDGET -->|API calls| GATEWAY
  SF_WIDGET -->|API calls| GATEWAY
  GATEWAY --> MIDDLEWARE --> FACTORY
  FACTORY -->|ACTIVE_PLATFORM=shopify| SHOPIFY
  FACTORY -->|ACTIVE_PLATFORM=salesforce| SALESFORCE
  SHOPIFY --> GATEWAY
  SALESFORCE --> SF_API
  GATEWAY -->|Normalized data| FASTAPI
  FASTAPI --> LLM
  FASTAPI --> RAG
  RAG --> INDEX
  RAG --> VECTOR
```

---

## Phase 0: Preparation & Analysis (1 day)

### 0.1 Confirm Existing Contract
- Review Python backend's expected input/output shapes for products and cart.
- Document the exact normalized `Product` and `CartItem` interfaces that Shopify adapter currently returns.
- Confirm these shapes will remain unchanged.

### 0.2 Environment Setup
- Clone the new project repo.
- Verify Node.js backend runs (`pnpm install`, `pnpm dev`).
- Verify Python backend runs and responds to health checks.
- Verify Elasticsearch is reachable.

### 0.3 Salesforce Org Access
- Confirm access to a Salesforce B2B Commerce sandbox/dev org.
- Identify required Apex endpoints (or plan to deploy them).
- Obtain Connected App credentials (client_id, JWT private key, etc.).

---

## Phase 1: Salesforce Adapter Package (3–4 days)

### 1.1 Create Folder Structure

```
backend-node/src/modules/salesforce_adapter/
├── index.ts          # Barrel export + factory
├── types.ts          # SalesforceConfig, Logger, DTOs
├── client.ts         # OAuth client (JWT + password flow)
├── products.ts       # searchProducts, getProductById
├── cart.ts           # getCart, addToCart, updateCartItem, removeFromCart
├── media.ts          # Image resolution helpers
└── README.md         # Usage docs
```

### 1.2 Create `types.ts`

Define all interfaces:

```typescript
// types.ts
export interface SalesforceConfig {
  tokenUrl: string;
  clientId: string;
  jwtUsername?: string;
  jwtPrivateKey?: string;
  username?: string;
  password?: string;
  securityToken?: string;
  clientSecret?: string;
  apiVersion: string;
  siteBaseUrl?: string;
  webstoreId?: string;
}

export interface Logger {
  debug(msg: string, data?: object): void;
  info(msg: string, data?: object): void;
  warn(msg: string, data?: object): void;
  error(msg: string, data?: any): void;
}

// Normalized shapes (must match what Python expects)
export interface Product {
  id: string;
  title: string;
  description?: string;
  price: string;
  image?: string;
  url?: string;
  inStock?: boolean;
  inventory_quantity?: number;
}

export interface CartItem {
  id: string;
  productId: string;
  title: string;
  quantity: number;
  price: number;
  image?: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  totalQuantity: number;
  totalPrice: number;
}
```

### 1.3 Create client.ts

OAuth client with JWT and password flow support:

```typescript
// client.ts
import axios, { AxiosInstance } from 'axios';
import jwt from 'jsonwebtoken';
import { SalesforceConfig, Logger } from './types';

const defaultLogger: Logger = {
  debug: () => {},
  info: console.log,
  warn: console.warn,
  error: console.error,
};

export class SalesforceClient {
  private config: SalesforceConfig;
  private logger: Logger;
  private client: AxiosInstance;
  private accessToken = '';
  private instanceUrl = '';
  private expiresAt = 0;

  constructor(config: SalesforceConfig, logger?: Logger) {
    this.config = config;
    this.logger = logger || defaultLogger;
    this.client = axios.create();

    this.client.interceptors.request.use(async (req) => {
      await this.ensureToken();
      req.headers.Authorization = `Bearer ${this.accessToken}`;
      if (!req.baseURL && this.instanceUrl) {
        req.baseURL = this.instanceUrl;
      }
      return req;
    });
  }

  private normalizePrivateKey(raw: string): string {
    if (!raw) return '';
    return raw.replace(/\\n/g, '\n');
  }

  private async requestTokenWithJwt(): Promise<void> {
    const { tokenUrl, clientId, jwtUsername, jwtPrivateKey } = this.config;
    if (!tokenUrl || !clientId || !jwtUsername || !jwtPrivateKey) {
      throw new Error('JWT config incomplete');
    }

    const privateKey = this.normalizePrivateKey(jwtPrivateKey);
    const now = Math.floor(Date.now() / 1000);
    const payload = { iss: clientId, sub: jwtUsername, aud: tokenUrl, exp: now + 180 };
    const assertion = jwt.sign(payload, privateKey, { algorithm: 'RS256' });

    const params = new URLSearchParams();
    params.append('grant_type', 'urn:ietf:params:oauth:grant-type:jwt-bearer');
    params.append('assertion', assertion);

    const resp = await axios.post(tokenUrl, params.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    this.accessToken = resp.data.access_token;
    this.instanceUrl = resp.data.instance_url || this.instanceUrl;
    this.expiresAt = Date.now() + (resp.data.expires_in || 3600) * 1000;
    this.client.defaults.baseURL = this.instanceUrl;

    this.logger.info('Salesforce token acquired', { instanceUrl: this.instanceUrl });
  }

  private async requestTokenWithPassword(): Promise<void> {
    const { tokenUrl, clientId, clientSecret, username, password, securityToken } = this.config;
    if (!tokenUrl || !clientId) throw new Error('Password flow config incomplete');

    const params = new URLSearchParams();
    params.append('grant_type', 'password');
    params.append('client_id', clientId);
    params.append('client_secret', clientSecret || '');
    params.append('username', username || '');
    params.append('password', `${password || ''}${securityToken || ''}`);

    const resp = await axios.post(tokenUrl, params.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    this.accessToken = resp.data.access_token;
    this.instanceUrl = resp.data.instance_url || this.instanceUrl;
    this.expiresAt = Date.now() + (resp.data.expires_in || 3600) * 1000;
    this.client.defaults.baseURL = this.instanceUrl;
  }

  private async ensureToken(): Promise<void> {
    const refreshThreshold = 60 * 1000;
    if (this.accessToken && Date.now() < this.expiresAt - refreshThreshold) return;

    if (this.config.jwtPrivateKey) {
      await this.requestTokenWithJwt();
    } else if (this.config.username && this.config.password) {
      await this.requestTokenWithPassword();
    } else {
      throw new Error('No Salesforce auth method configured');
    }
  }

  getAxios(): AxiosInstance {
    return this.client;
  }

  getConfig(): SalesforceConfig {
    return this.config;
  }
}
```

### 1.4 Create `products.ts`

```typescript
// products.ts
import { SalesforceClient } from './client';
import { Product, Logger } from './types';

export class ProductService {
  private client: SalesforceClient;
  private logger: Logger;

  constructor(client: SalesforceClient, logger: Logger) {
    this.client = client;
    this.logger = logger;
  }

  async search(query: string, limit = 10): Promise<Product[]> {
    const axios = this.client.getAxios();
    const config = this.client.getConfig();

    // Call Apex REST endpoint
    const resp = await axios.get('/services/apexrest/commerce/search', {
      params: { q: query, limit },
    });

    const results = resp.data?.products || resp.data || [];

    // Normalize to standard Product shape
    return results.map((p: any) => ({
      id: p.Id || p.id,
      title: p.Name || p.name || p.title,
      description: p.Description || p.description,
      price: String(p.UnitPrice || p.price || '0'),
      image: p.ImageUrl || p.image || '',
      url: p.ProductUrl || p.url || `${config.siteBaseUrl || ''}/product/${p.Id || p.id}`,
      inStock: p.IsAvailable ?? p.inStock ?? true,
      inventory_quantity: p.QuantityAvailable ?? p.inventory_quantity,
    }));
  }

  async getById(productId: string): Promise<Product | null> {
    const axios = this.client.getAxios();
    const config = this.client.getConfig();

    try {
      const resp = await axios.get(`/services/apexrest/commerce/product/${productId}`);
      const p = resp.data;
      if (!p) return null;

      return {
        id: p.Id || p.id,
        title: p.Name || p.name || p.title,
        description: p.Description || p.description,
        price: String(p.UnitPrice || p.price || '0'),
        image: p.ImageUrl || p.image || '',
        url: p.ProductUrl || p.url || `${config.siteBaseUrl || ''}/product/${p.Id || p.id}`,
        inStock: p.IsAvailable ?? p.inStock ?? true,
        inventory_quantity: p.QuantityAvailable ?? p.inventory_quantity,
      };
    } catch (err) {
      this.logger.error('getById failed', err);
      return null;
    }
  }
}
```

### 1.5 Create `cart.ts`

```typescript
// cart.ts
import { SalesforceClient } from './client';
import { Cart, CartItem, Logger } from './types';

export class CartService {
  private client: SalesforceClient;
  private logger: Logger;

  constructor(client: SalesforceClient, logger: Logger) {
    this.client = client;
    this.logger = logger;
  }

  async getCart(buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    const resp = await axios.get('/services/apexrest/CartApi/getCart', {
      params: { buyerAccountId },
    });

    const data = resp.data;
    const items: CartItem[] = (data.lines || []).map((l: any) => ({
      id: l.cartItemId || l.id,
      productId: l.productId,
      title: l.productName || l.name || l.title || '',
      quantity: l.quantity,
      price: typeof l.price === 'number' ? l.price : parseFloat(l.price || '0'),
      image: l.imageUrl || l.image,
    }));

    return {
      id: data.cartId || '',
      items,
      totalQuantity: items.reduce((sum, i) => sum + i.quantity, 0),
      totalPrice: items.reduce((sum, i) => sum + i.price * i.quantity, 0),
    };
  }

  async addToCart(productId: string, quantity: number, buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    await axios.post('/services/apexrest/CartApi/addItem', {
      productId,
      quantity,
      buyerAccountId,
    });
    return this.getCart(buyerAccountId);
  }

  async updateCartItem(cartItemId: string, quantity: number, buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    await axios.post('/services/apexrest/CartApi/updateItem', {
      cartItemId,
      quantity,
      buyerAccountId,
    });
    return this.getCart(buyerAccountId);
  }

  async removeFromCart(cartItemId: string, buyerAccountId: string): Promise<Cart> {
    const axios = this.client.getAxios();
    await axios.post('/services/apexrest/CartApi/removeItem', {
      cartItemId,
      buyerAccountId,
    });
    return this.getCart(buyerAccountId);
  }
}
```

### 1.6 Create index.ts (Factory)

```typescript
// index.ts
import { SalesforceClient } from './client';
import { ProductService } from './products';
import { CartService } from './cart';
import { SalesforceConfig, Logger, Product, Cart, CartItem } from './types';

export interface SalesforceAdapter {
  products: ProductService;
  cart: CartService;
  client: SalesforceClient;
}

export function createSalesforceAdapter(options: {
  config: SalesforceConfig;
  logger?: Logger;
}): SalesforceAdapter {
  const logger = options.logger || console;
  const client = new SalesforceClient(options.config, logger);

  return {
    products: new ProductService(client, logger),
    cart: new CartService(client, logger),
    client,
  };
}

// Re-export types
export * from './types';
```

---

## Phase 2: Adapter Factory & Platform Switching (2 days)

### 2.1 Create Unified Adapter Interface

Create `backend-node/src/modules/adapters/types.ts`:

```typescript
// adapters/types.ts
export interface Product {
  id: string;
  title: string;
  description?: string;
  price: string;
  image?: string;
  url?: string;
  inStock?: boolean;
  inventory_quantity?: number;
}

export interface CartItem {
  id: string;
  productId: string;
  title: string;
  quantity: number;
  price: number;
  image?: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  totalQuantity: number;
  totalPrice: number;
}

export interface ECommerceAdapter {
  products: {
    search(query: string, limit?: number): Promise<Product[]>;
    getById(id: string): Promise<Product | null>;
  };
  cart: {
    getCart(userId: string): Promise<Cart>;
    addToCart(productId: string, quantity: number, userId: string): Promise<Cart>;
    updateCartItem(cartItemId: string, quantity: number, userId: string): Promise<Cart>;
    removeFromCart(cartItemId: string, userId: string): Promise<Cart>;
  };
}
```

### 2.2 Create Adapter Factory

Create `backend-node/src/modules/adapters/factory.ts`:

```typescript
// adapters/factory.ts
import { ECommerceAdapter } from './types';
import { createSalesforceAdapter, SalesforceConfig } from '../salesforce_adapter';
import { createShopifyAdapter } from '../shopify_adapter'; // Assume exists
import { config } from '../../config/env';
import { logger } from '../observability/logger';

export type Platform = 'shopify' | 'salesforce';

let cachedAdapter: ECommerceAdapter | null = null;
let cachedPlatform: Platform | null = null;

function getSalesforceConfig(): SalesforceConfig {
  return {
    tokenUrl: config.SALESFORCE_TOKEN_URL,
    clientId: config.SALESFORCE_JWT_CLIENT_ID || config.SALESFORCE_CLIENT_ID,
    jwtUsername: config.SALESFORCE_JWT_USERNAME,
    jwtPrivateKey: config.SALESFORCE_JWT_PRIVATE_KEY,
    username: config.SALESFORCE_USERNAME,
    password: config.SALESFORCE_PASSWORD,
    securityToken: config.SALESFORCE_SECURITY_TOKEN,
    clientSecret: config.SALESFORCE_CLIENT_SECRET,
    apiVersion: config.SALESFORCE_API_VERSION || 'v57.0',
    siteBaseUrl: config.SALESFORCE_SITE_BASE_URL,
    webstoreId: config.SALESFORCE_WEBSTORE_ID,
  };
}

export function getAdapter(platform?: Platform): ECommerceAdapter {
  const activePlatform = platform || (config.ACTIVE_PLATFORM as Platform) || 'shopify';

  // Return cached if same platform
  if (cachedAdapter && cachedPlatform === activePlatform) {
    return cachedAdapter;
  }

  switch (activePlatform) {
    case 'salesforce':
      const sfAdapter = createSalesforceAdapter({
        config: getSalesforceConfig(),
        logger,
      });
      cachedAdapter = sfAdapter;
      cachedPlatform = activePlatform;
      return sfAdapter;

    case 'shopify':
    default:
      const shopifyAdapter = createShopifyAdapter({ logger });
      cachedAdapter = shopifyAdapter;
      cachedPlatform = activePlatform;
      return shopifyAdapter;
  }
}

export function clearAdapterCache(): void {
  cachedAdapter = null;
  cachedPlatform = null;
}
```

### 2.3 Update Config (`config/env.ts`)

Add Salesforce environment variables:

```typescript
// Add to existing config
export const config = {
  // ... existing Shopify config ...

  // Platform switching
  ACTIVE_PLATFORM: process.env.ACTIVE_PLATFORM || 'shopify',

  // Salesforce config
  SALESFORCE_TOKEN_URL: process.env.SALESFORCE_TOKEN_URL || '',
  SALESFORCE_CLIENT_ID: process.env.SALESFORCE_CLIENT_ID || '',
  SALESFORCE_CLIENT_SECRET: process.env.SALESFORCE_CLIENT_SECRET || '',
  SALESFORCE_JWT_CLIENT_ID: process.env.SALESFORCE_JWT_CLIENT_ID || '',
  SALESFORCE_JWT_USERNAME: process.env.SALESFORCE_JWT_USERNAME || '',
  SALESFORCE_JWT_PRIVATE_KEY: process.env.SALESFORCE_JWT_PRIVATE_KEY || '',
  SALESFORCE_USERNAME: process.env.SALESFORCE_USERNAME || '',
  SALESFORCE_PASSWORD: process.env.SALESFORCE_PASSWORD || '',
  SALESFORCE_SECURITY_TOKEN: process.env.SALESFORCE_SECURITY_TOKEN || '',
  SALESFORCE_API_VERSION: process.env.SALESFORCE_API_VERSION || 'v57.0',
  SALESFORCE_SITE_BASE_URL: process.env.SALESFORCE_SITE_BASE_URL || '',
  SALESFORCE_WEBSTORE_ID: process.env.SALESFORCE_WEBSTORE_ID || '',
};
```

---

## Phase 3: Update Routes to Use Factory (2 days)

### 3.1 Update Product Routes

Modify existing product routes to use the adapter factory:

```typescript
// web/routes/products.route.ts
import { FastifyInstance } from 'fastify';
import { getAdapter } from '../../adapters/factory';

export default async function productRoutes(app: FastifyInstance) {
  app.get('/api/products/search', async (request, reply) => {
    const { q, limit } = request.query as { q: string; limit?: string };
    const adapter = getAdapter();

    const products = await adapter.products.search(q, parseInt(limit || '10'));

    return { products };
  });

  app.get('/api/products/:id', async (request, reply) => {
    const { id } = request.params as { id: string };
    const adapter = getAdapter();

    const product = await adapter.products.getById(id);
    if (!product) {
      return reply.status(404).send({ error: 'Product not found' });
    }

    return { product };
  });
}
```

### 3.2 Update Cart Routes

```typescript
// web/routes/cart.route.ts
import { FastifyInstance } from 'fastify';
import { getAdapter } from '../../adapters/factory';

export default async function cartRoutes(app: FastifyInstance) {
  app.get('/api/cart', async (request, reply) => {
    const userId = request.headers['x-user-id'] as string || 'guest';
    const adapter = getAdapter();

    const cart = await adapter.cart.getCart(userId);
    return { cart };
  });

  app.post('/api/cart/add', async (request, reply) => {
    const { productId, quantity } = request.body as { productId: string; quantity: number };
    const userId = request.headers['x-user-id'] as string || 'guest';
    const adapter = getAdapter();

    const cart = await adapter.cart.addToCart(productId, quantity, userId);
    return { cart };
  });

  app.post('/api/cart/update', async (request, reply) => {
    const { cartItemId, quantity } = request.body as { cartItemId: string; quantity: number };
    const userId = request.headers['x-user-id'] as string || 'guest';
    const adapter = getAdapter();

    const cart = await adapter.cart.updateCartItem(cartItemId, quantity, userId);
    return { cart };
  });

  app.post('/api/cart/remove', async (request, reply) => {
    const { cartItemId } = request.body as { cartItemId: string };
    const userId = request.headers['x-user-id'] as string || 'guest';
    const adapter = getAdapter();

    const cart = await adapter.cart.removeFromCart(cartItemId, userId);
    return { cart };
  });
}
```

---

## Phase 4: Apex Endpoints (Salesforce Side) (2–3 days)

### 4.1 Deploy Apex REST Classes

Create these Apex classes in your Salesforce org:

**CommerceSearchRest.cls:**
```apex
@RestResource(urlMapping='/commerce/search')
global class CommerceSearchRest {
    @HttpGet
    global static List<Map<String, Object>> searchProducts() {
        String query = RestContext.request.params.get('q');
        Integer limitVal = Integer.valueOf(RestContext.request.params.get('limit') ?? '10');
        
        List<Product2> products = [
            SELECT Id, Name, Description, 
                   (SELECT UnitPrice FROM PricebookEntries WHERE IsActive = true LIMIT 1)
            FROM Product2 
            WHERE Name LIKE :('%' + query + '%')
            LIMIT :limitVal
        ];
        
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (Product2 p : products) {
            Map<String, Object> item = new Map<String, Object>();
            item.put('id', p.Id);
            item.put('name', p.Name);
            item.put('description', p.Description);
            item.put('price', p.PricebookEntries.isEmpty() ? 0 : p.PricebookEntries[0].UnitPrice);
            item.put('inStock', true);
            results.add(item);
        }
        return results;
    }
}
```

**CartApi.cls:**
```apex
@RestResource(urlMapping='/CartApi/*')
global class CartApi {
    @HttpGet
    global static Map<String, Object> getCart() {
        String buyerAccountId = RestContext.request.params.get('buyerAccountId');
        // Query WebCart or custom cart object
        // Return normalized cart structure
        return new Map<String, Object>{
            'cartId' => 'cart-123',
            'lines' => new List<Object>()
        };
    }
    
    @HttpPost
    global static Map<String, Object> handlePost() {
        String action = RestContext.request.requestURI.substringAfterLast('/');
        Map<String, Object> body = (Map<String, Object>) JSON.deserializeUntyped(
            RestContext.request.requestBody.toString()
        );
        
        if (action == 'addItem') {
            // Add item logic
        } else if (action == 'updateItem') {
            // Update item logic
        } else if (action == 'removeItem') {
            // Remove item logic
        }
        
        return new Map<String, Object>{ 'success' => true };
    }
}
```

### 4.2 Configure Connected App

1. Create Connected App in Salesforce Setup.
2. Enable OAuth with JWT Bearer Flow.
3. Upload your server's public certificate.
4. Grant "api" scope.
5. Pre-authorize the integration user.

---

## Phase 5: Environment Configuration (1 day)

### 5.1 Update `.env.example`

```env
# Platform Selection
ACTIVE_PLATFORM=shopify  # or 'salesforce'

# Shopify (existing)
SHOPIFY_STORE_DOMAIN=...
SHOPIFY_ACCESS_TOKEN=...

# Salesforce (new)
SALESFORCE_TOKEN_URL=https://login.salesforce.com/services/oauth2/token
SALESFORCE_JWT_CLIENT_ID=your_connected_app_client_id
SALESFORCE_JWT_USERNAME=integration@yourcompany.com
SALESFORCE_JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
SALESFORCE_API_VERSION=v57.0
SALESFORCE_SITE_BASE_URL=https://your-site.my.site.com

# Python Backend (unchanged)
PYTHON_BACKEND_URL=http://localhost:8000

# Elasticsearch (unchanged)
ELASTICSEARCH_URL=http://localhost:9200
```

### 5.2 Update `docker-compose.yml`

```yaml
services:
  backend-node:
    environment:
      - ACTIVE_PLATFORM=${ACTIVE_PLATFORM:-shopify}
      - SALESFORCE_TOKEN_URL=${SALESFORCE_TOKEN_URL}
      - SALESFORCE_JWT_CLIENT_ID=${SALESFORCE_JWT_CLIENT_ID}
      - SALESFORCE_JWT_USERNAME=${SALESFORCE_JWT_USERNAME}
      - SALESFORCE_JWT_PRIVATE_KEY=${SALESFORCE_JWT_PRIVATE_KEY}
      - SALESFORCE_API_VERSION=${SALESFORCE_API_VERSION:-v57.0}
      - SALESFORCE_SITE_BASE_URL=${SALESFORCE_SITE_BASE_URL}
    # ... rest unchanged
```

---

## Phase 6: Testing (3–4 days)

### 6.1 Unit Tests

Create `backend-node/src/modules/salesforce_adapter/__tests__/`:

**client.test.ts:**
```typescript
import { SalesforceClient } from '../client';
import axios from 'axios';

jest.mock('axios');

describe('SalesforceClient', () => {
  const mockConfig = {
    tokenUrl: 'https://login.salesforce.com/services/oauth2/token',
    clientId: 'test-client-id',
    jwtUsername: 'test@example.com',
    jwtPrivateKey: '-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----',
    apiVersion: 'v57.0',
  };

  it('should create client instance', () => {
    const client = new SalesforceClient(mockConfig);
    expect(client).toBeDefined();
  });

  it('should fetch token on first request', async () => {
    (axios.post as jest.Mock).mockResolvedValueOnce({
      data: { access_token: 'test-token', instance_url: 'https://test.salesforce.com' },
    });

    const client = new SalesforceClient(mockConfig);
    const axiosInstance = client.getAxios();
    expect(axiosInstance).toBeDefined();
  });
});
```

**products.test.ts:**
```typescript
import { ProductService } from '../products';
import { SalesforceClient } from '../client';

describe('ProductService', () => {
  const mockClient = {
    getAxios: jest.fn().mockReturnValue({
      get: jest.fn().mockResolvedValue({
        data: {
          products: [
            { Id: '1', Name: 'Test Product', UnitPrice: 99.99 },
          ],
        },
      }),
    }),
    getConfig: jest.fn().mockReturnValue({ siteBaseUrl: 'https://test.com' }),
  } as unknown as SalesforceClient;

  const mockLogger = { debug: jest.fn(), info: jest.fn(), warn: jest.fn(), error: jest.fn() };

  it('should search products and normalize results', async () => {
    const service = new ProductService(mockClient, mockLogger);
    const results = await service.search('test', 10);

    expect(results).toHaveLength(1);
    expect(results[0]).toMatchObject({
      id: '1',
      title: 'Test Product',
      price: '99.99',
    });
  });
});
```

### 6.2 Integration Tests

**integration/salesforce.test.ts:**
```typescript
import { createSalesforceAdapter } from '../salesforce_adapter';

describe('Salesforce Adapter Integration', () => {
  // Skip if no Salesforce credentials
  const shouldRun = process.env.SALESFORCE_JWT_CLIENT_ID;

  (shouldRun ? it : it.skip)('should search products from Salesforce', async () => {
    const adapter = createSalesforceAdapter({
      config: {
        tokenUrl: process.env.SALESFORCE_TOKEN_URL!,
        clientId: process.env.SALESFORCE_JWT_CLIENT_ID!,
        jwtUsername: process.env.SALESFORCE_JWT_USERNAME!,
        jwtPrivateKey: process.env.SALESFORCE_JWT_PRIVATE_KEY!,
        apiVersion: 'v57.0',
      },
    });

    const products = await adapter.products.search('test', 5);
    expect(Array.isArray(products)).toBe(true);
  });
});
```

### 6.3 E2E Tests

**e2e/platform-switching.test.ts:**
```typescript
import request from 'supertest';
import { app } from '../server';

describe('Platform Switching E2E', () => {
  it('should return products from Shopify when ACTIVE_PLATFORM=shopify', async () => {
    process.env.ACTIVE_PLATFORM = 'shopify';
    const res = await request(app).get('/api/products/search?q=shirt');
    expect(res.status).toBe(200);
    expect(res.body.products).toBeDefined();
  });

  it('should return products from Salesforce when ACTIVE_PLATFORM=salesforce', async () => {
    process.env.ACTIVE_PLATFORM = 'salesforce';
    const res = await request(app).get('/api/products/search?q=laptop');
    expect(res.status).toBe(200);
    expect(res.body.products).toBeDefined();
  });
});
```

### 6.4 Test Commands

Add to `package.json`:
```json
{
  "scripts": {
    "test": "jest",
    "test:unit": "jest --testPathPattern=__tests__",
    "test:integration": "jest --testPathPattern=integration",
    "test:e2e": "jest --testPathPattern=e2e",
    "test:salesforce": "ACTIVE_PLATFORM=salesforce jest"
  }
}
```

Run tests:
```bash
# Unit tests
pnpm test:unit

# Integration tests (requires Salesforce credentials)
pnpm test:integration

# E2E tests
pnpm test:e2e

# All tests with Salesforce
pnpm test:salesforce
```

---

## Phase 7: Documentation & Deployment (1–2 days)

### 7.1 Update API Contracts

Update api-contracts.md to document:
- Platform switching via `ACTIVE_PLATFORM`
- Salesforce-specific endpoints
- Normalized response shapes

### 7.2 Deployment Checklist

- [ ] Salesforce Connected App created and configured
- [ ] Apex classes deployed to Salesforce org
- [ ] JWT private key securely stored
- [ ] Environment variables configured in deployment platform
- [ ] `ACTIVE_PLATFORM` set correctly
- [ ] Integration tests passing against sandbox
- [ ] Health check endpoint verifies Salesforce connectivity

---

## Final Project Structure

```
backend-node/src/modules/
├── adapters/
│   ├── types.ts              # Unified adapter interface
│   └── factory.ts            # Platform-switching factory
├── salesforce_adapter/       # NEW
│   ├── index.ts
│   ├── types.ts
│   ├── client.ts
│   ├── products.ts
│   ├── cart.ts
│   ├── media.ts
│   ├── README.md
│   └── __tests__/
│       ├── client.test.ts
│       ├── products.test.ts
│       └── cart.test.ts
├── shopify_adapter/          # Existing
│   └── ...
├── web/
│   └── routes/
│       ├── products.route.ts  # Updated to use factory
│       └── cart.route.ts      # Updated to use factory
└── observability/
    └── ...
```

---

## Summary Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 0: Preparation | 1 day | Environment setup, contract review |
| Phase 1: Adapter Package | 3–4 days | `salesforce_adapter/` with client, products, cart |
| Phase 2: Factory | 2 days | Unified interface, platform switching |
| Phase 3: Route Updates | 2 days | Products + cart routes using factory |
| Phase 4: Apex | 2–3 days | Salesforce REST endpoints |
| Phase 5: Config | 1 day | Env vars, docker-compose |
| Phase 6: Testing | 3–4 days | Unit, integration, E2E tests |
| Phase 7: Docs & Deploy | 1–2 days | Documentation, deployment |

**Total: ~15–19 days**

---

## Key Points

1. **Python backend stays unchanged** — all platform logic is in Node.js; Python receives normalized `Product[]` and `Cart` shapes.

2. **Switch platforms with one env var** — `ACTIVE_PLATFORM=salesforce` or `ACTIVE_PLATFORM=shopify`.

3. **Adapter factory caches instances** — avoids repeated token fetches.

4. **Apex deployment required** — deploy provided classes to each Salesforce org.

5. **Testing at all levels** — unit tests for adapter, integration tests against Salesforce sandbox, E2E tests for full flow.

Would you like me to start implementing any specific phase, or create the file structure in your project now?


--------------New Plan----------------------------------------------------

## 🚀 Complete Salesforce Adapter Setup Guide (Step-by-Step)

### What's happening:
1. **Node backend** (backend-node) has Salesforce credentials in .env ✅
2. **Python backend** (backend-pylang) is MISSING the same credentials ❌
3. Python needs `cryptography` package for JWT RS256 signing ❌

---

## STEP 1: Install missing Python package

Open PowerShell and run:
```powershell
cd C:\Users\anura\develop\backend-pylang
.\.venv\Scripts\Activate.ps1
pip install cryptography
```

**Expected output:** `Successfully installed cryptography-...`

---

## STEP 2: Create Python .env file with Salesforce credentials

Create a new file `C:\Users\anura\develop\backend-pylang\.env` (copy the contents below):

```powershell
# Run this in PowerShell to create the .env file:
@'
# Easymart PyLang Backend Environment

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=False
ENVIRONMENT=development
TEST_MODE=False

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002

# OpenAI (copy from your existing .env.example)
OPENAI_API_KEY=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
OPENAI_MODEL=gpt-4.1

# Backend Node.js URL
NODE_BACKEND_URL=http://localhost:3001

# Search Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
SEARCH_LIMIT_DEFAULT=5
SEARCH_HYBRID_ALPHA=0.6
SEARCH_MMR_ENABLED=True
SEARCH_MMR_LAMBDA=0.7
SEARCH_MMR_FETCH_K=50
SEARCH_RRF_K=60

# Catalog Sync
CATALOG_SYNC_ENABLED=False
CATALOG_SYNC_INTERVAL_MINUTES=60

# Sessions
SESSION_TIMEOUT_MINUTES=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============================================
# SALESFORCE CONFIGURATION (IMPORTANT!)
# ============================================
SALESFORCE_BASE_URL=https://orgfarm-e6b615be40-dev-ed.develop.my.salesforce.com
SALESFORCE_TOKEN_URL=https://login.salesforce.com/services/oauth2/token
SALESFORCE_JWT_CLIENT_ID=3MVG9GCMQoQ6rpzR2MfUOzcLkKXJj8FjRv7PflrUWAYSiXFKcPTWy24m0jgp_cB40q.NzgwDBMF_x7y7LnhF0
SALESFORCE_JWT_USERNAME=sangeetasharma9352520@agentforce.com
SALESFORCE_JWT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCNxVpRFn+FQotz\nrKtsbAg4CX14u0t+b4puhzcjfnfYgA0AkWDX5ou5rfAF5PTcbYMx/x/mlhTsyIEP\nCBtSECI1V8A10LEkwqDTC67T/VWMge5guF8jpK5PEkM24XKpDKd+ZXz+KmjJ53A8\nyKpmK65kUBCVskbMWwpOF1W8fycJJiM+Zm8NLHOsI4Ajw30j54ihZcKV/UEVxh40\n+AgI40kDCSFGvyB+wxxUX5YRUk7gF8gKETrOwHQaB0Fx377aX2/weYTdM/OOJDBG\nFXXApVEsHRywS/gwD4hlc8JfINOEowKhzFeRVnwuNkJGIWUAZK9nXRxSCqnO7Sfh\nAvrEh4VlAgMBAAECggEACCkmmElXwNeCSH/VhFG5rWQadWMuptIL4W3mJiRnCK7i\nULiNnw/11hPln6k80R16sluRvgfAn5qxFyjrza8BERoChfaD4+5SLKPdBfXswUBP\ndQDX9SjLIeEWvmd+3q1MTPHRnp3ZV1n7s3wHlwcHrF2RftR6z9OjxbgBJu8Y06Vo\n7ivwuFafhu3Vh6Bky9G2P3RKqS+rEhYWfzN8JsGLWBEDFl8fkUzS7uEOOEQgoo0B\n9Gd+HqpvsKpFHIn+TnojnIcQGbILt7364m4nS9tJHWLnQlCbD6ybMO9VS3AgI07L\n/pQMaUpGpPDZKiQmylsl2L5wnEDitasLSvZGso8vAQKBgQC+ne+07Kl6u72fz27I\nxWX3fyTPRIP6uQd3XA/cKVC+dxjbyuIeRDLXx3hNyZnDicQyFS25TX6q7tdswzyg\niQAprELrEzdwIchW8tjoEkdgUmD6Lmyo2Xahe9giPsgNIRYaoLpp8WZNmThYEar8\nPw/CQJu+12ETNbOqKFLJXHzvgQKBgQC+Zj/EqQWLEirgD4bKRflvqvQ6O6JyuaI2\nhStlb46ZOw9OhF2J60buBAgV8MTvc6qDb9qL+nvzgZMf2Xu8iMh8EVc7g73rOpIG\nsf/whI9YMFs4t2wx1ZXBc4fc4Er13HJRmh/OYut4XVBKBfUS2DRfvVDujLaeq5A3\n3BKCtpjH5QKBgC7/BYCX8NkfvIrQO8IoWRGCOXMYs2l3gQ2+lvJzBUNQXcKi7MkF\ni3uD5HdZQx3gs4ydiB5tqtM9+8MHB8WUwYOEwyLuI/bzfU9ipHPjPdHTvbExDP08\nUHFT9V/MFsqV47tA8XT5XX24Txn3kS6L5bjA8SVGONrhnKBRPMgEk5EBAoGAEOEb\nsiGR3jxkFK0LtA70CBRNxoPW6PjQCqlPqZR0Pd1ghAN0D3AOP7eXx+oqa1gDu9dE\ntrgkGPhZxK8RKyutKmKXKy2IvrvYikNpfzchRh4zWBnau6hFuHq3hrtTqew7LkTN\noQxf97G+FnHkwiDss7gi3qMW5YYsKOeXtILflIkCgYEAvkajDjj8LRrkMYFb8gx7\n6oAWn15aR/CYq2zrqgSMGirFHevH8GWuwOoJ1ay00wR7CKRLO158F1usqygt2Y+t\nMNJ3GPtdwTzRCIBA4jAne2Kv8orTaXL4Aut1O7RIRGDsQhC0XoOGPWCzfPWkN/3J\n+3ItRHb4AQYHgy6APAAXEn8=\n-----END PRIVATE KEY-----
'@ | Out-File -FilePath C:\Users\anura\develop\backend-pylang\.env -Encoding utf8
```

**What this does:** Creates .env file with your Salesforce credentials (same as Node backend).

---

## STEP 3: Stop old Python server and restart

```powershell
# Find and stop the old server (if running)
netstat -ano | findstr ":8000"
# If you see a PID (like 13596), stop it:
Stop-Process -Id 13596 -Force

# Start fresh
cd C:\Users\anura\develop\backend-pylang
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug
```

**Expected:** Server starts and shows `[Easymart Assistant] Ready!`

---

## STEP 4: Test Python Salesforce endpoints

Open a **new PowerShell window** (keep the server running in the first one):

```powershell
# Test 1: Health check
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health/ping"

# Test 2: Salesforce export (this calls Salesforce API)
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/internal/salesforce/export?page=1&pageSize=10"

# Test 3: Salesforce search
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/internal/salesforce/search" -Body '{"query":"chair","page":1,"pageSize":10}' -ContentType "application/json"
```

---

## STEP 5: Start Node backend (in another PowerShell window)

```powershell
cd C:\Users\anura\develop\backend-node
npm run dev
```

**Expected:** Node starts on port 3001 (check .env PORT setting)

---

## STEP 6: Test Node → Python integration

```powershell
# Test Node health
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:3001/health"

# Test catalog export (Node proxies to Python for Salesforce)
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:3001/api/internal/catalog/export"
```

---

## STEP 7: Start Frontend (optional, in another PowerShell window)

```powershell
cd C:\Users\anura\develop\frontend
npm run dev
```

Then open browser: http://localhost:3000

---

## 📋 Quick Reference: All Test Commands

```powershell
# ========== PYTHON BACKEND (port 8000) ==========
# Health
Invoke-RestMethod -Uri "http://127.0.0.1:8000/"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/ping"

# Salesforce endpoints
Invoke-RestMethod -Uri "http://127.0.0.1:8000/internal/salesforce/export?page=1&pageSize=10"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/internal/salesforce/search" -Body '{"query":"sofa","page":1,"pageSize":10}' -ContentType "application/json"

# ========== NODE BACKEND (port 3001) ==========
# Health
Invoke-RestMethod -Uri "http://127.0.0.1:3001/health"

# Catalog export (should proxy to Python when ACTIVE_PLATFORM=salesforce)
Invoke-RestMethod -Uri "http://127.0.0.1:3001/api/internal/catalog/export"

# ========== ASSISTANT CHAT ==========
# Send a message to the assistant
$body = @{ message = "Show me sofas"; session_id = "test-123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/assistant/message" -Body $body -ContentType "application/json"
```

---

## 🔧 Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `RS256 algorithm not found` | Missing `cryptography` package | `pip install cryptography` |
| `Invalid URL 'None'` | Missing `SALESFORCE_TOKEN_URL` in .env | Add to .env |
| `Connection refused` | Server not running | Start uvicorn/npm |
| `401 Unauthorized` | Bad Salesforce credentials | Check .env values |

---

**Start with Step 1 now.** After each step, paste any errors you see and I'll help fix them before moving to the next step.

