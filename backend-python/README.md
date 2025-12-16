# Easymart Assistant - Backend Python

FastAPI backend for Easymart AI Shopping Assistant with hybrid BM25 + vector search.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend-python
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
copy .env.example .env

# Edit .env with your settings
# Minimum required: OPENAI_API_KEY (when implementing LLM)
```

### 3. Load Catalog Data

```bash
# Load products into catalog
python -m app.modules.catalog_index.load_catalog path/to/products.json
```

### 4. Run Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Access API

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health/

## 📁 Project Structure

```
backend-python/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── api/                       # API endpoints
│   │   ├── health_api.py         # Health check
│   │   └── assistant_api.py      # Chat assistant
│   ├── core/                      # Core application
│   │   ├── config.py             # Settings
│   │   ├── schemas.py            # Pydantic models
│   │   ├── dependencies.py       # FastAPI dependencies
│   │   └── exceptions.py         # Custom exceptions
│   └── modules/
│       ├── catalog_index/         # ✅ Hybrid search (COMPLETE)
│       │   ├── models/           # Product, Spec models
│       │   ├── indexing/         # BM25, Vector, Hybrid
│       │   ├── catalog.py        # Main API
│       │   └── load_catalog.py   # Data ingestion
│       ├── retrieval/             # 🔧 Search wrappers (PLACEHOLDER)
│       │   ├── product_search.py # Product search
│       │   └── spec_search.py    # Spec search
│       ├── assistant/             # 🔧 AI assistant (PLACEHOLDER)
│       │   ├── intent_detector.py # Intent detection
│       │   ├── llm_client.py     # LLM integration
│       │   └── tools.py          # Tool calling
│       └── observability/         # 🔧 Monitoring (PLACEHOLDER)
│           ├── logging_config.py # Structured logging
│           ├── events.py         # Event tracking
│           └── metrics.py        # Metrics collection
├── tests/                         # Test suites
├── data/                          # Data storage
│   ├── bm25/                     # BM25 indexes
│   ├── chromadb/                 # Vector indexes
│   └── easymart.db               # SQLite database
├── .env.example                   # Environment template
└── requirements.txt               # Python dependencies
```

## 🔌 API Endpoints

### Health Check
```bash
GET /health/
GET /health/ping
```

### Assistant
```bash
POST /assistant/message
{
  "session_id": "user123",
  "message": "Show me leather wallets"
}
```

## 🧪 Testing

```bash
# Test catalog module
python backend-python/tests/modules/catalog_index/test_catalog.py

# Run all tests (when implemented)
pytest
```

## 📊 Module Status

### ✅ Complete Modules
- **catalog_index**: Full hybrid BM25 + vector search with SQLite + ChromaDB
  - All tests passing (7/7)
  - Production-ready indexing
  - API: `searchProducts()`, `searchSpecs()`, `getProductById()`, `getSpecsForProduct()`

### 🔧 Placeholder Modules (Ready for Implementation)
- **retrieval**: Product/spec search wrappers with filtering
- **assistant**: Intent detection, LLM client, tool calling
- **observability**: Logging, events, metrics

## 🛠️ Implementation Guide

### Phase 1: Core Search (✅ COMPLETE)
- [x] Catalog index with BM25 + vector search
- [x] API endpoints (health, assistant placeholder)
- [x] FastAPI application setup

### Phase 2: Retrieval Enhancement (🔧 TODO)
- [ ] Implement product search filters (price, vendor, tags)
- [ ] Add ranking adjustments
- [ ] Implement spec Q&A

### Phase 3: AI Assistant (🔧 TODO)
- [ ] Add OpenAI integration in `llm_client.py`
- [ ] Implement tool calling with catalog search
- [ ] Add session management
- [ ] Enhance intent detection

### Phase 4: Observability (🔧 TODO)
- [ ] Set up structured logging
- [ ] Implement event tracking (search, views, etc.)
- [ ] Add metrics collection
- [ ] Connect to monitoring platform

## 🔑 Environment Variables

See [`.env.example`](.env.example) for all available configuration options.

### Required
- `OPENAI_API_KEY` - OpenAI API key (when implementing LLM)

### Optional (with defaults)
- `PORT` - Server port (default: 8000)
- `DEBUG` - Debug mode (default: False)
- `EMBEDDING_MODEL` - Sentence transformer model (default: all-MiniLM-L6-v2)
- `SEARCH_HYBRID_ALPHA` - Hybrid search weight (default: 0.5)

## 🚦 Development Workflow

1. **Start with catalog_index** (✅ Complete)
   - Load product data
   - Test search functionality

2. **Implement retrieval layer**
   - Add filters and ranking
   - Test with catalog_index

3. **Add AI assistant**
   - Connect LLM (OpenAI)
   - Implement tool calling
   - Add session management

4. **Add observability**
   - Set up logging
   - Track events
   - Collect metrics

## 📖 API Documentation

Once server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐛 Troubleshooting

### Module Import Errors
```bash
# Ensure you're running from backend-python directory
cd backend-python
python -m app.main
```

### ChromaDB Issues
```bash
# Clear ChromaDB data if needed
rm -rf data/chromadb/*
```

### SQLite Database
```bash
# Reset database
rm data/easymart.db
# Rebuild indexes
python -m app.modules.catalog_index.load_catalog products.json
```

## 📝 License

Part of Easymart Chatbot project.
