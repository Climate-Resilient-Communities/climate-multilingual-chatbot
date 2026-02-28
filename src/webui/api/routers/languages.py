"""
Language support endpoints
Integrates with MultilingualRouter and provides language validation
"""

import time
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.models.query_routing import MultilingualRouter

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class LanguageInfo(BaseModel):
    code: str
    name: str

class SupportedLanguagesResponse(BaseModel):
    command_a_languages: List[LanguageInfo]
    nova_languages: List[LanguageInfo]
    default_language: str
    total_supported: int

class LanguageValidationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    detected_language: Optional[str] = Field(None, description="Pre-detected language code")

class LanguageValidationResponse(BaseModel):
    detected_language: str
    confidence: float
    recommended_model: str
    is_supported: bool
    request_id: str

# Import dependency
from ..main import get_router

@router.get("/languages/supported", response_model=SupportedLanguagesResponse)
async def get_supported_languages(
    lang_router: MultilingualRouter = Depends(get_router)
):
    """
    Get all supported languages with their routing information
    
    Returns languages supported by Command A and Nova models
    This serves as the single source of truth for language support
    """
    try:
        # Get Command A supported languages
        command_a_languages = []
        for lang_code in lang_router.COMMAND_A_SUPPORTED_LANGUAGES:
            # Get full language name from the mapping
            lang_name = lang_router.LANGUAGE_CODE_MAP.get(lang_code, lang_code.upper())
            command_a_languages.append(LanguageInfo(code=lang_code, name=lang_name))
        
        # For Nova model, we support a broader set of languages
        # These are languages not in Command A's supported set
        nova_languages = []
        
        # Add some common languages not in Command A
        additional_nova_languages = {
            'eo': 'Esperanto',
            'la': 'Latin', 
            'cy': 'Welsh',
            'ga': 'Irish',
            'mt': 'Maltese',
            'is': 'Icelandic',
            'fo': 'Faroese',
            'eu': 'Basque',
            'ca': 'Catalan',
            'gl': 'Galician'
        }
        
        for lang_code, lang_name in additional_nova_languages.items():
            nova_languages.append(LanguageInfo(code=lang_code, name=lang_name))
        
        total_supported = len(command_a_languages) + len(nova_languages)
        
        logger.info(f"Returning language support: command_a={len(command_a_languages)} nova={len(nova_languages)}")
        
        return SupportedLanguagesResponse(
            command_a_languages=command_a_languages,
            nova_languages=nova_languages,
            default_language="en",
            total_supported=total_supported
        )
        
    except Exception as e:
        logger.error(f"Failed to get supported languages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "LANGUAGE_SUPPORT_ERROR",
                    "type": "server_error",
                    "message": "Failed to retrieve language support information",
                    "retryable": True
                }
            }
        )

@router.post("/languages/validate", response_model=LanguageValidationResponse)
async def validate_language(
    request: LanguageValidationRequest,
    lang_router: MultilingualRouter = Depends(get_router)
):
    """
    Validate and detect language for a given query
    
    Returns detected language, confidence, and recommended model
    """
    try:
        request_id = f"lang_{int(time.time() * 1000)}"
        
        # Use the language router to detect language
        language_info = lang_router.detect_language(request.query)
        
        detected_language = request.detected_language or language_info.get('language_code', 'en')
        confidence = language_info.get('confidence', 0.8)  # Default confidence
        
        # Determine recommended model based on language support
        if detected_language in lang_router.COMMAND_A_SUPPORTED_LANGUAGES:
            recommended_model = "command_a"
            is_supported = True
        else:
            recommended_model = "nova"
            is_supported = True  # Nova supports broader language set
        
        logger.info(
            f"Language validation: query_len={len(request.query)} "
            f"detected={detected_language} model={recommended_model} confidence={confidence:.3f}"
        )
        
        return LanguageValidationResponse(
            detected_language=detected_language,
            confidence=confidence,
            recommended_model=recommended_model,
            is_supported=is_supported,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Language validation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "LANGUAGE_VALIDATION_ERROR",
                    "type": "server_error",
                    "message": f"Failed to validate language: {str(e)}",
                    "retryable": True
                }
            }
        )

@router.get("/languages/test")
async def test_languages_endpoint():
    """Test endpoint to verify languages router is working"""
    return {
        "status": "Languages router is working",
        "timestamp": time.time(),
        "endpoints": [
            "GET /api/v1/languages/supported - Get all supported languages",
            "POST /api/v1/languages/validate - Validate language for query"
        ]
    }