import os
import logging
from enum import Enum
from typing import Dict, Any
from src.utils.env_loader import load_environment
from src.models.nova_flow import BedrockModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LanguageSupport(Enum):
    """Enum for language support levels"""
    COMMAND_R_PLUS = "command_r_plus"  # Full support
    COMMAND_R = "command_r"            # Basic support
    ALPHA = "alpha"                    # Experimental support
    UNSUPPORTED = "unsupported"        # No support

class MultilingualRouter:
    """Handles language routing for queries."""
    
    COMMAND_R_PLUS_SUPPORTED_LANGUAGES = {
        'en', 'fr', 'es', 'it', 'de', 'pt', 'ja', 'ko', 'zh', 'ar',
        'ru', 'pl', 'tr', 'vi', 'nl', 'cs', 'id', 'uk', 'ro', 'el', 'hi', 'he', 'fa'
    }
    
    LANGUAGE_CODE_MAP = {
        'zh-cn': 'zh', 'zh-tw': 'zh', 'pt-br': 'pt', 'pt-pt': 'pt',
        'en-us': 'en', 'en-gb': 'en', 'fr-ca': 'fr', 'fr-fr': 'fr',
        'es-es': 'es', 'es-mx': 'es', 'es-ar': 'es', 'de-de': 'de',
        'de-at': 'de', 'de-ch': 'de', 'nl-nl': 'nl', 'nl-be': 'nl',
        'it-it': 'it', 'it-ch': 'it', 'sv-se': 'sv', 'sv-fi': 'sv',
        'no-no': 'no', 'da-dk': 'da', 'fi-fi': 'fi', 'he-il': 'he',
        'ar-sa': 'ar', 'ar-eg': 'ar', 'ru-ru': 'ru', 'pl-pl': 'pl',
        'ja-jp': 'ja', 'ko-kr': 'ko', 'vi-vn': 'vi', 'id-id': 'id',
        'ms-my': 'ms', 'th-th': 'th', 'tr-tr': 'tr', 'uk-ua': 'uk',
        'bg-bg': 'bg', 'cs-cz': 'cs', 'hu-hu': 'hu', 'ro-ro': 'ro',
        'sk-sk': 'sk', 'sl-si': 'sl'
    }

    def __init__(self):
        """Initialize language routing"""
        # No special initialization needed currently
        pass

    def standardize_language_code(self, language_code: str) -> str:
        """Standardize language codes to match our supported formats."""
        return self.LANGUAGE_CODE_MAP.get(language_code.lower(), language_code.lower())

    def check_language_support(self, language_code: str) -> LanguageSupport:
        """Check the level of language support using standardized language codes."""
        if language_code in self.COMMAND_R_PLUS_SUPPORTED_LANGUAGES:
            return LanguageSupport.COMMAND_R_PLUS
        else: 
            return LanguageSupport.NOVA

    def _get_unsupported_language_message(self, language_name: str, language_code: str) -> str:
        """Private helper to generate unsupported language messages."""
        return f"We currently don't support {language_name} ({language_code}). Please try another language."
        
    async def route_query(
        self,
        query: str,
        language_code: str,
        language_name: str,
        translation: Any
    ) -> Dict[str, Any]:
        """Route and process query based on language."""
        try:
            # Process routing info
            routing_info = {
                'support_level': 'command_r_plus',
                'needs_translation': language_code != 'en',
                'message': None
            }
            
            # Set query processing parameters
            english_query = query
            processed_query = query
            
            # Handle non-English queries
            if routing_info['needs_translation']:
                try:
                    # Translate to English
                    english_query = await translation(query, language_name, 'english')
                    processed_query = english_query
                except Exception as e:
                    logger.error(f"Translation error: {str(e)}")
                    routing_info['message'] = f"Translation failed: {str(e)}"
                    return {
                        'should_proceed': False,
                        'routing_info': routing_info,
                        'processed_query': query,
                        'english_query': query
                    }

            return {
                'should_proceed': True,
                'routing_info': routing_info,
                'processed_query': processed_query,
                'english_query': english_query
            }

        except Exception as e:
            logger.error(f"Error in query routing: {str(e)}")
            return {
                'should_proceed': False,
                'routing_info': {
                    'support_level': 'unsupported',
                    'needs_translation': False,
                    'message': f"Routing error: {str(e)}"
                },
                'processed_query': query,
                'english_query': query
            }

def test_routing():
    """Test the query routing functionality"""
    try:
        # Initialize components
        print("\n=== Testing Query Routing ===")
        load_environment()
        
        # Initialize router and translation
        router = MultilingualRouter()
        nova_model = BedrockModel()
        
        # Test cases
        test_cases = [
            {
                'query': 'What is climate change?',
                'language_code': 'en',
                'language_name': 'english'
            },
            {
                'query': '¿Qué es el cambio climático?',
                'language_code': 'es',
                'language_name': 'spanish'
            },
            {
                'query': '気候変動とは何ですか？',
                'language_code': 'ja',
                'language_name': 'japanese'
            },
            {
                'query': '',  # Empty query test
                'language_code': 'en',
                'language_name': 'english'
            }
        ]
        
        # Run tests
        for case in test_cases:
            print(f"\nTesting: {case['query']}")
            print(f"Language: {case['language_name']}")
            
            result = router.route_query(
                query=case['query'],
                language_code=case['language_code'],
                language_name=case['language_name'],
                translation=nova_model.nova_translation
            )
            
            print(f"Should proceed: {result['should_proceed']}")
            print(f"Support level: {result['routing_info']['support_level']}")
            if result['should_proceed']:
                print(f"Processed query: {result['processed_query']}")
                if result['english_query'] != result['processed_query']:
                    print(f"English query: {result['english_query']}")
            else:
                print(f"Error: {result['routing_info']['message']}")
            print('-' * 50)
            
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_routing()