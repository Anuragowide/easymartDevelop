# 🛒 EasyMart v1 - Conversational Commerce Platform

[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue.svg)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://www.python.org/)
[![Fastify](https://img.shields.io/badge/Fastify-4.25-black.svg)](https://www.fastify.io/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> AI-powered conversational shopping assistant for Shopify stores using Mistral LLM via HuggingFace

---

## 📖 Overview

**EasyMart v1** is a production-ready conversational commerce platform that enables natural language shopping experiences for Shopify stores. Customers can chat with an AI assistant to discover products, get specifications, and make purchases through a simple chat interface.

### ✨ Key Features

- 🤖 **AI-Powered Chat**: Mistral 7B Instruct model via HuggingFace for natural conversations
- 🔍 **Semantic Product Search**: Vector embeddings + keyword search with Elasticsearch
- 📦 **Product Q&A**: RAG-based specification answering
- 🛍️ **Cart Management**: Add to cart directly from chat
- 💬 **Embeddable Widget**: Drop-in chat widget for any Shopify store
- 🔌 **Shopify Integration**: Real-time product sync via Admin API
- 📊 **Multi-Service Architecture**: Node.js gateway + Python AI backend

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Shopify Store  │
│   + Widget      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      Node.js Backend (Port 3001)    │
│  - API Gateway (Fastify)            │
│  - Shopify Adapter                  │
│  - Static Widget Serving            │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    Python Backend (Port 8000)       │
│  - FastAPI Server                   │
│  - Mistral LLM (HuggingFace)        │
│  - RAG Pipeline                     │
│  - Intent Detection                 │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Elasticsearch (Port 9200)         │
│  - Product Index (BM25)             │
│  - Vector Search (Embeddings)       │
└─────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+
- **pnpm** 8+
- **Python** 3.11+
- **Docker** (optional, for containerized deployment)
- **Shopify Store** with custom app credentials
- **HuggingFace API Key**

### Installation

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/easymart-v1.git
cd easymart-v1

# 2. Install Node.js backend dependencies
cd backend-node
pnpm install

# 3. Install Python backend dependencies (when ready)
cd ../backend-python
pip install -r requirements.txt

# 4. Configure environment variables
cd ../backend-node
cp .env.example .env
# Edit .env with your credentials

cd ../backend-python
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

#### Shopify Setup

1. Go to **Shopify Admin** → **Settings** → **Apps and sales channels**
2. Click **Develop apps** → **Create an app**
3. Configure scopes: `read_products`, `read_product_listings`, `write_draft_orders`
4. Install app and copy credentials:
   - `SHOPIFY_STORE_DOMAIN`: `your-store.myshopify.com`
   - `SHOPIFY_ACCESS_TOKEN`: `shpat_xxxxx...`

#### HuggingFace Setup

1. Sign up at https://huggingface.co
2. Go to https://huggingface.co/settings/tokens
3. Create new token with **read** access
4. Copy: `HUGGINGFACE_API_KEY`: `hf_xxxxx...`

### Running Locally

```bash
# Start Node.js backend
cd backend-node
pnpm dev
# Server runs on http://localhost:3001

# Start Python backend (separate terminal)
cd backend-python
uvicorn app.main:app --reload --port 8000
# Server runs on http://localhost:8000

# Start Elasticsearch (Docker)
docker run -d \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

### Testing

```bash
# Test Node.js health
curl http://localhost:3001/health

# Test Shopify connection
node test-shopify.js

# Test chat widget
curl http://localhost:3001/widget/chat-widget.js
```

---

## 📦 Project Structure

```
easymart-v1/
├── backend-node/              # Node.js API Gateway
│   ├── src/
│   │   ├── modules/
│   │   │   ├── web/           # HTTP routes + widget
│   │   │   ├── shopify_adapter/  # Shopify API wrapper
│   │   │   └── observability/ # Logging
│   │   ├── utils/             # HTTP clients, session
│   │   ├── types/             # TypeScript definitions
│   │   └── config/            # Environment config
│   ├── Dockerfile
│   └── package.json
│
├── backend-python/            # Python AI Backend
│   ├── app/
│   │   ├── api/               # FastAPI routes
│   │   ├── modules/
│   │   │   ├── assistant/     # LLM orchestration
│   │   │   ├── retrieval/     # Product search + RAG
│   │   │   └── catalog_index/ # Shopify → ES indexing
│   │   └── core/              # Pydantic schemas
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                  # Next.js Admin Dashboard (optional)
│   ├── app/
│   ├── components/
│   └── package.json
│
├── infra/                     # Infrastructure
│   ├── docker-compose.yml     # Multi-service orchestration
│   └── .env.example
│
└── docs/                      # Documentation
    ├── api-contracts.md
    ├── openapi-assistant.yaml
    ├── architecture-overview.md
    └── implementation-progress.md
```

---

## 🔌 API Endpoints

### Node.js Backend (`http://localhost:3001`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/chat` | POST | Send message to assistant |
| `/widget/chat-widget.js` | GET | Chat widget JavaScript |
| `/widget/chat-widget.css` | GET | Chat widget CSS |

### Python Backend (`http://localhost:8000`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/assistant/message` | POST | Process chat message (LLM) |

---

## 🎨 Widget Embedding

Add to your Shopify theme (`theme.liquid` before `</body>`):

```html
<script src="https://your-domain.com/widget/chat-widget.js"></script>
<link rel="stylesheet" href="https://your-domain.com/widget/chat-widget.css">
<script>
  window.EASYMART_BACKEND_URL = "https://your-domain.com/api/chat";
</script>
```

---

## 🐳 Docker Deployment

```bash
# Run all services with Docker Compose
cd infra
cp .env.example .env
# Edit .env with production credentials

docker-compose up -d

# Services:
# - backend-node: http://localhost:3001
# - backend-python: http://localhost:8000
# - search-index: http://localhost:9200
# - frontend: http://localhost:3000
```

---

## 🛠️ Tech Stack

### Backend
- **Node.js 18** with **TypeScript 5.3**
- **Fastify 4.25** - High-performance web framework
- **Axios** - HTTP client
- **pnpm** - Fast package manager

### AI & Search
- **HuggingFace Inference API** - Mistral 7B Instruct v0.2
- **Python 3.11** with **FastAPI**
- **Elasticsearch 8.11** - Product search + vector storage

### Frontend
- **Next.js 14** - React framework
- **Tailwind CSS** - Styling
- **Vanilla JavaScript** - Chat widget (no dependencies)

### Infrastructure
- **Docker** & **Docker Compose**
- **Shopify Admin API v2024-01**

---

## 📊 Current Status

| Component | Status | Progress |
|-----------|--------|----------|
| Node.js Backend | ✅ Complete | 100% |
| Python Backend | ⏳ In Progress | 0% |
| Chat Widget | ✅ Complete | 100% |
| Shopify Integration | ✅ Complete | 100% |
| Frontend Dashboard | ⚠️ Scaffold | 10% |
| Documentation | ✅ Complete | 100% |

**Overall Progress: 60%** 🚀

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Shopify** for the Commerce API
- **HuggingFace** for Mistral LLM access
- **Mistral AI** for the open-source model
- **Fastify** team for the excellent framework

---

## 📧 Contact

**Project Maintainer**: Your Name  
**Email**: your.email@example.com  
**GitHub**: [@yourusername](https://github.com/yourusername)

---

## 🗺️ Roadmap

### Phase 1 (Current)
- [x] Node.js backend complete
- [x] Shopify integration
- [x] Chat widget
- [ ] Python backend implementation
- [ ] Product indexing

### Phase 2 (Next 3 months)
- [ ] Multi-turn conversations
- [ ] Product recommendations
- [ ] Multi-language support (Hindi, Spanish)
- [ ] Analytics dashboard

### Phase 3 (6+ months)
- [ ] Visual search
- [ ] Voice input
- [ ] WhatsApp integration
- [ ] Shopify App Store listing

---

**Built with ❤️ for conversational commerce**
