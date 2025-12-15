# Backend Node.js

Node.js backend service for EasyMart - handles web layer and Shopify adapter.

## Features

- **Web Layer**: Serves chat widget and handles API requests
- **Shopify Adapter**: Integrates with Shopify Admin API for products and cart
- **Python Integration**: Forwards chat messages to Python assistant service
- **TypeScript**: Full type safety with strict mode
- **Fastify**: High-performance web framework

## Prerequisites

- Node.js 18+ and npm
- Python backend service running (for full functionality)
- Shopify store with Admin API access token

## Installation

```bash
# Install dependencies with pnpm
pnpm install

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - Add your Shopify store domain and access token
# - Set Python backend URL (default: http://localhost:8000)
```

## Configuration

Edit `.env` file:

```env
PORT=3001
PYTHON_BASE_URL=http://localhost:8000
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your_admin_access_token
SHOPIFY_API_VERSION=2024-01
```

## Development

```bash
# Start development server with auto-reload
pnpm dev

# Type check without building
pnpm type-check

# Lint code
pnpm lint

# Format code
pnpm format
```

## Production

```bash
# Build TypeScript to JavaScript
pnpm build

# Start production server
pnpm start
```

## API Endpoints

### Chat
- `POST /api/chat` - Send message to assistant
  - Body: `{ message: string, sessionId: string }`
  - Response: `{ replyText: string, actions?: any[] }`

### Health
- `GET /api/health` - Service health check
  - Response: `{ status: "ok", service: "node-backend" }`

### Widget
- `GET /widget/script.js` - Chat widget JavaScript
- `GET /widget/style.css` - Chat widget CSS

## Project Structure

```
src/
├── index.ts              # Entry point
├── server.ts             # Fastify server setup
├── config/
│   ├── env.ts           # Environment configuration
│   └── index.ts         # Config exports
├── modules/
│   ├── web/
│   │   ├── routes/      # API routes
│   │   ├── ui/          # Widget files
│   │   └── web.module.ts
│   ├── shopify_adapter/
│   │   ├── client.ts    # Shopify API client
│   │   ├── products.ts  # Product service
│   │   ├── cart.ts      # Cart service
│   │   └── index.ts
│   └── observability/
│       └── logger.ts    # Logging
└── utils/
    ├── pythonClient.ts  # Python API client
    └── session.ts       # Session helpers
```

## Integration with Python Backend

The Node backend forwards chat requests to the Python assistant service:

```typescript
// Node receives: POST /api/chat
// Forwards to: POST ${PYTHON_BASE_URL}/assistant/message
// Returns Python's response to client
```

Ensure Python backend is running and accessible at `PYTHON_BASE_URL`.

## Shopify Integration

### Admin API Access Token

1. Go to Shopify Admin → Apps → Develop apps
2. Create a new app
3. Configure Admin API scopes: `read_products`, `write_products`, `read_orders`, `write_orders`
4. Install app and copy Admin API access token
5. Add to `.env` as `SHOPIFY_ACCESS_TOKEN`

## Deployment

### Docker

```bash
# Build image
docker build -t easymart-node .

# Run container
docker run -p 3001:3001 --env-file .env easymart-node
```

### Docker Compose

See `../infra/docker-compose.yml` for multi-container setup.

## Troubleshooting

**Port already in use:**
```bash
# Change PORT in .env file
PORT=3002
```

**Cannot connect to Python backend:**
- Verify Python service is running
- Check `PYTHON_BASE_URL` in `.env`
- Test: `curl http://localhost:8000/health`

**Shopify API errors:**
- Verify `SHOPIFY_ACCESS_TOKEN` is valid
- Check API scopes include required permissions
- Ensure `SHOPIFY_STORE_DOMAIN` is correct (e.g., `store.myshopify.com`)

## License

ISC
