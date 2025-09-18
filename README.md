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
# Admin API Docs: http://localhost:3001/docs
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
# Terminal 1 - Backend API:
uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend (development mode):
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
   - **Admin API**: http://localhost:3001/docs

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
```

### Admin Dashboard Setup

The admin dashboard provides analytics, cost tracking, and user interaction insights. It runs as a standalone API server.

#### 1. Environment Variables for Admin API

Create a `.env` file in the project root with these variables:

```bash
# Admin Dashboard Authentication
ADMIN_PASSWORD=your_secure_admin_password

# Google Sheets Integration (for persistent analytics)
GOOGLE_SHEETS_ID=your_google_sheets_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
```

#### 2. Google Service Account Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Google Sheets API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it

3. **Create Service Account**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in service account details
   - Grant "Editor" role for Google Sheets access

4. **Download Credentials**:
   - In the service accounts list, click on your newly created account
   - Go to "Keys" tab > "Add Key" > "Create New Key"
   - Choose JSON format and download
   - Rename the file to `credentials.json` and place it in the project root

#### 3. Google Sheets Setup

1. **Create Analytics Spreadsheet**:
   - Create a new Google Sheets document
   - Copy the spreadsheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
   - Add this ID to your `.env` file as `GOOGLE_SHEETS_ID`

2. **Share with Service Account**:
   - Open the spreadsheet
   - Click "Share" button
   - Add your service account email (found in `credentials.json` as `client_email`)
   - Give "Editor" permissions

3. **Setup Sheets Structure**:
   The admin API will automatically create these sheets:
   - `Analytics` - User interaction data
   - `Feedback` - User feedback and ratings
   - `Costs` - Model usage cost tracking

#### 4. Running the Admin API Server

```bash
# Start the admin API server (runs on port 3001)
python admin_api_server.py

# Or run in background
nohup python admin_api_server.py &
```

The admin dashboard will be available at:
- **API Documentation**: http://localhost:3001/docs
- **Dashboard Interface**: http://localhost:9002/admin/dashboard (when Next.js frontend is running)

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

#### 6. Troubleshooting Admin Setup

**Common Issues**:

1. **Google Sheets Permission Error**:
   ```bash
   # Ensure service account email has editor access to spreadsheet
   # Check that GOOGLE_SHEETS_ID matches your spreadsheet URL
   ```

2. **Credentials File Not Found**:
   ```bash
   # Verify credentials.json is in project root
   # Check GOOGLE_SERVICE_ACCOUNT_FILE path in .env
   ```

3. **Admin Password Issues**:
   ```bash
   # Set a strong ADMIN_PASSWORD in .env file
   # Restart admin_api_server.py after changes
   ```

4. **Port Conflicts**:
   ```bash
   # Admin API runs on port 3001 by default
   # Ensure port is available or modify in admin_api_server.py
   ```

**Testing the Setup**:
```bash
# Test API endpoints
curl http://localhost:3001/health
curl -X POST http://localhost:3001/analytics/test-increment
```

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
├── credentials.json       # Google Service Account credentials
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