"""
Minimal FastAPI server for testing without heavy dependencies
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Climate Multilingual Chatbot API (Demo)",
    description="Minimal backend API for testing the frontend",
    version="1.0.0-demo"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9002", "http://127.0.0.1:9002"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Static file serving for Next.js frontend
frontend_out_dir = os.path.join(os.path.dirname(__file__), "src", "webui", "app", "out")
if os.path.exists(frontend_out_dir):
    # Mount static assets
    static_dir = os.path.join(frontend_out_dir, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static-assets")
        logger.info(f"✅ Mounted static assets from {static_dir}")
    
    logger.info(f"✅ Frontend directory found at {frontend_out_dir}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Climate Multilingual Chatbot API is running in demo mode",
        "version": "1.0.0-demo"
    }

@app.get("/api/v1/languages/supported")
async def get_supported_languages():
    """Mock endpoint for supported languages"""
    return {
        "languages": [
            {"code": "en", "name": "English", "native_name": "English"},
            {"code": "es", "name": "Spanish", "native_name": "Español"},
            {"code": "fr", "name": "French", "native_name": "Français"},
            {"code": "de", "name": "German", "native_name": "Deutsch"},
            {"code": "zh", "name": "Chinese", "native_name": "中文"},
        ]
    }

@app.post("/api/v1/chat/query")
async def chat_query(request_data: dict):
    """Mock chat endpoint"""
    query = request_data.get("query", "")
    language = request_data.get("language", "en")
    
    return {
        "response": f"This is a demo response to your query: '{query}' in {language}. The full chatbot features require API keys to be configured.",
        "language": language,
        "citations": [],
        "conversation_id": "demo-conversation-123"
    }

@app.get("/favicon.ico")
async def get_favicon():
    """Serve favicon.ico"""
    favicon_path = os.path.join(frontend_out_dir, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return JSONResponse(status_code=404, content={"detail": "Favicon not found"})

@app.get("/Logo.png")
async def get_logo():
    """Serve Logo.png"""
    logo_path = os.path.join(frontend_out_dir, "Logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    return JSONResponse(status_code=404, content={"detail": "Logo not found"})

# Serve Next.js frontend for all non-API routes
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve Next.js frontend for all non-API routes"""
    # Skip API routes
    if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("docs"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    # Serve the index.html for all frontend routes
    frontend_index = os.path.join(frontend_out_dir, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    
    return {
        "message": "Climate Multilingual Chatbot API (Demo Mode)",
        "version": "1.0.0-demo",
        "docs": "/docs",
        "health": "/health",
        "note": "This is a demo version. Configure API keys in .env for full functionality."
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
