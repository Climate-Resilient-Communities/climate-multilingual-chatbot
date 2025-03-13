"""
Centralized constants for the application
"""
from enum import Enum
from typing import Dict, List

class ModelType(Enum):
    NOVA = "nova"
    CLAUDE = "claude"
    GPT = "gpt"

class LanguageCode(Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"

# Model configuration constants
MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.7
TOP_P = 0.8
RETRY_ATTEMPTS = 3
REQUEST_TIMEOUT = 300

# Cache configuration
CACHE_EXPIRATION = 3600  # 1 hour
MAX_CACHE_SIZE = 10000

# Retrieval configuration
MAX_DOCUMENTS = 5
HYBRID_ALPHA = 0.5
RERANK_THRESHOLD = 0.7

# Error codes
ERROR_CODES = {
    "INITIALIZATION_ERROR": "E001",
    "MODEL_ERROR": "E002",
    "REDIS_ERROR": "E003",
    "RETRIEVAL_ERROR": "E004",
    "VALIDATION_ERROR": "E005",
    "TRANSLATION_ERROR": "E006"
}

# Response templates
RESPONSE_TEMPLATES = {
    "error": {
        "model_unavailable": "The model is temporarily unavailable. Please try again later.",
        "invalid_input": "The provided input is invalid. Please check and try again.",
        "service_error": "An error occurred while processing your request."
    },
    "success": {
        "processing": "Processing your request...",
        "complete": "Request completed successfully."
    }
}

# Supported language mappings
LANGUAGE_MAPPINGS: Dict[str, Dict[str, str]] = {
    "en": {"name": "English", "code": "en", "native": "English"},
    "es": {"name": "Spanish", "code": "es", "native": "Español"},
    "fr": {"name": "French", "code": "fr", "native": "Français"},
    "de": {"name": "German", "code": "de", "native": "Deutsch"},
    "zh": {"name": "Chinese", "code": "zh", "native": "中文"},
    "ja": {"name": "Japanese", "code": "ja", "native": "日本語"},
    "ko": {"name": "Korean", "code": "ko", "native": "한국어"}
}