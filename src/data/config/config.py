"""
Application configuration settings
"""
from pathlib import Path
import os
from typing import Dict, Any

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "src" / "data"

# Model configurations
MODEL_CONFIG = {
    "nova": {
        "model_id": "amazon.nova-lite-v1:0",
        "region": "us-east-1",
        "max_tokens": 2000,
        "temperature": 0.7,
        "top_p": 0.8
    }
}

# Retrieval configurations
RETRIEVAL_CONFIG = {
    "pinecone_index": "climate-change-adaptation-index-10-24-prod",
    "top_k_retrieve": 15,
    "top_k_rerank": 5,
    "hybrid_alpha": 0.5
}

# Redis configurations
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": 0,
    "expiration": 3600  # 1 hour cache expiration
}

# API configurations
API_CONFIG = {
    "aws": {
        "region": "us-east-1",
        "timeout": 300,
        "retries": 3
    },
    "pinecone": {
        "environment": "gcp-starter"
    }
}

# Logging configurations
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}