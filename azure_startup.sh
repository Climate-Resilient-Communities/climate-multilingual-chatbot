#!/bin/bash
# Azure App Service startup script for the climate chatbot

# Set necessary environment variables for Azure
export STREAMLIT_WATCHER_TYPE=none
export STREAMLIT_SERVER_RUN_ON_SAVE=false
export RAY_object_store_memory=10000000  # 10MB for Ray object store
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

# Check Ray configuration
echo "Configuring Ray with reduced memory footprint..."
python -c '
import os
import ray
import json
import tempfile

tmp_dir = tempfile.mkdtemp(prefix="ray_")
print(f"Created Ray temporary directory: {tmp_dir}")

# Configure Ray with minimal shared memory
try:
    if not ray.is_initialized():
        ray.init(
            object_store_memory=10 * 1024 * 1024,  # 10 MB
            object_spilling_config=json.dumps({
                "type": "filesystem",
                "params": {"directory_path": tmp_dir}
            }),
            num_cpus=1,
            dashboard_port=0,
            include_dashboard=False,
            ignore_reinit_error=True,
            _system_config={
                "object_spilling_threshold": 0.8,
                "max_io_workers": 1,
                "automatic_object_spilling_enabled": True,
            }
        )
        print("Ray initialized with minimal memory configuration")
    else:
        print("Ray was already initialized")
except Exception as e:
    print(f"Warning: Ray initialization error: {e}")
    print("App will continue with limited functionality")
'

# Start Streamlit with proper configuration
echo "Starting Streamlit application..."
streamlit run /app/src/webui/app_nova.py --server.port=$PORT --server.address=0.0.0.0