#!/bin/bash
echo "Starting Climate Multilingual Chatbot deployment..."

# Install Python dependencies if not already installed
echo "Installing Python dependencies..."
if [ ! -d "/home/site/wwwroot/venv" ]; then
    echo "Creating virtual environment..."
    python -m venv /home/site/wwwroot/venv
fi

source /home/site/wwwroot/venv/bin/activate
pip install --upgrade pip
pip install -r /home/site/wwwroot/requirements.txt

echo "Dependencies installed successfully"

# Start the FastAPI application
echo "Starting FastAPI application..."
cd /home/site/wwwroot
python -m uvicorn src.webui.api.main:app --host 0.0.0.0 --port $PORT