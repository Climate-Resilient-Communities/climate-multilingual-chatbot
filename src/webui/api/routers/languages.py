"""
Language support endpoints
Integrates with MultilingualRouter and provides language validation
"""

import time
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.models.query_routing import MultilingualRouter, LanguageSupport
from src.models.cohere_flow import FIRE_LANGUAGES, EARTH_LANGUAGES, WATER_LANGUAGES

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class LanguageInfo(BaseModel):
    code: str
    name: str

class SupportedLanguagesResponse(BaseModel):
    tiny_aya_fire_languages: List[LanguageInfo]
    tiny_aya_earth_languages: List[LanguageInfo]
    tiny_aya_water_languages: List[LanguageInfo]
    tiny_aya_global_note: str
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

    Returns languages supported by Tiny-Aya regional models (fire, earth, water, global)
    """
    try:
        name_map = lang_router.LANGUAGE_NAME_MAP

        fire_languages = [
            LanguageInfo(code=lc, name=name_map.get(lc, lc.upper()))
            for lc in sorted(FIRE_LANGUAGES)
        ]
        earth_languages = [
            LanguageInfo(code=lc, name=name_map.get(lc, lc.upper()))
            for lc in sorted(EARTH_LANGUAGES)
        ]
        water_languages = [
            LanguageInfo(code=lc, name=name_map.get(lc, lc.upper()))
            for lc in sorted(WATER_LANGUAGES)
        ]

        total_supported = len(FIRE_LANGUAGES) + len(EARTH_LANGUAGES) + len(WATER_LANGUAGES)

        logger.info(
            f"Returning language support: fire={len(fire_languages)} "
            f"earth={len(earth_languages)} water={len(water_languages)}"
        )

        return SupportedLanguagesResponse(
            tiny_aya_fire_languages=fire_languages,
            tiny_aya_earth_languages=earth_languages,
            tiny_aya_water_languages=water_languages,
            tiny_aya_global_note="English and all other languages not listed above",
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
        confidence = language_info.get('confidence', 0.8)

        # Determine recommended model based on Tiny-Aya routing
        support_level = lang_router.check_language_support(detected_language)
        recommended_model = support_level.value
        is_supported = True  # All languages are supported via regional routing

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
