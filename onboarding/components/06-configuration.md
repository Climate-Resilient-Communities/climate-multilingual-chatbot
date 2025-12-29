# Configuration Guide

This guide explains all the configuration options for the Climate Multilingual Chatbot.

---

## Environment Variables

### Required Variables

These must be set for the application to work:

```bash
# AWS Bedrock (Nova LLM)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Cohere (Reranking + Command-A)
COHERE_API_KEY=your_cohere_key

# Pinecone (Vector Database)
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=gcp-starter
```

### Optional Variables

```bash
# Redis Cache
REDIS_HOST=localhost          # Default: localhost
REDIS_PORT=6379              # Default: 6379
REDIS_PASSWORD=              # Default: none
REDIS_SSL=false              # Default: false

# Server
PORT=8000                    # Default: 8000
HOST=0.0.0.0                # Default: 0.0.0.0
ENVIRONMENT=development      # development|staging|production

# CORS
CORS_ORIGINS=http://localhost:9002  # Comma-separated list

# Features
DISABLE_RATE_LIMIT=false    # Disable for testing
FORCE_COMMAND_A_RESPONSES=false  # Force Cohere model

# Tavily (Fallback Search)
TAVILY_API_KEY=your_tavily_key  # Optional fallback

# HuggingFace (Embeddings)
HF_API_TOKEN=your_hf_token  # For downloading models

# LangSmith (Debugging)
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=your_project
```

---

## Configuration Files

### 1. Application Config

**File**: [`src/data/config/config.py`](../../src/data/config/config.py)

```python
# Nova Model Configuration
NOVA_CONFIG = {
    "model_id": "amazon.nova-lite-v1:0",
    "max_tokens": 2000,
    "temperature": 0.7,
    "region": "us-east-1"
}

# Retrieval Configuration
RETRIEVAL_CONFIG = {
    "top_k_retrieve": 15,      # Initial documents to fetch
    "top_k_rerank": 5,         # Final documents after reranking
    "min_rerank_score": 0.70,  # Minimum relevance score
    "hybrid_alpha": 0.5,       # Dense/sparse balance (0.5 = equal)

    # Similarity thresholds
    "similarity_base": 0.65,
    "similarity_fallback": 0.55,
    "adaptive_margin": 0.10,

    # MMR Diversification
    "mmr_enabled": True,
    "mmr_lambda": 0.30,
    "mmr_overfetch": 6
}

# Redis Configuration
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": 0,
    "expiration": 3600  # 1 hour TTL
}
```

### 2. Domain Boosting

**File**: [`src/data/config/config.py`](../../src/data/config/config.py) (lines 59-102)

Preferred sources get a 25% score boost:

```python
DOMAIN_BOOST_CONFIG = {
    "preferred_domains": [
        # Canadian Federal
        "canada.gc.ca",
        "nrcan.gc.ca",
        "ec.gc.ca",
        "climate.canada.ca",
        "climatechange.gc.ca",

        # Ontario
        "ontario.ca",
        "climatechange.ontario.ca",

        # Toronto/GTA
        "toronto.ca",
        "mississauga.ca",
        "brampton.ca",
        "markham.ca",
        "vaughan.ca",

        # International
        "ipcc.ch",
        "unfccc.int",

        # Research
        "climatedata.ca",
        "climateatlas.ca"
    ],
    "boost_weight": 0.25
}
```

### 3. Content Filtering

**File**: [`src/data/config/config.py`](../../src/data/config/config.py)

Blocked content types:

```python
AUDIENCE_BLOCKLIST = [
    # Grade levels
    "K-12", "K-2", "Gr. 5-8", "Gr. 1-4",

    # Educational content
    "lesson plan",
    "curriculum",
    "worksheet",
    "classroom",
    "school activity",

    # Blocked domains
    "lsf-lst.ca",
    "climatelearning.ca"
]
```

---

## Frontend Configuration

### Next.js Config

**File**: [`src/webui/app/next.config.ts`](../../src/webui/app/next.config.ts)

```typescript
const nextConfig = {
  output: 'export',           // Static export for FastAPI serving
  trailingSlash: true,        // Add trailing slashes to URLs
  distDir: 'out',             // Output directory
  images: {
    unoptimized: true         // No image optimization (static)
  }
}
```

### Tailwind Config

**File**: [`src/webui/app/tailwind.config.ts`](../../src/webui/app/tailwind.config.ts)

```typescript
const config = {
  darkMode: ["class"],        // Dark mode via class
  content: [
    './src/**/*.{ts,tsx}',    // Scan all TypeScript files
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {...},
        secondary: {...}
      }
    }
  }
}
```

### Language Configuration

**File**: [`src/webui/app/src/app/languages.json`](../../src/webui/app/src/app/languages.json)

```json
{
  "languages": [
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"},
    {"code": "zh", "name": "Chinese"},
    // ... 183 total languages
  ]
}
```

---

## Rate Limiting

**File**: [`src/webui/api/main.py`](../../src/webui/api/main.py) (lines 162-180)

| Environment | Chat Endpoint | Feedback Endpoint |
|-------------|--------------|-------------------|
| Development | 60 req/min | 100 req/min |
| Staging | 30 req/min | 60 req/min |
| Production | 20 req/min | 50 req/min |

