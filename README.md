# Climate Multilingual Chatbot

A comprehensive multilingual climate change assistant powered by Amazon Bedrock Nova and Cohere Command-A models. Supports 20+ languages with intelligent routing, real-time responses, and comprehensive citation system.

## 🌍 Features

- **Multilingual Support**: 180+ languages with intelligent model routing
- **Real-time Chat**: Server-sent events for streaming responses
- **Smart Caching**: Redis-based caching with bypass functionality  
- **Citation System**: Comprehensive source attribution with link validation
- **Safety Filters**: Advanced off-topic and harmful content filtering
- **Export Functionality**: Save conversations in multiple formats
- **Responsive Design**: Mobile-first, accessible UI with dark/light modes

## 🏗️ Architecture

- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, static export
- **Backend**: FastAPI with Python 3.12, serves both API and static files
- **AI Models**: Amazon Bedrock Nova Pro, Cohere Command-A
- **Vector Search**: Pinecone for climate knowledge retrieval
- **Caching**: Redis for performance optimization
- **Deployment**: Single Azure App Service deployment

## 🚀 Quick Start

### Production Build & Deploy

```bash
# 1. Build the complete application
./build.sh

# 2. Start production server (serves both API and frontend)
uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000

# 3. Access the application
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

### Development Setup

```bash
# Install Python dependencies
poetry install

# Install frontend dependencies
cd src/webui/app
npm install
cd ../../..

# Start development servers (run in separate terminals)
# Backend:
uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (development mode):
cd src/webui/app && npm run dev
```

## 🔧 Configuration

### Required Environment Variables

```bash
# AWS Bedrock
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Cohere
COHERE_API_KEY=your_cohere_key

# Pinecone
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX_NAME=your_index_name

# Redis (recommended for caching)
REDIS_URL=redis://localhost:6379
# Or use individual settings:
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=your_password  # if authentication is enabled
# REDIS_SSL=true  # for secure connections
```

### Redis Setup (Important!)

Redis is essential for caching responses and preventing regeneration of answers. **Without Redis persistence, all cached responses are lost when the application restarts.**

#### Quick Start (Development)
```bash
# Start Redis with proper persistence
./start-redis.sh
```

#### Production Setup

**Option 1: System Service (Recommended for VPS/EC2)**
```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
# Copy persistence settings from redis.conf to /etc/redis/redis.conf
```

**Option 2: Managed Redis (Recommended for Cloud)**
Use a managed service that handles persistence automatically:
- AWS ElastiCache for Redis
- Azure Cache for Redis
- Redis Enterprise Cloud
- Upstash Redis

Update environment variables with your managed Redis connection details.

**Why this matters:** See [REDIS_CACHE_FIX.md](REDIS_CACHE_FIX.md) for details on the cache persistence issue and solution.

## 📋 Supported Languages

### Command-A Model (22 languages)
Arabic, Bengali, Chinese, Filipino, French, Gujarati, Korean, Persian, Russian, Tamil, Urdu, Vietnamese, Polish, Turkish, Dutch, Czech, Indonesian, Ukrainian, Romanian, Greek, Hindi, Hebrew

### Nova Model (6 languages)  
English, Spanish, Japanese, German, Swedish, Danish

## 🧪 Testing

The application includes comprehensive multilingual testing:

```bash
# Run the test suite (when test files are present)
python comprehensive_multilingual_test.py
```

**Latest Test Results**: 64.6% overall score
- Language Detection: 87.2% (Excellent)
- Query Rewriting: 96.6% (Outstanding) 
- Citations: 60.5% (Good)
- Answer Quality: 57.6% (Acceptable)
- Safety Filtering: 37.1% (Needs Work)

## 📁 Project Structure

```
├── src/
│   ├── webui/
│   │   ├── api/           # FastAPI backend
│   │   └── app/           # Next.js frontend
│   ├── models/            # AI pipeline and models
│   ├── data/config/       # Configuration files
│   └── utils/             # Shared utilities
├── build.sh              # Production build script
├── STARTUP_GUIDE.md       # Detailed setup instructions
└── ARCHITECTURE.md        # Technical architecture details
```

## 📚 Documentation

- **[Startup Guide](STARTUP_GUIDE.md)**: Detailed setup and deployment instructions
- **[Architecture](ARCHITECTURE.md)**: Technical architecture and design decisions
- **[Azure Deployment](AZURE_DEPLOYMENT_GUIDE.md)**: Azure-specific deployment guide
- **[Info Folder](info/)**: Additional technical documentation and reports

## 🛡️ Security

- Input validation and sanitization
- Rate limiting and abuse protection  
- Content filtering for harmful/off-topic queries
- URL validation for citations
- CORS protection
- No sensitive data logging

## 🔄 Deployment

The application uses a **single deployment model**:
1. Next.js builds to static files (`out/` directory)
2. FastAPI serves both API endpoints and static files
3. All traffic goes through the FastAPI server on port 8000

## 📊 Performance

- **Language Detection**: <100ms response time
- **Query Processing**: <2s average response time
- **Caching**: Redis-based with intelligent bypass
- **Static Assets**: Optimized builds with compression

## 🤝 Contributing

1. Follow the existing code style and patterns
2. Run tests before submitting changes
3. Update documentation for significant changes
4. Use conventional commit messages

## 📄 License

See LICENSE file for details.

---

Built with ❤️ for global climate education and awareness.