import os
import logging
from enum import Enum
from typing import Dict, Any
import re
from src.utils.env_loader import load_environment
from src.utils.logging_setup import ensure_file_logger
from src.models.nova_flow import BedrockModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LanguageSupport(Enum):
    """Enum for language support levels"""
    COMMAND_A = "command_a"            # Command A model support  
    NOVA = "nova"                      # Nova model support
    UNSUPPORTED = "unsupported"        # No support

class MultilingualRouter:
    """Handles language routing for queries."""
    
    COMMAND_A_SUPPORTED_LANGUAGES = {
        'ar',   # Arabic
        'bn',   # Bengali  
        'zh',   # Chinese
        'tl',   # Filipino (Tagalog)
        'fr',   # French
        'gu',   # Gujarati
        'ko',   # Korean
        'fa',   # Persian
        'ru',   # Russian
        'ta',   # Tamil
        'ur',   # Urdu
        'vi',   # Vietnamese
        'pl',   # Polish
        'tr',   # Turkish
        'nl',   # Dutch
        'cs',   # Czech
        'id',   # Indonesian
        'uk',   # Ukrainian
        'ro',   # Romanian
        'el',   # Greek
        'hi',   # Hindi
        'he'    # Hebrew
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
        'sk-sk': 'sk', 'sl-si': 'sl', 'tl-ph': 'tl', 'gu-in': 'gu',
        'bn-bd': 'bn', 'ta-in': 'ta', 'ur-pk': 'ur', 'fa-ir': 'fa'
    }

    def __init__(self):
        """Initialize language routing"""
        # Ensure dedicated file logs exist as well
        try:
            ensure_file_logger(os.getenv("PIPELINE_LOG_FILE", os.path.join(os.getcwd(), "logs", "pipeline_debug.log")))
        except Exception:
            pass

    def _is_probably_english(self, text: str) -> bool:
        """Stricter heuristic for English using ASCII ratio and common stopwords."""
        if not text:
            return False
        t = text.lower()
        ascii_letters = re.findall(r"[a-z]", t)
        ascii_ratio = len(ascii_letters) / max(1, len(t))
        # Simple stopword hit
        en_hits = sum(1 for w in (" the ", " and ", " what ", " is ", " of ", " to ", " in ") if w in f" {t} ")
        es_hits = sum(1 for w in (" el ", " la ", " los ", " las ", " y ", " de ", " del ", " qué ", " que ", " es ") if w in f" {t} ")
        return ascii_ratio > 0.7 and en_hits >= 1 and es_hits == 0

    def _is_probably_non_english(self, text: str) -> bool:
        """Detect likely non-English (Spanish-like) content for mismatch blocking when EN selected."""
        if not text:
            return False
        t = text.lower()
        # Spanish cue words (ASCII-friendly)
        es_hits = sum(1 for w in (" el ", " la ", " los ", " las ", " y ", " de ", " del ", " que ", " por ", " para ") if w in f" {t} ")
        en_hits = sum(1 for w in (" the ", " and ", " what ", " is ", " of ", " to ", " in ") if w in f" {t} ")
        return es_hits > en_hits

    def _detect_language_code_simple(self, text: str) -> str:
        """Very lightweight language guess for routing-mismatch checks.

        Returns a 2-letter code if confident, else 'unknown'.
        """
        if not text:
            return 'unknown'
        t = f" {text.lower()} "
        # Fast path for common English short tokens (greetings/thanks/goodbye)
        english_short_tokens = [
            " hello ", " hi ", " hey ", " thanks ", " thank you ", " goodbye ", " bye "
        ]
        for token in english_short_tokens:
            if token in t:
                return 'en'
        # Script-based quick checks
        if re.search(r"[\u4e00-\u9fff]", t):
            return 'zh'
        if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", t):
            return 'ja'
        if re.search(r"[\uac00-\ud7af]", t):
            return 'ko'
        if re.search(r"[\u0600-\u06ff]", t):
            return 'ar'
        if re.search(r"[\u0590-\u05ff]", t):
            return 'he'
        if re.search(r"[\u0400-\u04FF]", t):
            return 'ru'
        if re.search(r"[\u0900-\u097F]", t):
            return 'hi'
        if re.search(r"[\u0370-\u03FF]", t):
            return 'el'
        if re.search(r"[\u0E00-\u0E7F]", t):
            return 'th'

        # Latin language stopword cues
        def hits(s):
            return sum(1 for w in s if w in t)

        en_set = [" the ", " and ", " what ", " is ", " of ", " to ", " in "]
        es_set = [" el ", " la ", " los ", " las ", " de ", " del ", " que ", " por ", " para ", " es ", " qué "]
        fr_set = [" le ", " la ", " les ", " des ", " du ", " est ", " que ", " pour ", " avec ", " sur "]
        de_set = [" der ", " die ", " das ", " und ", " ist ", " nicht ", " mit ", " auf "]
        it_set = [" il ", " lo ", " la ", " gli ", " le ", " che ", " per ", " con ", " non ", " è "]
        pt_set = [" o ", " a ", " os ", " as ", " de ", " do ", " da ", " que ", " para ", " com ", " não "]

        scores = {
            'en': hits(en_set),
            'es': hits(es_set),
            'fr': hits(fr_set),
            'de': hits(de_set),
            'it': hits(it_set),
            'pt': hits(pt_set),
        }
        lang, score = max(scores.items(), key=lambda x: x[1])
        # Require at least 2 stopword hits to be confident
        return lang if score >= 2 else 'unknown'

    def standardize_language_code(self, language_code: str) -> str:
        """Standardize language codes to match our supported formats."""
        return self.LANGUAGE_CODE_MAP.get(language_code.lower(), language_code.lower())

    def check_language_support(self, language_code: str) -> LanguageSupport:
        """Check the level of language support using standardized language codes."""
        standardized_code = self.standardize_language_code(language_code)
        
        if standardized_code in self.COMMAND_A_SUPPORTED_LANGUAGES:
            return LanguageSupport.COMMAND_A
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
        translation: Any = None
    ) -> Dict[str, Any]:
        """Route and process query based on language - central decision maker."""
        try:
            # Check language support level and determine model
            support_level = self.check_language_support(language_code)
            
            # Determine model type based on language support
            if support_level == LanguageSupport.COMMAND_A:
                model_type = "cohere"
                model_name = "Command-A"
            else:
                model_type = "nova"
                model_name = "Nova"
            
            logger.info(f"Language: {language_name} ({language_code}) → Model: {model_name}")
            
            # Process routing info with model selection
            routing_info = {
                'support_level': support_level.value,
                'model_type': model_type,
                'model_name': model_name,
                'needs_translation': language_code != 'en',
                'language_code': language_code,
                'language_name': language_name,
                'message': None
            }
            
            # Set query processing parameters
            english_query = query
            processed_query = query
            
            # Detect mismatch: selected language differs from detected language (for common languages)
            language_mismatch = False
            detected_code = self._detect_language_code_simple(query)
            if detected_code != 'unknown' and detected_code != language_code:
                language_mismatch = True
                detected_name = detected_code
                # For first-run UX, do not hard-stop; allow pipeline to translate, but include mismatch flag
                routing_info['message'] = (
                    f"Detected {detected_name} text while language selected is {language_name}. "
                    "You can switch the language in the sidebar."
                )
                routing_info['detected_language'] = detected_code
                # Proceed but mark mismatch; pipeline can decide to translate
                return {
                    'should_proceed': True,
                    'routing_info': {**routing_info, 'language_mismatch': language_mismatch},
                    'processed_query': query,
                    'english_query': query
                }

            # Handle non-English queries if translation function provided and no mismatch
            if routing_info['needs_translation'] and translation and not language_mismatch:
                try:
                    logger.info(f"Translating query from {language_name} to English")
                    try:
                        # Net debug before translation
                        logger.info("Router NET IN → query repr=%r", query[:200])
                    except Exception:
                        pass
                    # Translate to English using the provided translation function
                    english_query = await translation(query, language_name, 'english')
                    processed_query = english_query
                    logger.info("Translation successful")
                    try:
                        logger.info("Router NET OUT → english_query repr=%r", english_query[:200])
                    except Exception:
                        pass
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
                'routing_info': {**routing_info, 'language_mismatch': language_mismatch},
                'processed_query': processed_query,
                'english_query': english_query
            }

        except Exception as e:
            logger.error(f"Error in query routing: {str(e)}")
            return {
                'should_proceed': False,
                'routing_info': {
                    'support_level': 'unsupported',
                    'model_type': 'nova',  # Default fallback
                    'model_name': 'Nova',
                    'needs_translation': False,
                    'language_code': language_code,
                    'language_name': language_name,
                    'message': f"Routing error: {str(e)}"
                },
                'processed_query': query,
                'english_query': query
            }

