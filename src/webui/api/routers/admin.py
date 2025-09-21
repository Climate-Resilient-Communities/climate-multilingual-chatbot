"""
Admin API endpoints for analytics and dashboard
"""
import os
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import gspread
from google.oauth2.service_account import Credentials
import json

# Setup logging
logger = logging.getLogger(__name__)

# Router setup
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
security = HTTPBearer(auto_error=False)

# Admin authentication
def verify_admin_password(password: str) -> bool:
    """Verify admin password against environment variable"""
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        logger.error("ADMIN_PASSWORD not configured")
        return False
    return password == admin_password

def get_admin_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Dependency to verify admin authentication using Authorization header"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not verify_admin_password(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return True

# Legacy query parameter auth for backward compatibility
def get_admin_auth_query(password: str = Query(..., description="Admin password")):
    """Dependency to verify admin authentication using query parameter (deprecated)"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return True

def get_google_sheets_client():
    """Initialize Google Sheets client using service account credentials"""
    try:
        # Try to get credentials from environment variable (JSON string)
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if creds_json:
            creds_info = json.loads(creds_json)
            credentials = Credentials.from_service_account_info(
                creds_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
        else:
            # Fallback to service account file
            creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
            if not os.path.exists(creds_file):
                raise FileNotFoundError(f"Google service account file not found: {creds_file}")
            
            credentials = Credentials.from_service_account_file(
                creds_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
        
        return gspread.authorize(credentials)
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Google Sheets")

@router.post("/verify")
async def verify_admin_credentials(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Verify admin credentials
    Returns success if credentials are valid
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not verify_admin_password(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    return {"status": "verified", "message": "Admin credentials are valid"}

@router.get("/analytics")
async def get_analytics(admin_auth: bool = Depends(get_admin_auth)) -> Dict[str, Any]:
    """
    Get analytics data from Google Sheets feedback
    Returns thumbs up/down counts and basic stats
    """
    try:
        sheets_id = os.getenv("GOOGLE_SHEETS_ID")
        if not sheets_id:
            raise HTTPException(status_code=500, detail="Google Sheets ID not configured")
        
        # Initialize Google Sheets client
        gc = get_google_sheets_client()
        sheet = gc.open_by_key(sheets_id)
        
        # Get the first worksheet (assuming feedback is in the first sheet)
        worksheet = sheet.get_worksheet(0)
        
        # Get all records
        records = worksheet.get_all_records()
        
        # Initialize counters
        thumbs_up = 0
        thumbs_down = 0
        total_feedback = len(records)
        
        # Count feedback types
        for record in records:
            # Look for feedback columns (adjust column names as needed)
            feedback_value = None
            
            # Try different possible column names for feedback
            for key in record.keys():
                key_lower = key.lower()
                if any(word in key_lower for word in ['feedback', 'rating', 'thumbs', 'vote', 'helpful']):
                    feedback_value = str(record[key]).lower().strip()
                    break
            
            if feedback_value:
                if any(positive in feedback_value for positive in ['thumbs up', 'up', 'positive', 'yes', 'helpful', '👍', '1']):
                    thumbs_up += 1
                elif any(negative in feedback_value for negative in ['thumbs down', 'down', 'negative', 'no', 'not helpful', '👎', '0']):
                    thumbs_down += 1
        
        # Calculate percentages
        positive_percentage = (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0
        negative_percentage = (thumbs_down / total_feedback * 100) if total_feedback > 0 else 0
        
        analytics_data = {
            "summary": {
                "total_feedback": total_feedback,
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
                "positive_percentage": round(positive_percentage, 1),
                "negative_percentage": round(negative_percentage, 1),
                "unrated": total_feedback - thumbs_up - thumbs_down
            },
            "sheet_info": {
                "sheets_id": sheets_id,
                "worksheet_title": worksheet.title,
                "last_updated": worksheet.updated
            }
        }
        
        logger.info(f"Analytics data retrieved: {analytics_data['summary']}")
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error retrieving analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")

@router.get("/health")
async def admin_health(admin_auth: bool = Depends(get_admin_auth)) -> Dict[str, str]:
    """Health check for admin endpoints"""
    return {"status": "healthy", "message": "Admin API is operational"}

# Legacy endpoints for backward compatibility (deprecated)
@router.get("/analytics-legacy")
async def get_analytics_legacy(admin_auth: bool = Depends(get_admin_auth_query)) -> Dict[str, Any]:
    """
    Get analytics data using query parameter authentication (deprecated)
    Use /analytics with Authorization header instead
    """
    # Reuse the main analytics logic
    return await get_analytics(True)