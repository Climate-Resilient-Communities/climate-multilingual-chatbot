"""
Enhanced feedback system
Integrates with Redis cache and Google Sheets for storing granular feedback data
"""

import time
import logging
import os
import json
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, validator

from src.models.redis_cache import ClimateCache

# Google Sheets imports
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

router = APIRouter()

# Feedback categories matching frontend implementation
THUMBS_UP_CATEGORIES = [
    "instructions",     # Followed Instructions
    "comprehensive",    # Comprehensive Answer
    "translation",      # Good Translation
    "expected",         # Response works as expected
    "other"            # Other
]

THUMBS_DOWN_CATEGORIES = [
    "instructions",     # Didn't follow instructions
    "no-response",      # No Response Generated
    "unrelated",        # Response Unrelated
    "translation",      # Bad Translation
    "guard-filter",     # Guard Filter Misclassified
    "other"            # Other
]

# Google Sheets helper functions
def get_google_sheets_client():
    """Initialize Google Sheets client using service account credentials"""
    try:
        logger.info(f"🟡 SHEETS AUTH: Starting Google Sheets client initialization")
        
        # Try to get credentials from environment variable (JSON string)
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        logger.info(f"🟡 SHEETS AUTH: creds_json exists: {bool(creds_json)}")
        
        if creds_json:
            logger.info(f"🟡 SHEETS AUTH: Using JSON credentials from environment variable")
            creds_info = json.loads(creds_json)
            credentials = Credentials.from_service_account_info(
                creds_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            # Fallback to service account file
            creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
            logger.info(f"🟡 SHEETS AUTH: creds_file path: {creds_file}")
            logger.info(f"🟡 SHEETS AUTH: creds_file exists: {os.path.exists(creds_file)}")
            
            if not os.path.exists(creds_file):
                logger.warning(f"❌ SHEETS AUTH: Google service account file not found: {creds_file}")
                return None
            
            logger.info(f"🟡 SHEETS AUTH: Using credentials file: {creds_file}")
            credentials = Credentials.from_service_account_file(
                creds_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        
        logger.info(f"✅ SHEETS AUTH: Successfully created credentials")
        
        client = gspread.authorize(credentials)
        logger.info(f"✅ SHEETS AUTH: Successfully authorized gspread client")
        
        return client
        
    except Exception as e:
        logger.error(f"❌ SHEETS AUTH: Failed to initialize Google Sheets client: {e}")
        logger.error(f"❌ SHEETS AUTH ERROR TYPE: {type(e).__name__}")
        import traceback
        logger.error(f"❌ SHEETS AUTH TRACEBACK: {traceback.format_exc()}")
        return None

async def append_to_google_sheets(feedback_data: dict):
    """Append feedback data to Google Sheets"""
    try:
        logger.info(f"🟡 SHEETS START: Attempting to append feedback to Google Sheets")
        logger.info(f"🟡 SHEETS DATA: {feedback_data}")
        
        sheets_id = os.getenv("GOOGLE_SHEETS_ID")
        if not sheets_id:
            logger.warning("❌ SHEETS CONFIG: GOOGLE_SHEETS_ID not configured, skipping Sheets storage")
            return False
        
        logger.info(f"🟡 SHEETS CONFIG: Using sheet ID: {sheets_id}")
        
        # Initialize Google Sheets client
        gc = get_google_sheets_client()
        if not gc:
            logger.warning("❌ SHEETS CLIENT: Google Sheets client not available, skipping Sheets storage")
            return False
        
        logger.info(f"✅ SHEETS CLIENT: Successfully created Google Sheets client")
        
        sheet = gc.open_by_key(sheets_id)
        logger.info(f"✅ SHEETS OPEN: Successfully opened sheet: {sheet.title}")
        
        worksheet = sheet.get_worksheet(0)  # Use first worksheet
        logger.info(f"✅ SHEETS WORKSHEET: Successfully accessed worksheet: {worksheet.title}")
        
        # Prepare row data to append - Map to Google Form columns properly
        row_data = [
            feedback_data.get('timestamp', datetime.now().isoformat()),  # Timestamp
            f"👍 Thumbs Up" if feedback_data.get('feedback_type') == 'thumbs_up' else f"👎 Thumbs Down",  # What type of feedback are you sharing?
            feedback_data.get('language_code', 'en'),  # Which language(s) were you using?
            feedback_data.get('comment', '') or f"Automated feedback from message {feedback_data.get('message_id', '')}",  # Briefly describe your feedback
            f"Feedback ID: {feedback_data.get('feedback_id', '')} | Categories: {', '.join(feedback_data.get('categories', []))}",  # If this is a bug...
            f"Message ID: {feedback_data.get('message_id', '')}",  # Conversation history
            "Via Chatbot Interface"  # How often do you use the climate chatbot?
        ]
        
        logger.info(f"🟡 SHEETS ROW: Preparing to append row: {row_data}")
        
        # Append the row to the sheet
        worksheet.append_row(row_data)
        logger.info(f"✅ SHEETS SUCCESS: Successfully appended feedback {feedback_data.get('feedback_id')} to Google Sheets")
        return True
        
    except Exception as e:
        logger.error(f"❌ SHEETS ERROR: Failed to append feedback to Google Sheets: {e}")
        logger.error(f"❌ SHEETS ERROR TYPE: {type(e).__name__}")
        import traceback
        logger.error(f"❌ SHEETS ERROR TRACEBACK: {traceback.format_exc()}")
        return False

# Pydantic models
class FeedbackRequest(BaseModel):
    message_id: str = Field(..., min_length=1, description="ID of the message being rated")
    feedback_type: str = Field(..., pattern="^(thumbs_up|thumbs_down)$")
    categories: List[str] = Field(default=[], max_items=5, description="Feedback categories")
    comment: Optional[str] = Field(None, max_length=500, description="Optional comment")
    language_code: str = Field(default="en", description="Language of the interaction")

    @validator('categories')
    def validate_categories(cls, v, values):
        if not v:
            return v
            
        feedback_type = values.get('feedback_type')
        if feedback_type == 'thumbs_up':
            valid_categories = THUMBS_UP_CATEGORIES
        elif feedback_type == 'thumbs_down':
            valid_categories = THUMBS_DOWN_CATEGORIES
        else:
            raise ValueError('Invalid feedback_type')
        
        invalid_categories = [cat for cat in v if cat not in valid_categories]
        if invalid_categories:
            raise ValueError(f'Invalid categories for {feedback_type}: {invalid_categories}')
        
        return v

    @validator('comment')
    def validate_comment(cls, v):
        if v is not None:
            # Basic PII detection (extend as needed)
            v = v.strip()
            if not v:
                return None
            
            # Simple check for potential PII patterns
            pii_patterns = ['@', 'phone', 'email', 'address', 'ssn']
            lower_comment = v.lower()
            
            for pattern in pii_patterns:
                if pattern in lower_comment:
                    logger.warning(f"Potential PII detected in feedback comment")
                    # For now, just log warning - could implement redaction here
                    break
                    
        return v

class FeedbackResponse(BaseModel):
    success: bool
    feedback_id: str
    pii_detected: bool = False
    request_id: str

class FeedbackData(BaseModel):
    """Internal model for storing feedback in Redis"""
    feedback_id: str
    message_id: str
    session_id: Optional[str] = None
    feedback_type: str
    categories: List[str]
    comment: Optional[str] = None
    timestamp: datetime
    language_code: str
    query_hash: Optional[str] = None
    model_used: Optional[str] = None
    processing_time: Optional[float] = None

# Import dependency
from ..main import get_cache

@router.post("/feedback/submit", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    http_request: Request,
    cache: ClimateCache = Depends(get_cache)
):
    """
    Submit enhanced feedback with granular categories
    
    Stores detailed feedback data in Redis for analytics
    """
    try:
        request_id = getattr(http_request.state, 'request_id', str(uuid4()))
        feedback_id = f"fb_{uuid4().hex[:12]}"
        
        logger.info(
            f"Submitting feedback: id={feedback_id} type={request.feedback_type} "
            f"categories={len(request.categories)} message_id={request.message_id}"
        )
        
        # Create feedback data structure
        feedback_data = FeedbackData(
            feedback_id=feedback_id,
            message_id=request.message_id,
            feedback_type=request.feedback_type,
            categories=request.categories,
            comment=request.comment,
            timestamp=datetime.now(),
            language_code=request.language_code
        )
        
        # Store in Redis cache
        try:
            # Use a simple key structure for now
            feedback_key = f"feedback:{feedback_id}"
            feedback_dict = feedback_data.dict()
            feedback_dict['timestamp'] = feedback_dict['timestamp'].isoformat()
            
            logger.info(f"🔵 FEEDBACK SUBMISSION - Starting Redis storage for feedback_id: {feedback_id}")
            logger.info(f"🔵 FEEDBACK DATA: {feedback_dict}")
            
            # Store feedback data
            await cache.store_feedback(feedback_key, feedback_dict)
            
            # Also store in a list for analytics (message_id -> feedback_ids)
            message_feedback_key = f"message_feedback:{request.message_id}"
            await cache.add_to_list(message_feedback_key, feedback_id)
            
            logger.info(f"✅ REDIS SUCCESS: Feedback stored successfully in Redis: id={feedback_id}")
            
        except Exception as e:
            logger.error(f"❌ REDIS ERROR: Failed to store feedback in cache: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "FEEDBACK_STORAGE_ERROR",
                        "type": "server_error",
                        "message": "Failed to store feedback",
                        "retryable": True,
                        "request_id": request_id
                    }
                }
            )
        
        # Also store in Google Sheets for persistent analytics (non-blocking)
        try:
            logger.info(f"🟡 GOOGLE SHEETS - Starting Google Sheets storage for feedback_id: {feedback_id}")
            feedback_dict_for_sheets = feedback_data.dict()
            feedback_dict_for_sheets['timestamp'] = feedback_dict_for_sheets['timestamp'].isoformat()
            
            sheets_result = await append_to_google_sheets(feedback_dict_for_sheets)
            if sheets_result:
                logger.info(f"✅ GOOGLE SHEETS SUCCESS: Feedback stored in Google Sheets: id={feedback_id}")
            else:
                logger.warning(f"⚠️ GOOGLE SHEETS WARNING: Failed to store in Google Sheets but continuing: id={feedback_id}")
                
        except Exception as e:
            # Don't fail the request if Google Sheets fails - just log it
            logger.error(f"❌ GOOGLE SHEETS ERROR: Failed to store feedback in Google Sheets (non-blocking): {str(e)}")
            logger.error(f"❌ GOOGLE SHEETS ERROR DETAILS: feedback_id={feedback_id}, error_type={type(e).__name__}")
        
        logger.info(f"🎉 FEEDBACK COMPLETE: Successfully processed feedback submission: id={feedback_id}")
        
        return FeedbackResponse(
            success=True,
            feedback_id=feedback_id,
            pii_detected=False,  # Could implement PII detection logic here
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in feedback submission: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "FEEDBACK_SUBMISSION_ERROR", 
                    "type": "server_error",
                    "message": f"Failed to submit feedback: {str(e)}",
                    "retryable": True
                }
            }
        )

@router.get("/feedback/categories")
async def get_feedback_categories():
    """Get available feedback categories for each type"""
    return {
        "thumbs_up": THUMBS_UP_CATEGORIES,
        "thumbs_down": THUMBS_DOWN_CATEGORIES,
        "description": {
            "thumbs_up": {
                "instructions": "Followed Instructions", 
                "comprehensive": "Comprehensive Answer",
                "translation": "Good Translation",
                "expected": "Response works as expected",
                "other": "Other"
            },
            "thumbs_down": {
                "instructions": "Didn't follow instructions",
                "no-response": "No Response Generated", 
                "unrelated": "Response Unrelated",
                "translation": "Bad Translation",
                "guard-filter": "Guard Filter Misclassified",
                "other": "Other"
            }
        }
    }

@router.get("/feedback/test")
async def test_feedback_endpoint():
    """Test endpoint to verify feedback router is working"""
    return {
        "status": "Feedback router is working",
        "timestamp": time.time(),
        "endpoints": [
            "POST /api/v1/feedback/submit - Submit feedback",
            "GET /api/v1/feedback/categories - Get feedback categories"
        ]
    }