def test_routing():
    """Test the query routing functionality"""
    import asyncio
    
    async def run_tests():
        try:
            # Initialize components
            print("\n=== Testing Query Routing ===")
            load_environment()
            
            # Initialize router and translation
            router = MultilingualRouter()
            nova_model = BedrockModel()
            
            # Test cases - Comprehensive test of all supported languages
            test_cases = [
                # === Command A Languages (22 total) ===
                {
                    'query': 'ما هو تغير المناخ؟',
                    'language_code': 'ar',
                    'language_name': 'arabic'
                },
                {
                    'query': 'জলবায়ু পরিবর্তন কী?',
                    'language_code': 'bn',
                    'language_name': 'bengali'
                },
                {
                    'query': '什么是气候变化？',
                    'language_code': 'zh',
                    'language_name': 'chinese'
                },
                {
                    'query': 'Ano ang climate change?',
                    'language_code': 'tl',
                    'language_name': 'filipino'
                },
                {
                    'query': 'Qu\'est-ce que le changement climatique?',
                    'language_code': 'fr',
                    'language_name': 'french'
                },
                {
                    'query': 'આબોહવા પરિવર્તન શું છે?',
                    'language_code': 'gu',
                    'language_name': 'gujarati'
                },
                {
                    'query': '기후 변화는 무엇입니까?',
                    'language_code': 'ko',
                    'language_name': 'korean'
                },
                {
                    'query': 'تغییرات آب و هوایی چیست؟',
                    'language_code': 'fa',
                    'language_name': 'persian'
                },
                {
                    'query': 'Что такое изменение климата?',
                    'language_code': 'ru',
                    'language_name': 'russian'
                },
                {
                    'query': 'காலநிலை மாற்றம் என்றால் என்ன?',
                    'language_code': 'ta',
                    'language_name': 'tamil'
                },
                {
                    'query': 'موسمیاتی تبدیلی کیا ہے؟',
                    'language_code': 'ur',
                    'language_name': 'urdu'
                },
                {
                    'query': 'Biến đổi khí hậu là gì?',
                    'language_code': 'vi',
                    'language_name': 'vietnamese'
                },
                {
                    'query': 'Co to jest zmiana klimatu?',
                    'language_code': 'pl',
                    'language_name': 'polish'
                },
                {
                    'query': 'İklim değişikliği nedir?',
                    'language_code': 'tr',
                    'language_name': 'turkish'
                },
                {
                    'query': 'Wat is klimaatverandering?',
                    'language_code': 'nl',
                    'language_name': 'dutch'
                },
                {
                    'query': 'Co je změna klimatu?',
                    'language_code': 'cs',
                    'language_name': 'czech'
                },
                {
                    'query': 'Apa itu perubahan iklim?',
                    'language_code': 'id',
                    'language_name': 'indonesian'
                },
                {
                    'query': 'Що таке зміна клімату?',
                    'language_code': 'uk',
                    'language_name': 'ukrainian'
                },
                {
                    'query': 'Ce este schimbarea climatică?',
                    'language_code': 'ro',
                    'language_name': 'romanian'
                },
                {
                    'query': 'Τι είναι η κλιματική αλλαγή;',
                    'language_code': 'el',
                    'language_name': 'greek'
                },
                {
                    'query': 'जलवायु परिवर्तन क्या है?',
                    'language_code': 'hi',
                    'language_name': 'hindi'
                },
                {
                    'query': 'מה זה שינוי אקלים?',
                    'language_code': 'he',
                    'language_name': 'hebrew'
                },
                
                # === Nova Languages (English + 5 additional) ===
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
                    'query': 'Was ist der Klimawandel?',
                    'language_code': 'de',
                    'language_name': 'german'
                },
                {
                    'query': 'Vad är klimatförändringar?',
                    'language_code': 'sv',
                    'language_name': 'swedish'
                },
                {
                    'query': 'Hvad er klimaændringer?',
                    'language_code': 'da',
                    'language_name': 'danish'
                },
                
                # === Edge cases ===
                {
                    'query': '',  # Empty query test
                    'language_code': 'en',
                    'language_name': 'english'
                }
            ]
            
            # Run tests
            command_a_count = 0
            nova_count = 0
            
            for case in test_cases:
                print(f"\nTesting: {case['query']}")
                print(f"Language: {case['language_name']}")
                
                result = await router.route_query(
                    query=case['query'],
                    language_code=case['language_code'],
                    language_name=case['language_name'],
                    translation=nova_model.nova_translation
                )
                
                print(f"Should proceed: {result['should_proceed']}")
                print(f"Support level: {result['routing_info']['support_level']}")
                
                # Count routing decisions
                if result['routing_info']['support_level'] == 'command_a':
                    command_a_count += 1
                elif result['routing_info']['support_level'] == 'nova':
                    nova_count += 1
                    
                if result['should_proceed']:
                    print(f"Processed query: {result['processed_query']}")
                    if result['english_query'] != result['processed_query']:
                        print(f"English query: {result['english_query']}")
                else:
                    print(f"Error: {result['routing_info']['message']}")
                print('-' * 50)
            
            # Print summary
            print(f"\n=== ROUTING SUMMARY ===")
            print(f"Command A routes: {command_a_count}")
            print(f"Nova routes: {nova_count}")
            print(f"Total tests: {len(test_cases)}")
            print(f"Expected Command A: 22 languages")
            print(f"Expected Nova: 6 languages (English + 5 others)")
                
        except Exception as e:
            print(f"Test failed: {str(e)}")
    
    # Run the async tests
    try:
        asyncio.run(run_tests())
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_routing()