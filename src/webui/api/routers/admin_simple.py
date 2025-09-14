"""
Simple admin API endpoints without external dependencies
"""
import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query

# Setup logging
logger = logging.getLogger(__name__)

# Router setup
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

def verify_admin_password(password: str) -> bool:
    """Verify admin password against environment variable"""
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        logger.error("ADMIN_PASSWORD not configured")
        return False
    return password == admin_password

def get_admin_auth(password: str = Query(..., description="Admin password")):
    """Dependency to verify admin authentication"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return True

@router.get("/analytics")
async def get_analytics(password: str = Query(..., description="Admin password")) -> Dict[str, Any]:
    """
    Get basic analytics data (mock data for now until Google Sheets API is set up)
    """
    # Verify password
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    try:
        # Mock data for demonstration
        analytics_data = {
            "summary": {
                "total_feedback": 127,
                "thumbs_up": 89,
                "thumbs_down": 38,
                "positive_percentage": 70.1,
                "negative_percentage": 29.9,
                "unrated": 0
            },
            "sheet_info": {
                "sheets_id": os.getenv("GOOGLE_SHEETS_ID", "not_configured"),
                "worksheet_title": "Demo Data",
                "last_updated": "2025-09-13T15:45:00Z",
                "note": "This is mock data. Google Sheets API integration pending."
            }
        }
        
        logger.info(f"Analytics data retrieved (mock): {analytics_data['summary']}")
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error retrieving analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")

@router.get("/health")
async def admin_health(password: str = Query(..., description="Admin password")) -> Dict[str, str]:
    """Health check for admin endpoints"""
    # Verify password
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    return {"status": "healthy", "message": "Admin API is operational (simplified version)"}