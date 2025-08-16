# Climate Chatbot FastAPI Backend

Production-ready FastAPI backend integrating all pipeline components from `src/models/`.

## 🚀 Quick Start

### Start the API Server
```bash
uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Test the Integration
```bash
python test_api.py
```

### Access Points
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔧 Configuration

### Environment Variables
```bash
# CORS configuration (comma-separated origins)
CORS_ORIGINS=http://localhost:9002,https://your-frontend.azurewebsites.net

# Redis configuration (if using external Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-password

# Add other pipeline environment variables as needed
COHERE_API_KEY=your-key
PINECONE_API_KEY=your-key
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

## 📡 API Endpoints

### Core Endpoints
- `POST /api/v1/chat/query` - Main chat processing (10 requests/minute)
- `POST /api/v1/chat/stream` - SSE streaming chat (real-time)
- `GET /api/v1/languages/supported` - Supported languages
- `POST /api/v1/languages/validate` - Language validation
- `POST /api/v1/feedback/submit` - Enhanced feedback (30 requests/minute)

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness (includes prewarm status)
- `GET /health/live` - Liveness check

## 🛡️ Security Features

### Rate Limiting
- **Chat**: 10 requests/minute per IP
- **Feedback**: 30 requests/minute per IP
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Reset`, `Retry-After`

### CORS Protection
- Environment-driven origin restrictions
- No wildcards in production
- Credentials support for cookies

### Request Handling
- 60-second timeout protection
- Correlation IDs (`X-Request-ID`)
- Structured error responses
- PII detection in feedback

## 🔗 Frontend Integration

### Standard Request
```typescript
const response = await fetch('/api/v1/chat/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'What is climate change?',
    language: 'en',
    conversation_history: []
  })
});
```

### SSE Streaming
```typescript
const eventSource = new EventSource('/api/v1/chat/stream', {
  method: 'POST',
  body: JSON.stringify({ query: 'What is climate change?' })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'progress': // Processing stage updates
    case 'token': // Real-time response tokens
    case 'complete': // Final response with citations
  }
};
```

## 🧪 Testing

### Basic Integration Test
```bash
python test_api.py
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# Language support
curl http://localhost:8000/api/v1/languages/supported

# Chat query
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is climate change?", "language": "en"}'
```

## 🚀 Production Deployment

### Azure App Service
```bash
# Environment variables
CORS_ORIGINS=https://your-frontend.azurewebsites.net
REDIS_URL=redis://your-redis.cache.windows.net:6380

# Run command
uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src ./src
EXPOSE 8000
CMD ["uvicorn", "src.webui.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔧 Pipeline Integration

### Components Integrated
- ✅ **ClimateQueryPipeline** - Main processing pipeline
- ✅ **ConversationParser** - History standardization  
- ✅ **MultilingualRouter** - Language detection & routing
- ✅ **ClimateCache** - Redis storage for sessions & feedback

### Language Support
- **Command A Model**: 22+ languages (high-quality)
- **Nova Model**: Broader language support (fallback)
- **Auto-routing**: Based on language detection

### Error Handling
- Timeout protection (60s)
- Graceful degradation
- Structured error responses
- Request correlation tracking