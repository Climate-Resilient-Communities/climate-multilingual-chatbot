"""
Server-Sent Events (SSE) streaming endpoint for real-time chat responses
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.models.climate_pipeline import ClimateQueryPipeline
from src.models.conversation_parser import ConversationParser
from src.models.query_routing import MultilingualRouter

logger = logging.getLogger(__name__)

router = APIRouter()

class StreamChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en")
    conversation_history: list = Field(default=[])

# Import dependencies
from ..main import get_pipeline, get_conversation_parser, get_router

async def generate_chat_stream(
    request: StreamChatRequest,
    request_id: str,
    pipeline: ClimateQueryPipeline,
    conv_parser: ConversationParser,
    lang_router: MultilingualRouter
):
    """Generate SSE stream for chat response"""
    
    try:
        # Send initial progress
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'initializing', 'request_id': request_id})}\n\n"
        
        # Parse conversation history
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'parsing_history', 'request_id': request_id})}\n\n"
        
        standardized_history = []
        if request.conversation_history:
            try:
                standardized_history = conv_parser.parse_conversation_history(request.conversation_history)
            except Exception as e:
                logger.warning(f"Failed to parse conversation history: {str(e)}")
        
        # Language detection
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'detecting_language', 'request_id': request_id})}\n\n"
        
        detected_language = request.language
        model_used = "command_a"
        
        try:
            language_info = lang_router.detect_language(request.query)
            detected_language = language_info.get('language_code', detected_language)
            
            if detected_language in lang_router.COMMAND_A_SUPPORTED_LANGUAGES:
                model_used = "command_a"
            else:
                model_used = "nova"
                
        except Exception as e:
            logger.warning(f"Language routing failed: {str(e)}")
        
        # Send language info
        yield f"data: {json.dumps({'type': 'language_detected', 'language': detected_language, 'model': model_used, 'request_id': request_id})}\n\n"
        
        # Processing stages
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'retrieving_documents', 'request_id': request_id})}\n\n"
        await asyncio.sleep(0.5)  # Simulate processing time
        
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'reranking_results', 'request_id': request_id})}\n\n"
        await asyncio.sleep(0.3)
        
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'generating_response', 'request_id': request_id})}\n\n"
        
        # Get language name for pipeline
        language_name = lang_router.LANGUAGE_CODE_MAP.get(detected_language, 'english')
        
        # Process through pipeline with timeout
        try:
            result = await asyncio.wait_for(
                pipeline.process_query(
                    query=request.query,
                    language_name=language_name,
                    conversation_history=standardized_history
                ),
                timeout=60.0
            )
            
            if result.get('success', False):
                response_text = result.get('response', '')
                citations = result.get('citations', [])
                faithfulness_score = result.get('faithfulness_score', 0.0)
                
                # Stream response token by token (simulate)
                words = response_text.split()
                partial_response = ""
                
                for i, word in enumerate(words):
                    partial_response += word + " "
                    
                    yield f"data: {json.dumps({'type': 'token', 'content': word + ' ', 'partial_response': partial_response.strip(), 'request_id': request_id})}\n\n"
                    
                    # Small delay to simulate streaming without slowing too much
                    if i % 8 == 0:
                        await asyncio.sleep(0.02)
                
                # Send citations
                for citation in citations:
                    yield f"data: {json.dumps({'type': 'citation', 'citation': citation, 'request_id': request_id})}\n\n"
                
                # Send completion
                yield f"data: {json.dumps({'type': 'complete', 'final_response': response_text, 'citations': citations, 'faithfulness_score': faithfulness_score, 'model_used': model_used, 'language_used': detected_language, 'request_id': request_id})}\n\n"
                
            else:
                # Pipeline error
                error_msg = result.get('message', 'Processing failed')
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg, 'request_id': request_id})}\n\n"
                
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Request timed out after 60 seconds', 'request_id': request_id})}\n\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'error': f'Streaming failed: {str(e)}', 'request_id': request_id})}\n\n"
    
    finally:
        # Send end of stream
        yield f"data: {json.dumps({'type': 'end', 'request_id': request_id})}\n\n"

@router.post("/chat/stream")
async def stream_chat_response(
    request: StreamChatRequest,
    http_request: Request,
    pipeline: ClimateQueryPipeline = Depends(get_pipeline),
    conv_parser: ConversationParser = Depends(get_conversation_parser),
    lang_router: MultilingualRouter = Depends(get_router)
):
    """
    Stream chat response using Server-Sent Events (SSE)
    
    Returns real-time progress updates and token-by-token response
    """
    request_id = getattr(http_request.state, 'request_id', str(uuid4()))
    
    logger.info(f"Starting SSE stream: id={request_id} query_len={len(request.query)}")
    
    return StreamingResponse(
        generate_chat_stream(request, request_id, pipeline, conv_parser, lang_router),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id
        }
    )

@router.get("/chat/stream/test")
async def test_streaming():
    """Test endpoint for SSE streaming"""
    return {
        "status": "SSE streaming available",
        "endpoints": [
            "POST /api/v1/chat/stream - Stream chat responses with SSE"
        ],
        "usage": "Use EventSource in frontend to connect to /api/v1/chat/stream"
    }