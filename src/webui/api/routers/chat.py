"""
Chat endpoints with full pipeline integration
Integrates all existing components: climate_pipeline, conversation_parser, query_routing
"""

import time
import logging
import asyncio
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, validator

# Import existing pipeline components
from src.models.climate_pipeline import ClimateQueryPipeline
from src.models.conversation_parser import ConversationParser
from src.models.query_routing import MultilingualRouter
from src.models.redis_cache import ClimateCache

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    language: Optional[str] = Field(None, description="Language code (ISO 639-1)")
    conversation_history: Optional[List[ConversationMessage]] = Field(
        default=[], description="Previous conversation messages"
    )
    stream: bool = Field(default=False, description="Enable streaming response")

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()

class CitationDict(BaseModel):
    title: str
    url: str
    content: str = ""
    snippet: str = ""

class ChatResponse(BaseModel):
    success: bool
    response: str
    citations: List[CitationDict] = []
    faithfulness_score: float = 0.0
    processing_time: float = 0.0
    language_used: str = "en"
    model_used: Optional[str] = None
    request_id: str

class ErrorResponse(BaseModel):
    error: Dict[str, Any]

# Import dependencies from main
from ..main import get_pipeline, get_conversation_parser, get_router, get_cache

@router.post("/chat/query", response_model=ChatResponse)
async def process_chat_query(
    request: ChatRequest,
    http_request: Request,
    pipeline: ClimateQueryPipeline = Depends(get_pipeline),
    conv_parser: ConversationParser = Depends(get_conversation_parser),
    lang_router: MultilingualRouter = Depends(get_router),
    cache: ClimateCache = Depends(get_cache)
):
    """
    Process a chat query through the complete pipeline
    
    Integrates:
    - ConversationParser for history standardization
    - MultilingualRouter for language detection and model selection
    - ClimateQueryPipeline for main processing
    - Redis cache for session management
    """
    start_time = time.time()
    request_id = getattr(http_request.state, 'request_id', str(uuid4()))
    
    try:
        logger.info(f"Processing chat query: id={request_id} query_len={len(request.query)} lang={request.language}")
        
        # Step 1: Parse conversation history
        standardized_history = []
        if request.conversation_history:
            try:
                # Convert Pydantic models to dict format expected by ConversationParser
                history_dicts = [msg.dict() for msg in request.conversation_history]
                standardized_history = conv_parser.parse_conversation_history(history_dicts)
                logger.info(f"Parsed conversation history: {len(standardized_history)} messages")
            except Exception as e:
                logger.warning(f"Failed to parse conversation history: {str(e)}")
                standardized_history = []
        
        # Step 2: Language detection and routing
        detected_language = request.language or "en"
        model_used = "unknown"
        
        try:
            # Priority: User dropdown selection > Auto-detection > Default to English
            if request.language:
                # User explicitly selected a language from dropdown - always use it
                detected_language = request.language
            else:
                # No language selected - use auto-detection as fallback
                language_info = lang_router.detect_language(request.query)
                detected_language = language_info.get('language_code', detected_language)
            
            # Determine which model to use based on language support
            if detected_language in lang_router.COMMAND_A_SUPPORTED_LANGUAGES:
                model_used = "command_a"
            else:
                model_used = "nova"
                
            logger.info(f"Language routing: detected={detected_language} model={model_used}")
            
        except Exception as e:
            logger.warning(f"Language routing failed, using defaults: {str(e)}")
            detected_language = request.language or "en"
            model_used = "command_a"  # Default fallback
        
        # Step 3: Process through main pipeline
        try:
            # Use router's language name mapping for pipeline processing
            language_name = lang_router.LANGUAGE_NAME_MAP.get(detected_language, 'english')
            if not language_name:
                language_name = 'english'  # Fallback
            
            # Process through ClimateQueryPipeline with timeout
            try:
                result = await asyncio.wait_for(
                    pipeline.process_query(
                        query=request.query,
                        language_name=language_name,
                        conversation_history=standardized_history
                    ),
                    timeout=60.0  # 60 second timeout to prevent hangs
                )
            except asyncio.TimeoutError:
                logger.error(f"Pipeline processing timeout: id={request_id}")
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": {
                            "code": "PROCESSING_TIMEOUT",
                            "type": "timeout_error",
                            "message": "Request timed out after 60 seconds",
                            "retryable": True,
                            "request_id": request_id
                        }
                    }
                )
            
            processing_time = time.time() - start_time
            
            # Handle pipeline result
            if result.get('success', False):
                # Keep citations in original dictionary format for better frontend handling
                citations = result.get('citations', [])
                if citations and isinstance(citations[0], dict):
                    # Ensure all required fields are present for each citation
                    citations = [
                        CitationDict(
                            title=cite.get('title', 'Untitled Source'),
                            url=cite.get('url', ''),
                            content=cite.get('content', ''),
                            snippet=cite.get('snippet', '')
                        ) for cite in citations
                    ]
                else:
                    citations = []
                
                response = ChatResponse(
                    success=True,
                    response=result.get('response', ''),
                    citations=citations,
                    faithfulness_score=result.get('faithfulness_score', 0.0),
                    processing_time=processing_time,
                    language_used=detected_language,
                    model_used=model_used,
                    request_id=request_id
                )
                
                logger.info(
                    f"Query processed successfully: id={request_id} "
                    f"time={processing_time:.3f}s model={model_used} "
                    f"faithfulness={result.get('faithfulness_score', 0.0):.3f}"
                )
                
                return response
            else:
                # Pipeline returned error
                error_msg = result.get('message', 'Pipeline processing failed')
                logger.error(f"Pipeline error: id={request_id} error={error_msg}")
                
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": {
                            "code": "PIPELINE_ERROR",
                            "type": "processing_error",
                            "message": error_msg,
                            "retryable": True,
                            "request_id": request_id
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"Pipeline processing failed: id={request_id} error={str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "PIPELINE_PROCESSING_ERROR",
                        "type": "server_error", 
                        "message": f"Failed to process query: {str(e)}",
                        "retryable": True,
                        "request_id": request_id
                    }
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any other unexpected errors
        processing_time = time.time() - start_time
        logger.error(f"Unexpected error in chat query: id={request_id} error={str(e)} time={processing_time:.3f}s")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "type": "server_error",
                    "message": "An unexpected error occurred",
                    "retryable": True,
                    "request_id": request_id
                }
            }
        )

@router.get("/chat/test")
async def test_chat_endpoint():
    """Test endpoint to verify chat router is working"""
    return {
        "status": "Chat router is working",
        "timestamp": time.time(),
        "endpoints": [
            "POST /api/v1/chat/query - Main chat processing"
        ]
    }