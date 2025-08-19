#!/bin/bash
# Azure App Service startup script for Climate Multilingual Chatbot

echo "🚀 Starting Climate Multilingual Chatbot..."
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "PORT: $PORT"

# Set environment variables
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Create necessary directories
mkdir -p /tmp/logs /tmp/huggingface

# Verify we're in the right directory
cd /home/site/wwwroot
echo "Files in current directory:"
ls -la

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip install --no-cache-dir --timeout 300 -r requirements.txt
else
    echo "⚠️ requirements.txt not found, skipping dependency installation"
fi

# Verify the main module exists
if [ -f "src/webui/api/main.py" ]; then
    echo "✅ FastAPI main module found"
else
    echo "❌ FastAPI main module not found at src/webui/api/main.py"
    echo "Available files:"
    find . -name "*.py" | head -10
    exit 1
fi

# Start the FastAPI application with error handling
echo "🌐 Starting FastAPI server on port $PORT..."
exec python -m uvicorn src.webui.api.main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 120 --log-level info