#!/usr/bin/env python3
"""
DEPRECATED: Use uvicorn directly instead

Start the FastAPI backend server for local development:
uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload

URLs:
📍 API: http://localhost:8000
📚 Docs: http://localhost:8000/docs
🏥 Health: http://localhost:8000/health
"""

print("⚠️  DEPRECATED: Use uvicorn directly instead:")
print("   uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload")
print()
print("URLs:")
print("📍 API: http://localhost:8000")
print("📚 Docs: http://localhost:8000/docs")
print("🏥 Health: http://localhost:8000/health")