"""
Enhanced feedback system
Integrates with Redis cache for storing granular feedback data
"""

import time
import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, validator

from src.models.redis_cache import ClimateCache

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
            
            logger.info(f"Feedback stored successfully: id={feedback_id}")
            
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