# Azure Single Deployment Configuration Guide

## 🚀 **Overview**

This guide outlines the Azure deployment strategy for the Climate Multilingual Chatbot, implementing a **single deployment model** where FastAPI serves the Next.js frontend as static files. This approach is based on the successful [Climate-Stories-Map](https://github.com/Climate-Resilient-Communities/Climate-Stories-Map) deployment strategy.

## 📋 **Architecture**

```
Azure App Service (Single Deployment)
├── FastAPI Backend (Python 3.11)
│   ├── API endpoints at /api/v1/*
│   ├── Health checks at /health
│   └── Static file serving for frontend
├── Next.js Frontend (Static Export)
│   ├── Built to 'out' directory
│   ├── Static assets at /_next/*
│   └── Served for all non-API routes
└── Environment Variables
    ├── Azure Cache for Redis
    ├── API Keys (Cohere, Pinecone, AWS)
    └── Production configuration
```

## ✅ **Completed Configuration**

### **1. Next.js Static Export Configuration**
- ✅ **File**: `src/webui/app/next.config.ts`
- ✅ **Configuration**:
  ```typescript
  const nextConfig: NextConfig = {
    output: 'export',
    distDir: 'out',
    // ... other config
  };
  ```

### **2. FastAPI Static File Serving**
- ✅ **File**: `src/webui/api/main.py`
- ✅ **Configuration**:
  ```python
  from fastapi.staticfiles import StaticFiles
  from fastapi.responses import FileResponse
  
  # Mount Next.js static assets
  app.mount("/_next", StaticFiles(directory="src/webui/app/out/_next"), name="next-static")
  
  # Serve frontend for all non-API routes
  @app.get("/{full_path:path}")
  async def serve_react_app(full_path: str):
      # Serve index.html for frontend routes
  ```

### **3. Build Automation**
- ✅ **File**: `build.sh`
- ✅ **Features**:
  - Automated frontend build with `npm run build`
  - Static export validation
  - FastAPI configuration verification
  - Ready for Azure deployment

### **4. GitHub Actions CI/CD**
- ✅ **File**: `.github/workflows/deploy-azure.yml`
- ✅ **Features**:
  - Node.js 18 and Python 3.11 setup
  - Frontend build and validation
  - Security audits (npm audit, pip-audit)
  - Azure App Service deployment
  - Health check validation

## ⚠️ **Remaining Azure Configuration**

### **1. Azure App Service Settings**

You need to configure these in your Azure App Service:

```bash
# App Settings in Azure Portal
CORS_ORIGINS=https://your-app.azurewebsites.net
NODE_ENV=production
PYTHON_PATH=/site/wwwroot

# Environment Variables (Already configured per your note)
COHERE_API_KEY=your-key
PINECONE_API_KEY=your-key
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-key
REDIS_URL=your-azure-cache-connection

# Additional Production Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### **2. GitHub Secrets Configuration**

Add this secret to your GitHub repository:

```
AZURE_WEBAPP_PUBLISH_PROFILE
```

Get this from Azure Portal → App Service → Deployment Center → Download publish profile.

### **3. Azure App Service Configuration**

In Azure Portal:
```yaml
Runtime Stack: Python 3.11
Always On: true
Health Check: /health
Startup Command: "uvicorn src.webui.api.main:app --host 0.0.0.0 --port $PORT"
```

## 🚀 **Deployment Process**

### **Local Testing**
```bash
# 1. Build the application
./build.sh

# 2. Test single deployment locally
uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Verify frontend is served at http://localhost:8000
# 4. Verify API endpoints at http://localhost:8000/api/v1/*
```

### **Azure Deployment**
```bash
# 1. Push to main branch
git push origin main

# 2. GitHub Actions will automatically:
#    - Build frontend (npm run build)
#    - Install Python dependencies
#    - Run security audits
#    - Deploy to Azure App Service
#    - Run health checks

# 3. Verify deployment at your Azure URL
```

## 📊 **Verification Checklist**

After deployment, verify:

- [ ] **Frontend Loading**: Main page loads at your Azure URL
- [ ] **API Endpoints**: Test `/api/v1/chat/query` endpoint
- [ ] **Static Assets**: Verify CSS and JS files load from `/_next/*`
- [ ] **Health Checks**: `/health` returns healthy status
- [ ] **Language Support**: Test multiple language queries
- [ ] **Mobile Experience**: Verify responsive design works
- [ ] **Error Handling**: Test error scenarios work correctly

## 🏆 **Benefits of Single Deployment**

1. **Simplified Architecture**: One App Service instead of two
2. **Reduced Costs**: Single Azure resource
3. **Easier CORS**: No cross-origin issues
4. **Unified Logging**: All logs in one place
5. **Simplified SSL**: One certificate for everything
6. **Faster Response**: No network latency between services

## 🔧 **Troubleshooting**

### **Common Issues**

1. **Frontend Not Loading**:
   - Check `src/webui/app/out/` directory exists
   - Verify FastAPI static file mounting
   - Check Azure startup logs

2. **API Endpoints Not Working**:
   - Verify environment variables are set
   - Check Azure App Service logs
   - Test health endpoint first

3. **Build Failures**:
   - Check Node.js and Python versions
   - Verify all dependencies are installed
   - Check build logs in GitHub Actions

## 📈 **Performance Optimizations**

- **Static Asset Caching**: Azure CDN for `/_next/*` files
- **Health Check Optimization**: Lightweight `/health` endpoint
- **Prewarming**: Background pipeline initialization
- **Connection Pooling**: Optimized for Azure Cache for Redis

## 🔒 **Security Features**

- **HTTPS Only**: Azure App Service enforces HTTPS
- **CORS Configuration**: Strict origin restrictions
- **Rate Limiting**: API endpoint protection
- **Environment Isolation**: Production secrets management
- **Security Headers**: CSRF, XSS protection

## 📚 **Reference Implementation**

This configuration is based on the successful deployment of the Climate-Stories-Map project, which uses the same single deployment strategy with FastAPI serving Next.js static files.

---

**✅ Ready for Production Deployment**: All code changes complete, Azure configuration pending secrets and App Service settings.