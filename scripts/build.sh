#!/bin/bash

# Build script for Azure single deployment
# Based on Climate-Stories-Map deployment model
# Builds Next.js frontend and prepares for FastAPI static serving

# Exit on error
set -e

echo "🚀 Starting Climate Multilingual Chatbot build process..."
echo "📊 Build strategy: Single deployment (FastAPI serves Next.js static files)"

# Build the frontend
echo ""
echo "📦 Building Next.js frontend..."
cd src/webui/app

# Install dependencies
echo "Installing frontend dependencies..."
npm install

# Build the application for static export
echo "Building frontend for static export..."
npm run build

# Check if build was successful
if [ ! -d "out" ]; then
    echo "❌ Frontend build failed - 'out' directory not found"
    exit 1
fi

echo "✅ Frontend build successful - static files generated in 'out' directory"

# Return to root directory
cd ../../..

# Check FastAPI static file configuration
echo ""
echo "🔍 Verifying FastAPI static file configuration..."

if grep -q "StaticFiles" src/webui/api/main.py; then
    echo "✅ FastAPI configured to serve static files"
else
    echo "⚠️  Warning: FastAPI may not be configured for static file serving"
fi

echo ""
echo "🎉 Build complete! Single deployment ready."
echo ""
echo "📋 Deployment structure:"
echo "  ├── FastAPI backend (src/webui/api/main.py)"
echo "  ├── Next.js static files (src/webui/app/out/)"
echo "  ├── Static assets mounted at /_next"
echo "  └── Frontend served for all non-API routes"
echo ""
echo "🚀 To test locally:"
echo "  uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "🌐 Ready for Azure App Service deployment!"