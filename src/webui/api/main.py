"""
FastAPI backend for Climate Multilingual Chatbot
Integrates with existing pipeline components from src/models/
"""

import os
import time
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import existing pipeline components
from src.models.climate_pipeline import ClimateQueryPipeline
from src.models.conversation_parser import ConversationParser
from src.models.query_routing import MultilingualRouter
from src.models.redis_cache import ClimateCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global pipeline instance
pipeline: ClimateQueryPipeline = None
conversation_parser: ConversationParser = None
router: MultilingualRouter = None
cache: ClimateCache = None
prewarm_completed = False

async def background_prewarm():
    """Prewarm pipeline in background to avoid blocking startup"""
    global prewarm_completed
    try:
        logger.info("🔥 Starting background pipeline prewarming...")
        if pipeline:
            await pipeline.prewarm()
            prewarm_completed = True
            logger.info("✅ Background prewarming completed")
    except Exception as e:
        logger.error(f"❌ Background prewarming failed: {str(e)}")
        prewarm_completed = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup pipeline on startup/shutdown"""
    global pipeline, conversation_parser, router, cache
    
    logger.info("🚀 Starting Climate Chatbot API...")
    
    try:
        # Initialize core components
        logger.info("Initializing pipeline components...")
        
        # Climate processing pipeline (main component)
        pipeline = ClimateQueryPipeline()
        
        # Start prewarm in background to not block startup
        asyncio.create_task(background_prewarm())
        logger.info("✅ Climate pipeline initialized (prewarming in background)")
        
        # Conversation parser for history handling
        conversation_parser = ConversationParser()
        logger.info("✅ Conversation parser initialized")
        
        # Language router for model selection
        router = MultilingualRouter()
        logger.info("✅ Language router initialized")
        
        # Redis cache for sessions and feedback
        cache = ClimateCache()
        logger.info("✅ Redis cache initialized")
        
        logger.info("🎉 All components initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize components: {str(e)}")
        raise
    
    yield
    
    # Cleanup on shutdown
    logger.info("🧹 Cleaning up pipeline...")
    try:
        if pipeline:
            await pipeline.cleanup()
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {str(e)}")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="Climate Multilingual Chatbot API",
    description="Backend API for climate change information chatbot with multilingual support",
    version="1.0.0",
    lifespan=lifespan
)

# Environment-driven CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:9002").split(",")
cors_origins = [origin.strip() for origin in cors_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Environment-driven for prod/dev
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Simple in-memory rate limiter (for production, use Redis-based limiter)
rate_limit_storage = defaultdict(lambda: deque())

def check_rate_limit(client_ip: str, endpoint: str, max_requests: int = 10, window_minutes: int = 1) -> bool:
    """Simple token bucket rate limiter"""
    now = time.time()
    window_seconds = window_minutes * 60
    
    # Clean old requests
    bucket_key = f"{client_ip}:{endpoint}"
    bucket = rate_limit_storage[bucket_key]
    
    while bucket and bucket[0] < now - window_seconds:
        bucket.popleft()
    
    # Check if under limit
    if len(bucket) >= max_requests:
        return False
    
    # Add current request
    bucket.append(now)
    return True

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_and_log(request: Request, call_next):
    start_time = time.time()
    
    # Add correlation ID
    request_id = f"req_{int(time.time() * 1000)}"
    request.state.request_id = request_id
    
    # Simple rate limiting for API endpoints
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    # Allow disabling rate limits for local batch testing via env
    if os.getenv("DISABLE_RATE_LIMIT", "").strip().lower() in ("1", "true", "yes"):
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"REQUEST {request.method} {request.url.path} "
            f"status={response.status_code} time={process_time:.3f}s id={request_id} ip={client_ip}"
        )
        response.headers["X-Request-ID"] = request_id
        return response
    
    # Environment-based rate limits
    environment = os.getenv("ENVIRONMENT", "production").lower()
    rate_limits_config = {
        "development": {
            "/api/v1/chat/query": 60,      # Higher for testing
            "/api/v1/feedback/submit": 100
        },
        "staging": {
            "/api/v1/chat/query": 30,
            "/api/v1/feedback/submit": 60
        },
        "production": {
            "/api/v1/chat/query": 20,      # Conservative for prod
            "/api/v1/feedback/submit": 50
        }
    }
    rate_limits = rate_limits_config.get(environment, rate_limits_config["production"])
    
    if path in rate_limits:
        max_requests = rate_limits[path]
        if not check_rate_limit(client_ip, path, max_requests):
            logger.warning(f"Rate limit exceeded: ip={client_ip} path={path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "type": "rate_limit_error",
                        "message": "Too many requests. Please try again later.",
                        "retryable": True,
                        "request_id": request_id
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Window": "60",  # 60 seconds
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                    "Retry-After": "60"
                }
            )
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"REQUEST {request.method} {request.url.path} "
        f"status={response.status_code} time={process_time:.3f}s id={request_id} ip={client_ip}"
    )
    
    response.headers["X-Request-ID"] = request_id
    return response

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies pipeline is initialized and prewarmed"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    # Check if basic components are ready
    basic_ready = all([
        pipeline is not None,
        conversation_parser is not None,
        router is not None,
        cache is not None
    ])
    
    # Full readiness includes prewarming completion
    if not basic_ready:
        raise HTTPException(status_code=503, detail="Components not initialized")
    
    return {
        "status": "ready" if prewarm_completed else "initializing",
        "pipeline_initialized": pipeline is not None,
        "prewarm_completed": prewarm_completed,
        "components": {
            "climate_pipeline": pipeline is not None,
            "conversation_parser": conversation_parser is not None,
            "language_router": router is not None,
            "redis_cache": cache is not None
        },
        "timestamp": time.time()
    }

@app.get("/health/live")
async def liveness_check():
    """Liveness check - verifies basic functionality"""
    try:
        # Test basic pipeline functionality
        if pipeline:
            # Quick test without full processing
            test_result = {"status": "live"}
        else:
            raise HTTPException(status_code=503, detail="Pipeline not available")
            
        return {
            "status": "live",
            "timestamp": time.time(),
            "test_result": test_result
        }
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Liveness check failed: {str(e)}")

# Dependency to get pipeline instance
def get_pipeline() -> ClimateQueryPipeline:
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return pipeline

def get_conversation_parser() -> ConversationParser:
    if conversation_parser is None:
        raise HTTPException(status_code=503, detail="Conversation parser not initialized")
    return conversation_parser

def get_router() -> MultilingualRouter:
    if router is None:
        raise HTTPException(status_code=503, detail="Language router not initialized")
    return router

def get_cache() -> ClimateCache:
    if cache is None:
        raise HTTPException(status_code=503, detail="Cache not initialized")
    return cache

# Static file serving for single deployment (Next.js frontend)
# Mount the static files directory for Next.js assets
frontend_out_dir = os.path.join(os.path.dirname(__file__), "..", "app", "out")
if os.path.exists(frontend_out_dir):
    # Mount Next.js static assets
    app.mount("/_next", StaticFiles(directory=os.path.join(frontend_out_dir, "_next")), name="next-static")
    logger.info(f"✅ Mounted Next.js static files from {frontend_out_dir}")

# Import and include routers
from .routers import chat, languages, feedback, streaming

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(languages.router, prefix="/api/v1", tags=["languages"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(streaming.router, prefix="/api/v1", tags=["streaming"])

# Serve Next.js frontend for all non-API routes (single deployment)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve Next.js frontend for all non-API routes"""
    # Skip API routes - let FastAPI routers handle them
    if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("docs"):
        # These will be handled by other routes
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    # Serve the index.html for all frontend routes
    frontend_index = os.path.join(os.path.dirname(__file__), "..", "app", "out", "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    
    # Fallback API info if frontend not built
    return {
        "message": "Climate Multilingual Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "note": "Frontend not built. Run 'npm run build' in src/webui/app/"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(f"Global exception in request {request_id}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "type": "server_error",
                "message": "An internal error occurred",
                "retryable": True,
                "request_id": request_id
            }
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )