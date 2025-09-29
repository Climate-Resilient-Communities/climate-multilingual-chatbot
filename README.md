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

# 3. Start admin API server (optional, for analytics dashboard)
python admin_api_server.py

# 4. Access the application
# Main App: http://localhost:8000
# Admin Dashboard: http://localhost:8000/admin/dashboard
# API Docs: http://localhost:8000/docs
# Admin API Docs: http://localhost:8001/docs
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

# Terminal 3 - Admin API (optional):
python admin_api_server.py
```

### Complete Setup with Admin Dashboard

For full functionality including analytics and cost tracking:

1. **Setup Environment Variables** (see Configuration section below)
2. **Configure Google Sheets** (see Admin Dashboard Setup)
3. **Run All Services**:

   ```bash
   # Start main application
   uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload

   # Start admin API (in another terminal)
   python admin_api_server.py

   # Start frontend development server (in another terminal)
   cd src/webui/app && npm run dev
   ```

4. **Access Points**:
   - **Main Chat**: http://localhost:9002 (dev) or http://localhost:8000 (prod)
   - **Admin Dashboard**: http://localhost:9002/admin/dashboard
   - **API Documentation**: http://localhost:8000/docs
   - **Admin API**: http://localhost:8001/docs

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

# Redis (optional, uses in-memory fallback)
REDIS_URL=redis://localhost:6379

# CORS Configuration (production)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Admin Dashboard Authentication
ADMIN_PASSWORD=your_secure_admin_password

# Google Sheets Integration (for persistent analytics)
GOOGLE_SHEETS_ID=your_google_sheets_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
```

#### 5. Admin Dashboard Features

- **🔐 Password Protection**: Secure admin access
- **📊 Analytics Overview**: Total interactions, daily trends
- **💰 Cost Tracking**: Real-time cost estimates for AI models
  - Cohere Command-A: ~$5.00 per 1M tokens
  - Amazon Nova Pro: ~$0.60 per 1M tokens
  - Pinecone Vector Search: ~$0.20 per 1M tokens
- **📈 Interaction Breakdown**: User engagement metrics
- **🛡️ Safety Metrics**: Content filtering statistics
- **💾 Persistent Storage**: Data saved to Google Sheets for long-term analysis

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
│   │   └── app/           # Next.js frontend (includes admin dashboard)
│   ├── models/            # AI pipeline and models
│   ├── data/config/       # Configuration files
│   └── utils/             # Shared utilities (including cost_tracker.py)
├── admin_api_server.py    # Standalone admin API server
├── credentials.json       # Google Service Account credentials (must add yourself using Google API)
├── analytics_data.json    # Local analytics storage (auto-generated)
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

- **Secure Admin Authentication**: Uses Authorization headers instead of query parameters for admin access
- **Environment-based CORS**: CORS origins configured via `CORS_ORIGINS` environment variable
- **No Hardcoded Secrets**: All passwords and credentials stored in environment variables
- **Input Validation**: Comprehensive input validation and sanitization
- **Rate Limiting**: Built-in abuse protection  
- **Content Filtering**: Advanced filtering for harmful/off-topic queries
- **URL Validation**: Citation URLs validated for security
- **Secure Logging**: Sensitive data excluded from application logs
- **No Client-Side Secrets**: No authentication credentials stored in frontend bundles

### Admin Security

The admin dashboard uses secure authentication:

- **Backend Verification**: Admin credentials verified server-side only
- **Bearer Token Auth**: Uses `Authorization: Bearer <password>` headers
- **No URL Exposure**: Admin passwords never appear in URLs or logs
- **Environment Config**: Admin password set via `ADMIN_PASSWORD` environment variable

```bash
# Secure admin access example
curl -H "Authorization: Bearer your_admin_password" \
     http://localhost:8000/api/v1/admin/analytics
```## 🔄 Deployment

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