To disable (testing only):
```bash
DISABLE_RATE_LIMIT=true
```

---

## Model Selection

### Language → Model Mapping

**File**: [`src/models/query_routing.py`](../../src/models/query_routing.py)

| Languages | Model | Speed |
|-----------|-------|-------|
| en, es, ja, de, sv, da | Nova | Fast |
| ar, bn, zh, fil, fr, gu, ko, fa, ru, ta, ur, vi, pl, tr, nl, cs, id, uk, ro, el, hi, he | Command-A | Slower |
| All others | Nova (with translation) | Medium |

### Force Model Override

```bash
# Force all queries through Command-A
FORCE_COMMAND_A_RESPONSES=true
```

---

## Redis Configuration

### Basic Setup

**File**: [`redis.conf`](../../redis.conf)

```bash
# Network
bind 127.0.0.1
port 6379
protected-mode yes

# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence (AOF - recommended)
appendonly yes
appendfsync everysec

# Persistence (RDB - backup)
save 60 1
save 300 10
save 900 1

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Data directory
dir /var/lib/redis
```

### Production Settings

For production, consider:

```bash
# Security
requirepass your_strong_password

# TLS/SSL
tls-port 6380
tls-cert-file /path/to/cert.pem
tls-key-file /path/to/key.pem

# Replication (if using replica)
# replicaof master_host master_port
```

---

## Azure Configuration

### App Service Settings

**File**: [`src/data/config/azure_config.py`](../../src/data/config/azure_config.py)

Auto-detected environment variables:
- `WEBSITE_SITE_NAME` - App name
- `WEBSITE_HOSTNAME` - Hostname
- `WEBSITES_PORT` - Port (usually 8000)
- `WEBSITE_INSTANCE_ID` - Instance ID
- `APPINSIGHTS_INSTRUMENTATIONKEY` - Application Insights

### Startup Command

```bash
pip install --only-binary=all -r requirements.txt && \
python -m uvicorn src.webui.api.main:app --host 0.0.0.0 --port $PORT
```

---

## Logging Configuration

**File**: [`src/utils/logging_setup.py`](../../src/utils/logging_setup.py)

```python
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",

    # File logging (optional)
    "file_enabled": os.getenv("ENABLE_LOCAL_CHAT_LOGS", "false") == "true",
    "file_path": "logs/pipeline_debug.log",
    "file_max_bytes": 5 * 1024 * 1024,  # 5MB
    "file_backup_count": 3
}
```

Enable file logging:
```bash
ENABLE_LOCAL_CHAT_LOGS=true
```

---

## Timeout Configuration

| Component | Timeout | Location |
|-----------|---------|----------|
| API Request | 60s | `chat.py` line 148 |
| Nova LLM Call | 30s | `nova_flow.py` line 109 |
| Cohere Rerank | 10s | `rerank.py` line 102 |
| Redis Connection | 5s | `redis_cache.py` line 40 |

---

## Testing Configuration

**File**: [`pytest.ini`](../../pytest.ini)

```ini
[pytest]
pythonpath = src
testpaths = tests
python_files = test_*.py
asyncio_mode = auto

# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
```

Run tests:
```bash
# All tests
pytest

# Specific type
pytest -m unit
pytest -m integration

# Verbose
pytest -v

# With coverage
pytest --cov=src
```

---

## Environment Setup Summary

### Development (.env)

```bash
# Required
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_DEFAULT_REGION=us-east-1
COHERE_API_KEY=xxx
PINECONE_API_KEY=xxx

# Optional
REDIS_HOST=localhost
ENVIRONMENT=development
DISABLE_RATE_LIMIT=true
CORS_ORIGINS=http://localhost:9002
```

### Production (.env)

```bash
# Required
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_DEFAULT_REGION=us-east-1
COHERE_API_KEY=xxx
PINECONE_API_KEY=xxx

# Redis (managed service recommended)
REDIS_HOST=your-redis.cache.azure.net
REDIS_PORT=6380
REDIS_PASSWORD=xxx
REDIS_SSL=true

# Server
ENVIRONMENT=production
PORT=8000
CORS_ORIGINS=https://your-domain.azurewebsites.net

# Monitoring (optional)
APPINSIGHTS_INSTRUMENTATIONKEY=xxx
```

---

## Key Files

| File | Purpose |
|------|---------|
| [`config.py`](../../src/data/config/config.py) | Main configuration |
| [`constants.py`](../../src/data/config/constants.py) | Application constants |
| [`azure_config.py`](../../src/data/config/azure_config.py) | Azure settings |
| [`env_loader.py`](../../src/utils/env_loader.py) | Environment loading |
| [`redis.conf`](../../redis.conf) | Redis settings |
| [`pytest.ini`](../../pytest.ini) | Test configuration |
| [`next.config.ts`](../../src/webui/app/next.config.ts) | Next.js config |
| [`tailwind.config.ts`](../../src/webui/app/tailwind.config.ts) | Tailwind config |

---

## Learn More

- [Startup Guide](../../STARTUP_GUIDE.md)
- [Deployment Guide](../../Deployment.md)
- [Backend Guide](./01-backend.md)
