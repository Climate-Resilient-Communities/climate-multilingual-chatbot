"""
Query routing — Tiny-Aya regional model selection + language detection.

Routing priority:
  1. tiny-aya-fire  → South Asian languages
  2. tiny-aya-earth → African languages
  3. tiny-aya-water → Asia-Pacific, Western Asia, European languages
  4. tiny-aya-global → English + catch-all default
  5. nova           → fallback only (when Cohere API is unavailable)
"""
import os
import logging
import re
from enum import Enum
from typing import Dict, Any
from src.utils.env_loader import load_environment
from src.models.cohere_flow import resolve_tiny_aya_model, FIRE_LANGUAGES, EARTH_LANGUAGES, WATER_LANGUAGES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LanguageSupport(Enum):
    """Model tier for a given language."""
    TINY_AYA_GLOBAL = "tiny_aya_global"
    TINY_AYA_FIRE = "tiny_aya_fire"
    TINY_AYA_EARTH = "tiny_aya_earth"
    TINY_AYA_WATER = "tiny_aya_water"
    NOVA = "nova"  # fallback only


class MultilingualRouter:
    """Routes queries to the correct Tiny-Aya regional model based on language."""

    # ── Language code normalisation ──────────────────────────────────────
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
        'bn-bd': 'bn', 'ta-in': 'ta', 'ur-pk': 'ur', 'fa-ir': 'fa',
    }

    # ── Language code → name (183 languages) ────────────────────────────
    LANGUAGE_NAME_MAP = {
        'aa': 'afar', 'ab': 'abkhazian', 'ae': 'avestan', 'af': 'afrikaans', 'ak': 'akan', 'am': 'amharic', 'an': 'aragonese', 'ar': 'arabic', 'as': 'assamese', 'av': 'avaric',
        'ay': 'aymara', 'az': 'azerbaijani', 'ba': 'bashkir', 'be': 'belarusian', 'bg': 'bulgarian', 'bi': 'bislama', 'bm': 'bambara', 'bn': 'bengali', 'bo': 'tibetan', 'br': 'breton',
        'bs': 'bosnian', 'ca': 'catalan', 'ce': 'chechen', 'ch': 'chamorro', 'co': 'corsican', 'cr': 'cree', 'cs': 'czech', 'cu': 'church slavic', 'cv': 'chuvash', 'cy': 'welsh',
        'da': 'danish', 'de': 'german', 'dv': 'divehi', 'dz': 'dzongkha', 'ee': 'ewe', 'el': 'greek', 'en': 'english', 'eo': 'esperanto', 'es': 'spanish', 'et': 'estonian',
        'eu': 'basque', 'fa': 'persian', 'ff': 'fulah', 'fi': 'finnish', 'fj': 'fijian', 'fo': 'faroese', 'fr': 'french', 'fy': 'western frisian', 'ga': 'irish', 'gd': 'gaelic',
        'gl': 'galician', 'gn': 'guarani', 'gu': 'gujarati', 'gv': 'manx', 'ha': 'hausa', 'he': 'hebrew', 'hi': 'hindi', 'ho': 'hiri motu', 'hr': 'croatian', 'ht': 'haitian',
        'hu': 'hungarian', 'hy': 'armenian', 'hz': 'herero', 'ia': 'interlingua', 'id': 'indonesian', 'ie': 'interlingue', 'ig': 'igbo', 'ii': 'sichuan yi', 'ik': 'inupiaq', 'io': 'ido',
        'is': 'icelandic', 'it': 'italian', 'iu': 'inuktitut', 'ja': 'japanese', 'jv': 'javanese', 'ka': 'georgian', 'kg': 'kongo', 'ki': 'kikuyu', 'kj': 'kuanyama', 'kk': 'kazakh',
        'kl': 'kalaallisut', 'km': 'central khmer', 'kn': 'kannada', 'ko': 'korean', 'kr': 'kanuri', 'ks': 'kashmiri', 'ku': 'kurdish', 'kv': 'komi', 'kw': 'cornish', 'ky': 'kirghiz',
        'la': 'latin', 'lb': 'luxembourgish', 'lg': 'ganda', 'li': 'limburgan', 'ln': 'lingala', 'lo': 'lao', 'lt': 'lithuanian', 'lu': 'luba-katanga', 'lv': 'latvian', 'mg': 'malagasy',
        'mh': 'marshallese', 'mi': 'maori', 'mk': 'macedonian', 'ml': 'malayalam', 'mn': 'mongolian', 'mr': 'marathi', 'ms': 'malay', 'mt': 'maltese', 'my': 'burmese', 'na': 'nauru',
        'nb': 'norwegian bokmål', 'nd': 'ndebele, north', 'ne': 'nepali', 'ng': 'ndonga', 'nl': 'dutch', 'nn': 'norwegian nynorsk', 'no': 'norwegian', 'nr': 'ndebele, south', 'nv': 'navajo', 'ny': 'chichewa',
        'oc': 'occitan', 'oj': 'ojibwa', 'om': 'oromo', 'or': 'oriya', 'os': 'ossetian', 'pa': 'panjabi', 'pi': 'pali', 'pl': 'polish', 'ps': 'pushto', 'pt': 'portuguese',
        'qu': 'quechua', 'rm': 'romansh', 'rn': 'rundi', 'ro': 'romanian', 'ru': 'russian', 'rw': 'kinyarwanda', 'sa': 'sanskrit', 'sc': 'sardinian', 'sd': 'sindhi', 'se': 'northern sami',
        'sg': 'sango', 'si': 'sinhala', 'sk': 'slovak', 'sl': 'slovenian', 'sm': 'samoan', 'sn': 'shona', 'so': 'somali', 'sq': 'albanian', 'sr': 'serbian', 'ss': 'swati',
        'st': 'sotho, southern', 'su': 'sundanese', 'sv': 'swedish', 'sw': 'swahili', 'ta': 'tamil', 'te': 'telugu', 'tg': 'tajik', 'th': 'thai', 'ti': 'tigrinya', 'tk': 'turkmen',
        'tl': 'tagalog', 'tn': 'tswana', 'to': 'tonga', 'tr': 'turkish', 'ts': 'tsonga', 'tt': 'tatar', 'tw': 'twi', 'ty': 'tahitian', 'ug': 'uighur', 'uk': 'ukrainian',
        'ur': 'urdu', 'uz': 'uzbek', 've': 'venda', 'vi': 'vietnamese', 'vo': 'volapük', 'wa': 'walloon', 'wo': 'wolof', 'xh': 'xhosa', 'yi': 'yiddish', 'yo': 'yoruba',
        'za': 'zhuang', 'zh': 'chinese', 'zu': 'zulu',
    }

    def __init__(self):
        """Initialize language routing."""
        pass

    # ── Heuristic language detection (unchanged from original) ──────────

    def _is_probably_english(self, text: str) -> bool:
        if not text:
            return False
        t = text.lower()
        ascii_letters = re.findall(r"[a-z]", t)
        ascii_ratio = len(ascii_letters) / max(1, len(t))
        en_hits = sum(1 for w in (" the ", " and ", " what ", " is ", " of ", " to ", " in ") if w in f" {t} ")
        es_hits = sum(1 for w in (" el ", " la ", " los ", " las ", " y ", " de ", " del ", " qué ", " que ", " es ") if w in f" {t} ")
        return ascii_ratio > 0.7 and en_hits >= 1 and es_hits == 0

    def _is_probably_non_english(self, text: str) -> bool:
        if not text:
            return False
        t = text.lower()
        es_hits = sum(1 for w in (" el ", " la ", " los ", " las ", " y ", " de ", " del ", " que ", " por ", " para ") if w in f" {t} ")
        en_hits = sum(1 for w in (" the ", " and ", " what ", " is ", " of ", " to ", " in ") if w in f" {t} ")
        return es_hits > en_hits

    def _detect_language_code_simple(self, text: str) -> str:
        if not text:
            return 'unknown'
        t = f" {text.lower()} "
        # Greeting shortcuts
        for token in (" hello ", " hi ", " hey ", " thanks ", " thank you ", " goodbye ", " bye "):
            if token in t:
                return 'en'
        for token in (" hola ", " buenos ", " buenas ", " gracias ", " adiós ", " cómo ", " como "):
            if token in t:
                return 'es'
        for token in (" bonjour ", " salut ", " merci ", " au revoir ", " comment "):
            if token in t:
                return 'fr'
        # Script detection
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
        # Stopword scoring for Latin scripts
        def hits(s):
            return sum(1 for w in s if w in t)
        scores = {
            'en': hits([" the ", " and ", " what ", " is ", " of ", " to ", " in "]),
            'es': hits([" el ", " la ", " los ", " las ", " de ", " del ", " que ", " por ", " para ", " es ", " qué ", " con ", " en ", " se ", " un ", " una "]),
            'fr': hits([" le ", " la ", " les ", " des ", " du ", " est ", " que ", " pour ", " avec ", " sur "]),
            'de': hits([" der ", " die ", " das ", " und ", " ist ", " nicht ", " mit ", " auf "]),
            'it': hits([" il ", " lo ", " la ", " gli ", " le ", " che ", " per ", " con ", " non ", " è "]),
            'pt': hits([" os ", " as ", " da ", " que ", " para ", " com ", " não ", " está ", " são ", " tem "]),
        }
        lang, score = max(scores.items(), key=lambda x: x[1])
        return lang if score >= 2 else 'unknown'

    # ── Public API ──────────────────────────────────────────────────────

    def detect_language(self, text: str) -> Dict[str, Any]:
        detected_code = self._detect_language_code_simple(text)
        if detected_code == 'unknown':
            detected_code = 'en'
            confidence = 0.5
        else:
            confidence = 0.8
        return {
            'language_code': detected_code,
            'confidence': confidence,
            'method': 'simple_detection',
        }

    def standardize_language_code(self, language_code: str) -> str:
        return self.LANGUAGE_CODE_MAP.get(language_code.lower(), language_code.lower())

    def check_language_support(self, language_code: str) -> LanguageSupport:
        """Determine which Tiny-Aya regional model to use for a language."""
        lc = self.standardize_language_code(language_code)
        if lc in FIRE_LANGUAGES:
            return LanguageSupport.TINY_AYA_FIRE
        if lc in EARTH_LANGUAGES:
            return LanguageSupport.TINY_AYA_EARTH
        if lc in WATER_LANGUAGES:
            return LanguageSupport.TINY_AYA_WATER
        return LanguageSupport.TINY_AYA_GLOBAL

    def _get_model_info(self, support: LanguageSupport) -> Dict[str, str]:
        """Return model_type and human-readable model_name for a support tier."""
        model_id, region = resolve_tiny_aya_model('en')  # default
        mapping = {
            LanguageSupport.TINY_AYA_GLOBAL: ("tiny_aya_global", "Tiny-Aya Global", "tiny-aya-global"),
            LanguageSupport.TINY_AYA_FIRE:   ("tiny_aya_fire",   "Tiny-Aya Fire",   "tiny-aya-fire"),
            LanguageSupport.TINY_AYA_EARTH:  ("tiny_aya_earth",  "Tiny-Aya Earth",  "tiny-aya-earth"),
            LanguageSupport.TINY_AYA_WATER:  ("tiny_aya_water",  "Tiny-Aya Water",  "tiny-aya-water"),
            LanguageSupport.NOVA:            ("nova",            "Nova",             "amazon.nova-lite-v1:0"),
        }
        model_type, model_name, model_id = mapping.get(
            support, ("tiny_aya_global", "Tiny-Aya Global", "tiny-aya-global")
        )
        return {"model_type": model_type, "model_name": model_name, "model_id": model_id}

    async def route_query(
        self,
        query: str,
        language_code: str,
        language_name: str,
        translation: Any = None,
    ) -> Dict[str, Any]:
        """Route and process query — central decision maker."""
        try:
            support_level = self.check_language_support(language_code)
            info = self._get_model_info(support_level)
            model_type = info["model_type"]
            model_name = info["model_name"]

            logger.info(f"Language: {language_name} ({language_code}) → Model: {model_name}")

            routing_info = {
                'support_level': support_level.value,
                'model_type': model_type,
                'model_name': model_name,
                'model_id': info["model_id"],
                'needs_translation': language_code != 'en',
                'language_code': language_code,
                'language_name': language_name,
                'message': None,
            }

            english_query = query
            processed_query = query

            # Mismatch detection
            language_mismatch = False
            detected_code = self._detect_language_code_simple(query)
            if detected_code != 'unknown' and detected_code != language_code:
                language_mismatch = True
                routing_info['message'] = (
                    f"Detected {detected_code} text while language selected is {language_name}. "
                    "You can switch the language in the sidebar."
                )
                routing_info['detected_language'] = detected_code
                return {
                    'should_proceed': True,
                    'routing_info': {**routing_info, 'language_mismatch': language_mismatch},
                    'processed_query': query,
                    'english_query': query,
                }

            # Translate non-English queries
            if routing_info['needs_translation'] and translation and not language_mismatch:
                try:
                    logger.info(f"Translating query from {language_name} to English")
                    english_query = await translation(query, language_name, 'english')
                    processed_query = english_query
                    logger.info("Translation successful")
                except Exception as e:
                    logger.error(f"Translation error: {e}")
                    routing_info['message'] = f"Translation failed: {e}"
                    return {
                        'should_proceed': False,
                        'routing_info': routing_info,
                        'processed_query': query,
                        'english_query': query,
                    }

            return {
                'should_proceed': True,
                'routing_info': {**routing_info, 'language_mismatch': language_mismatch},
                'processed_query': processed_query,
                'english_query': english_query,
            }

        except Exception as e:
            logger.error(f"Error in query routing: {e}")
            return {
                'should_proceed': False,
                'routing_info': {
                    'support_level': 'nova',
                    'model_type': 'nova',
                    'model_name': 'Nova',
                    'needs_translation': False,
                    'language_code': language_code,
                    'language_name': language_name,
                    'message': f"Routing error: {e}",
                },
                'processed_query': query,
                'english_query': query,
            }
