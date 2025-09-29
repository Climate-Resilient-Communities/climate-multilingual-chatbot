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
    Get comprehensive analytics data by proxying to the dashboard server
    """
    # Verify password
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    try:
        # Proxy to the dashboard server for comprehensive analytics
        import httpx
        
        # Get dashboard server URL from environment or use default
        dashboard_host = os.getenv("DASHBOARD_HOST", "localhost")
        dashboard_port = os.getenv("DASHBOARD_PORT", "8001")
        dashboard_url = f"http://{dashboard_host}:{dashboard_port}/admin/analytics"
        
        params = {"password": password}
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(dashboard_url, params=params)
            
            if response.status_code == 200:
                analytics_data = response.json()
                logger.info(f"Analytics retrieved from dashboard server ({len(analytics_data)} sections)")
                return analytics_data
            elif response.status_code == 401:
                logger.error("Dashboard server authentication failed")
                raise HTTPException(status_code=401, detail="Invalid admin credentials")
            else:
                logger.warning(f"Dashboard server error: {response.status_code}")
                raise Exception(f"Dashboard server returned {response.status_code}")
                
    except httpx.TimeoutException:
        logger.error("Dashboard server timeout")
        raise HTTPException(status_code=503, detail="Dashboard server timeout")
    except httpx.ConnectError:
        logger.warning("Dashboard server unavailable, using fallback data")
    except Exception as e:
        logger.warning(f"Dashboard server error: {e}, using fallback data")
        
        # Production fallback - provide minimal data structure when dashboard is unavailable
        from datetime import datetime
        
        fallback_data = {
            "summary": {
                "total_feedback": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "positive_percentage": 0.0,
                "negative_percentage": 0.0,
                "unrated": 0
            },
            "sheet_info": {
                "sheets_id": os.getenv("GOOGLE_SHEETS_ID", "not_configured"),
                "worksheet_title": "Service Unavailable",
                "last_updated": datetime.now().isoformat() + "Z",
                "note": "Dashboard service unavailable. Please check admin server status."
            },
            "cost_analytics": {
                "total_cost": 0.0,
                "total_interactions": 0,
                "model_breakdown": {},
                "cost_summary": {"cohere_cost": 0.0, "nova_cost": 0.0, "pinecone_cost": 0.0},
                "recent_interactions": [],
                "interaction_breakdown": {
                    "on-topic": 0, "off-topic": 0, "harmful": 0,
                    "climate_response": 0, "vector_search": 0, "translation": 0
                },
                "language_breakdown": {},
                "detailed_queries": {"on_topic": [], "off_topic": [], "harmful": []}
            }
        }
        
        logger.info("Using fallback analytics data - dashboard server unavailable")
        return fallback_data

@router.get("/health")
async def admin_health(password: str = Query(..., description="Admin password")) -> Dict[str, str]:
    """Health check for admin endpoints"""
    # Verify password
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    return {"status": "healthy", "message": "Admin API is operational (simplified version)"}