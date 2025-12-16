# EasyMart Backend-Python - Quick Start Guide

## 🚀 Running with Docker

### Prerequisites
- Docker and Docker Compose installed
- HuggingFace API key (get from https://huggingface.co/settings/tokens)

### Quick Start

1. **Build the Docker image:**
```bash
docker build -t easymart-backend-python .
```

2. **Run with environment variables:**
```bash
docker run -p 8000:8000 \
  -e HUGGINGFACE_API_KEY=your_hf_key_here \
  -e NODE_BACKEND_URL=http://localhost:3001 \
  easymart-backend-python
```

3. **Or use docker-compose (recommended):**
```bash
cd ../infra
cp .env.example .env
# Edit .env with your keys
docker-compose up backend-python
```

## 🔧 Running Locally (Development)

### Prerequisites
- Python 3.11+
- pip or poetry

### Setup

1. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the server:**
```bash
python start_server.py
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Test Assistant Endpoint
```bash
curl -X POST http://localhost:8000/assistant/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "message": "Show me office chairs under $500"
  }'
```

## 📊 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `HUGGINGFACE_API_KEY` | HuggingFace API key for Mistral-7B | Yes |
| `NODE_BACKEND_URL` | URL of Node.js backend | Yes |
| `ENVIRONMENT` | production/development | No |
| `PORT` | Server port (default: 8000) | No |

## 🐳 Docker Image Details

- **Base Image**: python:3.11-slim
- **Size**: ~1.2GB (includes pre-cached embedding model)
- **Exposed Port**: 8000
- **Health Check**: `/health` endpoint every 30s
- **User**: Non-root (appuser:1000)

## 📦 Pre-loaded Data

The Docker image includes:
- ✅ Sentence-transformers model (all-MiniLM-L6-v2)
- ✅ Product catalog in SQLite
- ✅ BM25 indexes
- ✅ ChromaDB vector store

## 🔍 Troubleshooting

**Issue**: Model download timeout
- **Solution**: Model is pre-cached in Docker image, no download needed

**Issue**: Cannot connect to Node backend
- **Solution**: Check `NODE_BACKEND_URL` is correct. In docker-compose use service name: `http://backend-node:3001`

**Issue**: Health check failing
- **Solution**: Increase `start_period` in healthcheck (model loading takes ~30-40s)

## 📝 Notes

- First request may take 5-10 seconds as Mistral model initializes
- Session data is stored in-memory (lost on restart)
- For production, consider Redis for session persistence
- ChromaDB data persists in Docker volume `python-data`
