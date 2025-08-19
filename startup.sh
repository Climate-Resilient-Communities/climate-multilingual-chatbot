#!/bin/bash
echo "🚀 Starting Climate Multilingual Chatbot FastAPI deployment..."

# Set Azure paths
WWWROOT="/home/site/wwwroot"
VENV_PATH="$WWWROOT/venv"

echo "📂 Working directory: $WWWROOT"
cd $WWWROOT

# Verify we're in the right location
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found in $WWWROOT"
    echo "📁 Current directory contents:"
    ls -la
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ ! -d "$VENV_PATH" ]; then
    echo "🔧 Creating virtual environment at $VENV_PATH..."
    python -m venv $VENV_PATH
fi

echo "🔌 Activating virtual environment..."
source $VENV_PATH/bin/activate

echo "⬆️ Upgrading pip..."
pip install --upgrade pip

echo "📥 Installing requirements..."
pip install -r requirements.txt

echo "✅ Dependencies installed successfully"

# Verify FastAPI app exists
if [ ! -f "src/webui/api/main.py" ]; then
    echo "❌ Error: FastAPI main.py not found at src/webui/api/main.py"
    echo "📁 Available files:"
    find . -name "*.py" -path "*/api/*" | head -5
    exit 1
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH="$WWWROOT:$PYTHONPATH"

# Start the FastAPI application
echo "🎯 Starting FastAPI application on port $PORT..."
echo "🔗 Module path: src.webui.api.main:app"
python -m uvicorn src.webui.api.main:app --host 0.0.0.0 --port $PORT