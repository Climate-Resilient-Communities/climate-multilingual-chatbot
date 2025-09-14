#!/usr/bin/env python3
"""
Standalone admin API server for the climate chatbot dashboard.
This runs independently of the main application to avoid dependency conflicts.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import Dict, Any

app = FastAPI(title="Climate Chatbot Admin API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin password from environment or default
ADMIN_PASSWORD = "climate_admin_2024"#os.getenv("ADMIN_PASSWORD", "climate_admin_2024")

@app.get("/")
async def root():
    return {"message": "Climate Chatbot Admin API", "status": "running"}

@app.get("/admin/analytics")
async def get_analytics(password: str = Query(..., description="Admin password")):
    """
    Get analytics data for the admin dashboard.
    Requires admin password for authentication.
    """
    
    # Verify admin password
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    # Mock analytics data that matches the frontend's expected format
    analytics_data = {
        "summary": {
            "total_feedback": 186,
            "thumbs_up": 127,
            "thumbs_down": 59,
            "positive_percentage": 68.3,
            "negative_percentage": 31.7,
            "unrated": 0
        },
        "sheet_info": {
            "sheets_id": "1ABC123XYZ789_sample_sheet_id",
            "worksheet_title": "MLCC Feedback Data",
            "last_updated": "2025-09-13T15:30:00Z"
        }
    }
    
    return analytics_data

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "admin-api"}

if __name__ == "__main__":
    print("🚀 Starting Climate Chatbot Admin API...")
    print(f"📊 Admin dashboard will be available at: http://localhost:8002/admin/analytics")
    print(f"🔑 Admin password: {ADMIN_PASSWORD}")
    print("="*60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,  # Use different port to avoid conflicts
        reload=False,  # Disable reload to avoid warnings
        log_level="info"
    )