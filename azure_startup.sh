#!/bin/bash
# Azure App Service startup script for the climate chatbot

# Set necessary environment variables for Azure
export STREAMLIT_WATCHER_TYPE=none
export STREAMLIT_SERVER_RUN_ON_SAVE=false
export HF_HOME=/tmp/huggingface  # Replace deprecated TRANSFORMERS_CACHE
export TRANSFORMERS_CACHE=/tmp/huggingface/transformers

# Create temp directories if they don't exist
mkdir -p /tmp/huggingface/transformers

# Set up Python event loop properly before starting
echo "Initializing event loop configuration..."
python -c '
import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
print("Event loop configured successfully")
'

# Start Streamlit with proper configuration
echo "Starting Streamlit application..."
streamlit run /app/src/webui/app_nova.py --server.port=$PORT --server.address=0.0.0.0