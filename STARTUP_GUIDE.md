# Climate Multilingual Chatbot - Startup Guide

This guide provides step-by-step instructions for starting both the backend API and frontend development servers.

## Prerequisites

- Python 3.12 with virtual environment activated
- Node.js (for Next.js frontend)
- Redis server running on localhost:6379
- Required environment variables and API keys configured

## Quick Start

### 🚀 **BEST PRACTICE: One-Line Server Restart**
```bash
# Kill both servers and start them together
pkill -f uvicorn; pkill -f "npm run dev"; sleep 3 && cd /Users/luis_ticas/Documents/GitHub/climate-multilingual-chatbot && poetry run uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 & cd src/webui/app && npm run dev &
```

### 1. Backend API Server

**Location**: Root directory  
**Port**: 8000  
**Endpoint**: http://localhost:8000

#### Start Command
```bash
# Start backend server
poetry run uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend Next.js Server

**Location**: `src/webui/app/`  
**Port**: 9002  
**Endpoint**: http://localhost:9002

#### Start Command
```bash
cd src/webui/app
npm run dev
```

## Full Startup Procedure

### Step 1: Environment Setup
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # or activate.bat on Windows

# Verify Python version
python --version  # Should be 3.12.x
```

### Step 2: Fix SSL Certificate Issue
Some of the Python libraries used in this project have issues with SSL certificate validation on macOS. To fix this, you need to create a dummy certificate file and copy the content of the `certifi` certificate to it.

```bash
# Create a dummy certificate file
touch /tmp/combined_certs.pem

# Copy the certifi CA bundle to the dummy file
cp $(python -c "import certifi; print(certifi.where())") /tmp/combined_certs.pem
```

### Step 3: Start Backend (Terminal 1)
```bash
# Navigate to project root
cd /path/to/climate-multilingual-chatbot

# Start backend server
poetry run uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000
```

**Wait for this message before proceeding:**
```
INFO:     Application startup complete.
```
You can also check the logs in `.logs/uvicorn_8000.log` and `backend.log`.

### Step 4: Start Frontend (Terminal 2)
```bash
# Navigate to frontend directory
cd src/webui/app

# Start development server
npm run dev
```

**Wait for this message:**
```
✓ Ready in 873ms
```

### Step 5: Verify Both Services
1. **Backend**: Visit http://localhost:8000/docs
2. **Frontend**: Visit http://localhost:9002
3. **Integration**: Test a chat query through the frontend

## Troubleshooting

### Backend Issues

#### SSL Certificate Errors
**Error**: `Could not find a suitable TLS CA certificate bundle, invalid path: /tmp/combined_certs.pem` or `[X509: NO_CERTIFICATE_OR_CRL_FOUND] no certificate or crl found`

**Solution**:
Follow the instructions in "Step 2: Fix SSL Certificate Issue" in the "Full Startup Procedure" section.

#### Redis Connection Issues
**Error**: Redis connection failed

**Solution**:
```bash
# Start Redis server
redis-server
# Or on macOS with Homebrew:
brew services start redis
```

#### Missing API Keys
**Error**: Various API initialization errors

**Solution**: Ensure all required environment variables are set:
- `COHERE_API_KEY`
- `PINECONE_API_KEY`
- `AWS_ACCESS_KEY_ID` (for Bedrock)
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`

### Frontend Issues

#### Port Already in Use
**Error**: `EADDRINUSE: address already in use :::9002`

**Solution**:
```bash
# Kill process on port 9002
lsof -ti:9002 | xargs kill -9
# Or use different port
npm run dev -- -p 9003
```

#### Node Modules Issues
**Error**: Module not found errors

**Solution**:
```bash
cd src/webui/app
rm -rf node_modules package-lock.json
npm install
```

## Development Commands

### Backend Development
```bash
# Start without auto-reload (recommended)
poetry run uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000

# Check logs
tail -f .logs/uvicorn_8000.log
```

### Frontend Development
```bash
cd src/webui/app

# Development server with Turbopack
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Type checking
npm run typecheck

# Linting
npm run lint
```

## API Endpoints

### Backend API (Port 8000)
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `POST /api/v1/chat/query` - Main chat endpoint
- `POST /api/v1/chat/stream` - Streaming chat endpoint
- `POST /api/v1/feedback/submit` - Submit feedback
- `GET /api/v1/languages/supported` - Get supported languages
- `POST /api/v1/languages/validate` - Validate/detect language

### Frontend (Port 9002)
- `http://localhost:9002` - Main chat interface
- All API calls proxied to backend

---

**Last Updated**: 2025-08-17  
**Tested On**: macOS with Python 3.12, Node.js 18+
