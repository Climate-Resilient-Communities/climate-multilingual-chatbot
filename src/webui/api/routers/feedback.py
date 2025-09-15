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
        # Try to get credentials from environment variable (JSON string)
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if creds_json:
            creds_info = json.loads(creds_json)
            credentials = Credentials.from_service_account_info(
                creds_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            # Fallback to service account file
            creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
            if not os.path.exists(creds_file):
                logger.warning(f"Google service account file not found: {creds_file}")
                return None
            
            credentials = Credentials.from_service_account_file(
                creds_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        
        return gspread.authorize(credentials)
    except Exception as e:
        logger.warning(f"Failed to initialize Google Sheets client: {e}")
        return None

async def append_to_google_sheets(feedback_data: dict):
    """Append feedback data to Google Sheets"""
    try:
        sheets_id = os.getenv("GOOGLE_SHEETS_ID")
        if not sheets_id:
            logger.warning("GOOGLE_SHEETS_ID not configured, skipping Sheets storage")
            return False
        
        # Initialize Google Sheets client
        gc = get_google_sheets_client()
        if not gc:
            logger.warning("Google Sheets client not available, skipping Sheets storage")
            return False
        
        sheet = gc.open_by_key(sheets_id)
        worksheet = sheet.get_worksheet(0)  # Use first worksheet
        
        # Prepare row data to append
        row_data = [
            feedback_data.get('timestamp', datetime.now().isoformat()),
            feedback_data.get('feedback_id', ''),
            feedback_data.get('message_id', ''),
            feedback_data.get('feedback_type', ''),
            ', '.join(feedback_data.get('categories', [])),  # Join categories with commas
            feedback_data.get('comment', '') or '',
            feedback_data.get('language_code', 'en')
        ]
        
        # Append the row to the sheet
        worksheet.append_row(row_data)
        logger.info(f"Successfully appended feedback {feedback_data.get('feedback_id')} to Google Sheets")
        return True
        
    except Exception as e:
        logger.error(f"Failed to append feedback to Google Sheets: {e}")
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
            
            # Store feedback data
            await cache.store_feedback(feedback_key, feedback_dict)
            
            # Also store in a list for analytics (message_id -> feedback_ids)
            message_feedback_key = f"message_feedback:{request.message_id}"
            await cache.add_to_list(message_feedback_key, feedback_id)
            
            logger.info(f"Feedback stored successfully in Redis: id={feedback_id}")
            
        except Exception as e:
            logger.error(f"Failed to store feedback in cache: {str(e)}")
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
            feedback_dict_for_sheets = feedback_data.dict()
            feedback_dict_for_sheets['timestamp'] = feedback_dict_for_sheets['timestamp'].isoformat()
            await append_to_google_sheets(feedback_dict_for_sheets)
        except Exception as e:
            # Don't fail the request if Google Sheets fails - just log it
            logger.warning(f"Failed to store feedback in Google Sheets (non-blocking): {str(e)}")
        
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