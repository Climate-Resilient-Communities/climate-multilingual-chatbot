# Backend (FastAPI) Guide

This guide explains the backend server that powers the Climate Multilingual Chatbot.

---

## What is the Backend?

The **backend** is the server-side part of our application. It:
- Receives requests from the frontend (web browser)
- Processes them using the AI pipeline
- Returns responses back to the user

**Technology**: [FastAPI](https://fastapi.tiangolo.com/) - a modern, fast Python web framework

**Location**: [`src/webui/api/`](../../src/webui/api/)

---

## Entry Point

### main.py

**File**: [`src/webui/api/main.py`](../../src/webui/api/main.py)

This is where everything starts. When you run the server, this file:

1. **Creates the FastAPI app** (line 98-104)
```python
app = FastAPI(
    title="Climate Multilingual Chatbot API",
    version="1.0.0",
    lifespan=lifespan
)
```

2. **Sets up middleware** (line 106-116)
   - CORS: Allows the frontend to communicate with the backend
   - Logging: Records all requests for debugging

3. **Initializes components** (line 50-96)
   - ClimateQueryPipeline (AI processing)
   - Redis cache (response caching)
   - Language router (multilingual support)

4. **Registers API routes** (line 276-283)
```python
app.include_router(chat_router, prefix="/api/v1/chat")
app.include_router(languages_router, prefix="/api/v1/languages")
app.include_router(feedback_router, prefix="/api/v1/feedback")
app.include_router(consent_router, prefix="/api/v1/consent")
```

5. **Serves static files** (line 285-291)
   - Serves the built Next.js frontend at `/`

---

## API Endpoints

### Chat Endpoints

**File**: [`src/webui/api/routers/chat.py`](../../src/webui/api/routers/chat.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/chat/query` | POST | Process a chat query |
| `/api/v1/chat/stream` | POST | Stream response in real-time |
| `/api/v1/chat/test` | GET | Health check for chat service |

#### Example: /chat/query

**Request**:
```json
{
  "query": "What is climate change?",
  "language": "en",
  "conversation_history": [],
  "stream": false,
  "skip_cache": false
}
```

**Response**:
```json
{
  "success": true,
  "response": "Climate change refers to...",
  "citations": [
    {
      "title": "IPCC Report",
      "url": "https://ipcc.ch/...",
      "snippet": "..."
    }
  ],
  "faithfulness_score": 0.85,
  "processing_time": 3.2,
  "language_used": "en",
  "model_used": "nova",
  "request_id": "req_1234567890"
}
```

### Language Endpoints

**File**: [`src/webui/api/routers/languages.py`](../../src/webui/api/routers/languages.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/languages/supported` | GET | List all supported languages |
| `/api/v1/languages/validate` | POST | Detect language of text |

### Feedback Endpoints

**File**: [`src/webui/api/routers/feedback.py`](../../src/webui/api/routers/feedback.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/feedback/submit` | POST | Submit user feedback |
| `/api/v1/feedback/categories` | GET | Get available feedback types |

### Health Endpoints

**File**: [`src/webui/api/main.py`](../../src/webui/api/main.py) (lines 217-272)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Full readiness check |
| `/health/live` | GET | Liveness probe |

---

## Middleware

### Rate Limiting

**Location**: [`main.py`](../../src/webui/api/main.py) lines 118-215

Prevents abuse by limiting how many requests a user can make:

| Environment | Chat Limit | Feedback Limit |
|-------------|------------|----------------|
| Development | 60/min | 100/min |
| Staging | 30/min | 60/min |
| Production | 20/min | 50/min |

When exceeded, returns:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retryable": true
  }
}
```

### CORS (Cross-Origin Resource Sharing)

**Location**: [`main.py`](../../src/webui/api/main.py) lines 106-116

Configures which domains can call the API:
```python
origins = os.environ.get("CORS_ORIGINS", "http://localhost:9002").split(",")
```

### Request Logging

**Location**: [`main.py`](../../src/webui/api/main.py) lines 142-215

Logs every request with:
- Unique request ID
- Processing time
- Client IP address
- HTTP status code

Example log:
```
REQUEST POST /api/v1/chat/query status=200 time=3.2s id=req_1234567890 ip=192.168.1.1
```

---

## Error Handling

The backend uses standardized error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "type": "error_type",
    "message": "Human-readable message",
    "retryable": true,
    "request_id": "req_1234567890"
  }
}
```

### Error Types

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `LANGUAGE_MISMATCH` | 400 | Query language doesn't match selection |
| `OFF_TOPIC_QUERY` | 400 | Question isn't about climate |
| `HARMFUL_QUERY` | 400 | Blocked harmful content |
| `PROCESSING_TIMEOUT` | 504 | Request took too long |
| `INTERNAL_ERROR` | 500 | Something went wrong |

---

## Request Flow

```
1. Browser sends request
        │
        ▼
2. FastAPI receives request
        │
        ▼
3. Middleware runs:
   • Rate limit check
   • Request logging
        │
        ▼
4. Router handles request:
   • Validates input (Pydantic)
   • Calls pipeline
        │
        ▼
5. Pipeline processes query
        │
        ▼
6. Response returned to browser
```

---

## Running the Backend

### Development
```bash
# With auto-reload
poetry run uvicorn src.webui.api.main:app --reload --port 8000
```

### Production
```bash
poetry run uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

Required:
```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
COHERE_API_KEY=...
PINECONE_API_KEY=...
```

Optional:
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
CORS_ORIGINS=http://localhost:9002
ENVIRONMENT=development
DISABLE_RATE_LIMIT=false
```

---

## Key Files Summary

| File | Purpose | Lines |
|------|---------|-------|
| [`main.py`](../../src/webui/api/main.py) | App entry, middleware, health checks | ~400 |
| [`routers/chat.py`](../../src/webui/api/routers/chat.py) | Chat endpoints | ~300 |
| [`routers/languages.py`](../../src/webui/api/routers/languages.py) | Language endpoints | ~175 |
| [`routers/feedback.py`](../../src/webui/api/routers/feedback.py) | Feedback endpoints | ~230 |
| [`routers/consent.py`](../../src/webui/api/routers/consent.py) | Consent management | ~200 |

---

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [AI Pipeline Guide](./03-ai-pipeline.md)
- [Caching Guide](./05-caching.md)
