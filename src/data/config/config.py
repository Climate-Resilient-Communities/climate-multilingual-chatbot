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
    "pinecone_index": os.getenv("PINECONE_INDEX_NAME", "climate-change-adaptation-index-10-24-prod"),
    # Base knobs
    "top_k_retrieve": 15,           # legacy top-k before rerank (kept for compatibility)
    "top_k_rerank": 5,              # cross-encoder final cap
    "hybrid_alpha": 0.5,            # dense/sparse fusion weight
    # Overfetch controls: balance latency vs recall
    "overfetch": 8,                 # smaller initial vector overfetch for interactive UX
    # Similarity gating
    "similarity_base": 0.65,
    "similarity_fallback": 0.55,
    "adaptive_margin": 0.10,
    "min_kept": 3,
    # Refill
    "refill_enabled": False,        # keep off for interactivity; can flip on for batch
    "refill_overfetch": 6,          # stays modest if enabled
    # MMR diversification
    "mmr_enabled": True,
    "mmr_lambda": 0.30,
    "mmr_overfetch": 6,             # keep tight to limit extra embeddings
    # Optional quality gates (None disables the filter)
    "min_pinecone_score": None,     # e.g., 0.30 for cosine metric; confirm index metric first
    "min_rerank_score": 0.70,       # tuned via calibration; drop very weak contexts
    "auto_calibrate_rerank_floor": False,  # placeholder; not active in code yet
    # Filters & boosts
    "filters": {
        "lang": "en",
        "audience_blocklist": ["K-2", "K-6", "K-8", "K-12", "lesson plan", "curriculum"],
        "science_min_year": 2015,
        "doc_type_preferences": {
            "howto": ["guideline", "factsheet", "toolkit", "report"],
            "science": ["peer_reviewed", "report"],
        },
    },
    "boosts": {
        "preferred_domains": [
            # Federal Canadian sources
            "canada.gc.ca", "www.canada.ca", "canada.ca",
            "nrcan.gc.ca", "ec.gc.ca", "climate.canada.ca",
            
            # Provincial sources
            "ontario.ca", "www.ontario.ca", "climatechange.ontario.ca",
            
            # GTA municipal sources
            "toronto.ca", "www.toronto.ca",
            "peelregion.ca", "www.peelregion.ca",
            "mississauga.ca", "www.mississauga.ca",
            "brampton.ca", "www.brampton.ca",
            "markham.ca", "www.markham.ca",
            "vaughan.ca", "www.vaughan.ca",
            "richmond-hill.ca", "www.richmond-hill.ca",
            "york.ca", "www.york.ca",
            "durham.ca", "www.durham.ca",
            "halton.ca", "www.halton.ca",
            
            # Canadian research/educational
            "nrcan.ca", "statcan.gc.ca", "agr.gc.ca",
            "climatedata.ca", "climateatlas.ca",
            "cleanairpartnership.org",
            
            # International authoritative (lower priority)
            "ipcc.ch", "unfccc.int"
        ],
        "domain_boost_weight": 0.25,  # Increased from 0.10 to 0.25 for stronger Canadian preference
        
        # NEW: Location-aware query enhancement
        "location_boosts": {
            "canadian_places": {
                "keywords": [
                    "canada", "canadian", "ontario", "toronto", "gta", 
                    "rexdale", "etobicoke", "north york", "scarborough",
                    "mississauga", "brampton", "markham", "vaughan",
                    "peel region", "york region", "durham region", "halton region"
                ],
                "boost_weight": 0.30,  # Strong boost for location-specific queries
            }
        }
    },
    # Diagnostics
    "log_retrieval_diagnostics": True,
    # Safety caps (legacy)
    "max_docs_before_rerank": 8,
    "final_max_docs": 5,
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