"""
Input validation and sanitization module
"""
import re
import html
from typing import Optional, Dict, Any
import logging
from src.utils.error_handler import ValidationError
from src.data.config.constants import ERROR_CODES, LanguageCode
from src.utils.metrics import track_metrics

logger = logging.getLogger(__name__)

class InputValidator:
    # Maximum query length to prevent abuse
    MAX_QUERY_LENGTH = 1000
    
    # Regex patterns for validation
    PATTERNS = {
        'html_tags': re.compile(r'<[^>]+>'),
        'sql_injection': re.compile(r'(?i)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|WHERE)\s+'),
        'script_tags': re.compile(r'(?i)<script[^>]*>.*?</script>'),
        'unsafe_chars': re.compile(r'[^\w\s.,!?-]')
    }
    
    @classmethod
    @track_metrics("input_validation")
    def validate_query(cls, query: str) -> str:
        """Validate and sanitize user query"""
        if not query or not query.strip():
            raise ValidationError(
                message="Query cannot be empty",
                error_code=ERROR_CODES["VALIDATION_ERROR"]
            )
            
        if len(query) > cls.MAX_QUERY_LENGTH:
            raise ValidationError(
                message=f"Query exceeds maximum length of {cls.MAX_QUERY_LENGTH} characters",
                error_code=ERROR_CODES["VALIDATION_ERROR"]
            )
            
        # Basic sanitization
        sanitized = cls._sanitize_input(query)
        
        # Check for potential malicious patterns
        if cls._contains_malicious_patterns(sanitized):
            raise ValidationError(
                message="Query contains potentially unsafe patterns",
                error_code=ERROR_CODES["VALIDATION_ERROR"]
            )
            
        return sanitized
    
    @classmethod
    @track_metrics("language_validation")    
    def validate_language(cls, language: str) -> Optional[str]:
        """Validate language code/name"""
        try:
            # Normalize language input
            language = language.lower().strip()
            
            # Check if it's a valid language code or name
            for lang_code in LanguageCode:
                if language == lang_code.value or language == lang_code.name.lower():
                    return lang_code.value
                    
            raise ValidationError(
                message=f"Unsupported language: {language}",
                error_code=ERROR_CODES["VALIDATION_ERROR"]
            )
            
        except Exception as e:
            logger.error(f"Language validation error: {str(e)}")
            raise ValidationError(
                message="Invalid language format",
                error_code=ERROR_CODES["VALIDATION_ERROR"]
            )
    
    @classmethod
    def _sanitize_input(cls, text: str) -> str:
        """Sanitize input text"""
        # HTML escape to prevent XSS
        text = html.escape(text)
        
        # Remove HTML tags
        text = cls.PATTERNS['html_tags'].sub('', text)
        
        # Remove script tags
        text = cls.PATTERNS['script_tags'].sub('', text)
        
        # Remove potentially unsafe characters
        text = cls.PATTERNS['unsafe_chars'].sub('', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    @classmethod
    def _contains_malicious_patterns(cls, text: str) -> bool:
        """Check for potentially malicious patterns"""
        # Check for SQL injection patterns
        if cls.PATTERNS['sql_injection'].search(text):
            return True
            
        # Add more pattern checks as needed
        return False
    
    @classmethod
    @track_metrics("request_validation")
    def validate_request(cls, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete request payload"""
        validated = {}
        
        try:
            # Validate query if present
            if 'query' in request:
                validated['query'] = cls.validate_query(request['query'])
                
            # Validate language if present
            if 'language' in request:
                validated['language'] = cls.validate_language(request['language'])
                
            # Add more validation as needed for other fields
            
            return validated
            
        except ValidationError as e:
            logger.error(f"Request validation error: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected validation error: {str(e)}")
            raise ValidationError(
                message="Invalid request format",
                error_code=ERROR_CODES["VALIDATION_ERROR"]
            )