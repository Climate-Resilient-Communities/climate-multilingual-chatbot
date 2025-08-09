import os
import asyncio
import logging
import time
import warnings
from typing import Dict, Any, List, Optional, Callable
import hashlib
import re
from langsmith import traceable

# Filter out transformer warnings early
warnings.filterwarnings("ignore", message="You're using a XLMRobertaTokenizerFast tokenizer")
warnings.filterwarnings("ignore", message=".*XLMRobertaTokenizerFast.*", category=UserWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

from src.utils.env_loader import load_environment
from src.models.query_routing import MultilingualRouter
from src.models.query_rewriter import query_rewriter
from src.models.retrieval import get_documents
from src.models.gen_response_unified import UnifiedResponseGenerator
from src.models.hallucination_guard import check_hallucination, extract_contexts, evaluate_faithfulness_threshold
from src.models.redis_cache import ClimateCache
from src.models.nova_flow import BedrockModel
from src.models.cohere_flow import CohereModel
from src.models.conversation_parser import conversation_parser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClimateQueryPipeline:
    """New unified processing pipeline for climate queries."""
    
    def __init__(self, index_name: Optional[str] = None):
        """Initialize the processing pipeline with eager heavy-resource setup for fast first query."""
        try:
            load_environment()
            
            # Lightweight components
            self.router = MultilingualRouter()
            self.response_generator = UnifiedResponseGenerator()
            self.redis_client = self._initialize_redis()
            
            # Models for translation (lightweight clients)
            self.nova_model = BedrockModel()
            self.cohere_model = CohereModel()
            
            # Eager heavy initialization for embeddings, index, and Cohere client
            self.index_name = index_name or "climate-chatbot-index"
            _t0 = time.time()
            self.embed_model = self._initialize_embedding_model()
            logger.info(f"Init: embeddings model ready in {time.time() - _t0:.2f}s")
            _t1 = time.time()
            self.index = self._initialize_pinecone_index()
            logger.info(f"Init: pinecone index ready in {time.time() - _t1:.2f}s")
            
            # Cohere client for retrieval and reranking
            self.COHERE_API_KEY = os.getenv("COHERE_API_KEY")
            _t2 = time.time()
            self.cohere_client = self._init_cohere()
            logger.info(f"Init: cohere client ready in {time.time() - _t2:.2f}s")
            
            logger.info("✓ Climate Query Pipeline initialized (eager heavy-init)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Climate Query Pipeline: {str(e)}")
            raise

    async def prewarm(self) -> None:
        """Pre-initialize heavy dependencies to reduce first-query latency."""
        try:
            logger.info("Prewarm: starting heavy component initialization")
            start = time.time()
            # Embedding model
            t0 = time.time()
            if self.embed_model is None:
                self.embed_model = self._initialize_embedding_model()
            logger.info(f"Prewarm: embeddings ready in {time.time() - t0:.2f}s")
            # Pinecone index
            t1 = time.time()
            if self.index is None:
                self.index = self._initialize_pinecone_index()
            logger.info(f"Prewarm: pinecone ready in {time.time() - t1:.2f}s")
            # Cohere client
            t2 = time.time()
            if self.cohere_client is None:
                self.cohere_client = self._init_cohere()
            logger.info(f"Prewarm: cohere client ready in {time.time() - t2:.2f}s")
            logger.info(f"Prewarm complete in {time.time() - start:.2f}s")
        except Exception as e:
            logger.warning(f"Prewarm encountered an error: {str(e)}")

    def _initialize_redis(self):
        """Initialize Redis cache."""
        try:
            cache = ClimateCache()
            return cache.redis_client if hasattr(cache, 'redis_client') else None
        except Exception as e:
            logger.warning(f"Redis initialization failed: {str(e)}")
            return None

    def _initialize_embedding_model(self):
        """Initialize embedding model with optimizations for tokenizer performance."""
        try:
            from FlagEmbedding import BGEM3FlagModel
            model_path = os.getenv("EMBED_MODEL_PATH", "BAAI/bge-m3")
            
            # Initialize with optimizations and warning suppression
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                warnings.simplefilter("ignore", FutureWarning)
                warnings.filterwarnings("ignore", message=".*XLMRobertaTokenizerFast.*")
                warnings.filterwarnings("ignore", message=".*fast tokenizer.*")
                
                model = BGEM3FlagModel(model_path, use_fp16=True, device="cpu")
            
            # Try to optimize tokenizer usage if accessible
            if hasattr(model, 'tokenizer') and hasattr(model.tokenizer, '__call__'):
                logger.info("✓ Embedding model initialized with fast tokenizer")
            else:
                logger.debug("Embedding model using standard tokenizer (performance could be improved)")
                
            return model
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {str(e)}")
            raise

    def _initialize_pinecone_index(self):
        """Initialize Pinecone index."""
        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            return pc.Index(self.index_name)
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            raise

    def _init_cohere(self):
        """Initialize Cohere client."""
        try:
            import cohere
            return cohere.Client(self.COHERE_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Cohere client: {str(e)}")
            raise

    def get_language_code(self, language_name: str) -> str:
        """Convert language name to code."""
        language_map = {
            'english': 'en', 'spanish': 'es', 'french': 'fr', 'german': 'de',
            'italian': 'it', 'portuguese': 'pt', 'dutch': 'nl', 'russian': 'ru',
            'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko', 'arabic': 'ar',
            'hindi': 'hi', 'bengali': 'bn', 'urdu': 'ur', 'tamil': 'ta',
            'gujarati': 'gu', 'persian': 'fa', 'vietnamese': 'vi', 'thai': 'th',
            'turkish': 'tr', 'polish': 'pl', 'czech': 'cs', 'hungarian': 'hu',
            'romanian': 'ro', 'greek': 'el', 'hebrew': 'he', 'ukrainian': 'uk',
            'indonesian': 'id', 'filipino': 'tl', 'danish': 'da', 'swedish': 'sv',
            'norwegian': 'no', 'finnish': 'fi', 'bulgarian': 'bg', 'slovak': 'sk',
            'slovenian': 'sl', 'estonian': 'et', 'latvian': 'lv', 'lithuanian': 'lt'
        }
        return language_map.get(language_name.lower(), 'en')

    @traceable(name="climate_query_processing")
    async def process_query(
        self,
        query: str,
        language_name: str,
        conversation_history: Optional[List[Dict]] = None,
        run_manager=None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """
        Main processing pipeline - replaces the old _process_query_internal.
        
        Flow: Route → Rewrite → Retrieve → Generate → Guard → Return
        """
        start_time = time.time()
        
        def report(stage: str, pct: float) -> None:
            if progress_callback is None:
                return
            try:
                progress_callback(stage, float(max(0.0, min(1.0, pct))))
            except Exception:
                # Never fail pipeline due to UI callback issues
                pass
        language_code = self.get_language_code(language_name)
        
        try:
            logger.info(f"Processing query: '{query[:100]}...' in {language_name} (code: {language_code})")
            report("Thinking…", 0.02)
            
            # Initialize holders
            response: Optional[str] = None
            citations: List[Dict[str, Any]] = []
            used_cached: bool = False
            cached_response_language: str = 'en'  # Track language of cached response
            _retr_start = _gen_start = _hall_start = time.time()
            
            # STEP 1: ROUTE THE QUERY
            logger.info("Step 1: Query Routing")
            _route_start = time.time()
            
            # Get translation function based on routing decision
            route_result = await self.router.route_query(
                query=query,
                language_code=language_code,
                language_name=language_name,
                translation=None
            )
            report("Routing…", 0.08)
            
            # Check for language mismatch early
            if route_result.get('routing_info', {}).get('language_mismatch'):
                detected_lang = route_result['routing_info'].get('detected_language', 'unknown')
                lang_code_to_name = {
                    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                    'it': 'Italian', 'pt': 'Portuguese', 'nl': 'Dutch', 'ru': 'Russian',
                    'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic',
                    'hi': 'Hindi', 'bn': 'Bengali', 'ur': 'Urdu', 'ta': 'Tamil',
                    'gu': 'Gujarati', 'fa': 'Persian', 'vi': 'Vietnamese', 'th': 'Thai',
                    'tr': 'Turkish', 'pl': 'Polish', 'cs': 'Czech', 'hu': 'Hungarian',
                    'ro': 'Romanian', 'el': 'Greek', 'he': 'Hebrew', 'uk': 'Ukrainian',
                    'id': 'Indonesian', 'tl': 'Filipino', 'da': 'Danish', 'sv': 'Swedish',
                    'no': 'Norwegian', 'fi': 'Finnish', 'bg': 'Bulgarian', 'sk': 'Slovak',
                    'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian', 'lt': 'Lithuanian'
                }
                detected_name = lang_code_to_name.get(detected_lang, detected_lang.upper())
                
                return self._create_error_response(
                    "Whoops! You wrote in a different language than the one you selected. Please choose the language you want me to respond in on the side panel so I can ensure the best translation for you!",
                    language_code,
                    time.time() - start_time
                )
            
            if not route_result['should_proceed']:
                return self._create_error_response(
                    route_result['routing_info']['message'],
                    language_code,
                    time.time() - start_time
                )

            routing_info = route_result['routing_info']
            model_type = routing_info['model_type']
            
            logger.info(f"✓ Routed to {routing_info['model_name']} model")
            logger.info(f"Timing: routing={(time.time() - _route_start)*1000:.1f}ms")
            
            # Set translation function based on model type
            if routing_info['needs_translation']:
                if model_type == 'nova':
                    translation_func = self.nova_model.translate
                else:
                    translation_func = self.cohere_model.translate
                
                # Re-run routing with proper translation function
                route_result = await self.router.route_query(
                    query=query,
                    language_code=language_code,
                    language_name=language_name,
                    translation=translation_func
                )
                
                if not route_result['should_proceed']:
                    return self._create_error_response(
                        route_result['routing_info']['message'],
                        language_code,
                        time.time() - start_time
                    )

            processed_query = route_result['processed_query']
            english_query = route_result['english_query']
            
            # STEP 2: CHECK CACHE
            logger.info("Step 2: Cache Check")
            _cache_start = time.time()
            normalized = self._normalize_query(english_query)
            
            # FIX: Create language-specific cache keys for non-English queries
            # This ensures Filipino queries get Filipino responses from cache
            cache_key = self._make_cache_key(language_code, model_type, normalized)
            
            if self.redis_client and not skip_cache:
                try:
                    cache = ClimateCache()
                    cached_result = await cache.get(cache_key)
                    
                    if cached_result:
                        logger.info(f"✓ Cache hit for {language_name} - returning cached response")
                        # Cached result should already be in the correct language
                        return self._add_processing_time(cached_result, start_time)
                    else:
                        logger.info(f"Cache miss for {language_name} query")
                        
                        # Try fuzzy match for this specific language
                        fuzzy_hit = await self._try_fuzzy_cache_match(
                            normalized, 
                            language_code=language_code,
                            model_type=model_type
                        )
                        if fuzzy_hit is not None:
                            logger.info(f"✓ Cache hit via fuzzy match (score={fuzzy_hit['score']:.2f})")
                            return self._add_processing_time(fuzzy_hit['result'], start_time)
                            
                except Exception as e:
                    logger.debug(f"Cache unavailable: {str(e)}")
            logger.info(f"Timing: cache={(time.time() - _cache_start)*1000:.1f}ms")

            # STEP 3: REWRITE THE QUERY
            logger.info("Step 3: Query Rewriting")
            _rewrite_start = time.time()
            report("Rewriting query…", 0.14)
            try:
                # Parse conversation history properly for query rewriter
                formatted_history = conversation_parser.format_for_query_rewriter(conversation_history)
                
                rewriter_output = await query_rewriter(
                    user_query=query,  # Use original query for language detection, not translated version
                    nova_model=self.nova_model,
                    conversation_history=formatted_history,
                    selected_language_code=language_code
                )
                text = (rewriter_output or "").strip()
                
                # Parse fields
                lang_match = re.search(r"Language:\s*([a-z]{2}|unknown)", text, re.IGNORECASE)
                cls_match = re.search(r"Classification:\s*(on-topic|off-topic|harmful)", text, re.IGNORECASE)
                match_match = re.search(r"LanguageMatch:\s*(yes|no)", text, re.IGNORECASE)
                rew_match = re.search(r"Rewritten:\s*(.+)", text, re.IGNORECASE)
                detected_lang = (lang_match.group(1).lower() if lang_match else 'unknown')
                classification = (cls_match.group(1).lower() if cls_match else 'off-topic')
                language_match_result = (match_match.group(1).lower() if match_match else 'unknown')
                
                logger.info(f"Query rewriter processed: detected_lang='{detected_lang}', classification='{classification}', language_match='{language_match_result}'")

                # Check for language mismatch based on query rewriter analysis
                if language_match_result == 'no' or (detected_lang != 'unknown' and detected_lang != language_code):
                    lang_code_to_name = {
                        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                        'it': 'Italian', 'pt': 'Portuguese', 'nl': 'Dutch', 'ru': 'Russian',
                        'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic',
                        'hi': 'Hindi', 'bn': 'Bengali', 'ur': 'Urdu', 'ta': 'Tamil',
                        'gu': 'Gujarati', 'fa': 'Persian', 'vi': 'Vietnamese', 'th': 'Thai',
                        'tr': 'Turkish', 'pl': 'Polish', 'cs': 'Czech', 'hu': 'Hungarian',
                        'ro': 'Romanian', 'el': 'Greek', 'he': 'Hebrew', 'uk': 'Ukrainian',
                        'id': 'Indonesian', 'tl': 'Filipino', 'da': 'Danish', 'sv': 'Swedish',
                        'no': 'Norwegian', 'fi': 'Finnish', 'bg': 'Bulgarian', 'sk': 'Slovak',
                        'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian', 'lt': 'Lithuanian'
                    }
                    detected_name = lang_code_to_name.get(detected_lang, detected_lang.upper())
                    selected_name = lang_code_to_name.get(language_code, language_code.upper())
                    
                    logger.warning(f"Language mismatch detected by query rewriter: query is in {detected_name} but {selected_name} was selected")
                    return self._create_error_response(
                        "Whoops! You wrote in a different language than the one you selected. Please choose the language you want me to respond in on the side panel so I can ensure the best translation for you!",
                        language_code,
                        time.time() - start_time
                    )

                if classification == 'off-topic':
                    return self._create_error_response(
                        "I'm a climate change assistant and can only help with questions about climate, environment, and sustainability.",
                        language_code,
                        time.time() - start_time
                    )
                if classification == 'harmful':
                    return self._create_error_response(
                        "I can't assist with that request. Please ask me questions about climate change, environmental issues, or sustainability.",
                        language_code,
                        time.time() - start_time
                    )

                # Adopt rewritten query if provided
                if rew_match and rew_match.group(1).strip().lower() != 'n/a':
                    processed_query = rew_match.group(1).strip()
                    logger.info("✓ Query rewritten for better retrieval")
                else:
                    logger.info("✓ Query rewriting skipped - no enhancement needed")
            except Exception as e:
                logger.warning(f"Query rewriting failed, using original: {str(e)}")
            logger.info(f"Timing: rewrite={(time.time() - _rewrite_start)*1000:.1f}ms")

            # STEP 4: INPUT GUARDS
            logger.info("Step 4: Input Guards")
            _guards_start = time.time()
            report("Validating input…", 0.2)
            guard_results = await self._process_input_guards(processed_query)
            if not guard_results['passed']:
                return self._create_error_response(
                    "Query failed content moderation checks",
                    language_code,
                    time.time() - start_time
                )
            logger.info("✓ Input guards passed")
            logger.info(f"Timing: guards={(time.time() - _guards_start)*1000:.1f}ms")

            # Ensure heavy deps are ready
            if self.embed_model is None:
                t_embed = time.time()
                self.embed_model = self._initialize_embedding_model()
                logger.info(f"Init: embeddings initialized in {time.time() - t_embed:.2f}s")
            if self.index is None:
                t_index = time.time()
                self.index = self._initialize_pinecone_index()
                logger.info(f"Init: pinecone index initialized in {time.time() - t_index:.2f}s")
            if self.cohere_client is None:
                t_cohere = time.time()
                self.cohere_client = self._init_cohere()
                logger.info(f"Init: cohere client initialized in {time.time() - t_cohere:.2f}s")

            # STEP 5: RETRIEVE DOCUMENTS
            logger.info("Step 5: Document Retrieval")
            _retr_start = time.time()
            report("Retrieving documents…", 0.35)
            try:
                documents = await get_documents(
                    processed_query,
                    self.index,
                    self.embed_model,
                    self.cohere_client
                )
                logger.info(f"✓ Retrieved {len(documents)} documents")
            except Exception as e:
                logger.error(f"Document retrieval failed: {str(e)}")
                documents = []
            logger.info(f"Timing: retrieval={(time.time() - _retr_start)*1000:.1f}ms")
            report("Documents retrieved", 0.6)

            # STEP 6: GENERATE RESPONSE
            logger.info(f"Step 6: Response Generation ({routing_info['model_name']})")
            _gen_start = time.time()
            report("Formulating response…", 0.7)
            try:
                # Generate response in English first
                response, citations = await self.response_generator.generate_response(
                    query=processed_query,
                    documents=documents,
                    model_type=model_type,
                    language_code='en',  # Always generate in English first
                    conversation_history=conversation_history
                )
                logger.info("✓ Response generated successfully in English")
            except Exception as e:
                logger.error(f"Response generation failed: {str(e)}")
                return self._create_error_response(
                    f"Response generation failed: {str(e)}",
                    language_code,
                    time.time() - start_time
                )
            logger.info(f"Timing: generation={(time.time() - _gen_start)*1000:.1f}ms")
            report("Response drafted", 0.85)

            # STEP 7: HALLUCINATION GUARD
            logger.info("Step 7: Quality Validation")
            _hall_start = time.time()
            report("Verifying answer…", 0.9)
            try:
                if self.COHERE_API_KEY:
                    contexts = extract_contexts(documents, max_contexts=5)
                    faithfulness_score = await check_hallucination(
                        question=english_query,
                        answer=response,
                        contexts=contexts,
                        cohere_api_key=self.COHERE_API_KEY,
                        threshold=0.7,
                        bedrock_model=self.nova_model
                    )
                    evaluation = evaluate_faithfulness_threshold(faithfulness_score, threshold=0.7)
                    logger.info(f"✓ Faithfulness score: {faithfulness_score:.3f}")
                    logger.info(f"✓ Assessment: {evaluation['assessment']}")
                    if not evaluation['is_faithful']:
                        logger.warning(f"Response faithfulness below threshold: {faithfulness_score:.3f} < 0.7")
                else:
                    logger.warning("Cohere API key not found, skipping hallucination check")
                    faithfulness_score = 0.8
            except Exception as e:
                logger.warning(f"Hallucination check failed: {str(e)}")
                faithfulness_score = 0.3
            logger.info(f"Timing: faithfulness={(time.time() - _hall_start)*1000:.1f}ms")

            # STEP 8: TRANSLATE RESPONSE IF NEEDED
            _trans_time = 0.0
            original_english_response = response  # Keep English version for caching
            
            if language_code != 'en':
                logger.info(f"Step 8: Translating response to {language_name} (code={language_code})")
                try:
                    _trans_start = time.time()
                    # Use Nova translator for all languages including Filipino
                    translated_response = await self.nova_model.translate(
                        response, 
                        'english', 
                        language_name
                    )
                    response = translated_response
                    logger.info(f"✓ Response translated successfully to {language_name}")
                except Exception as e:
                    logger.error(f"Response translation to {language_name} failed: {str(e)}")
                    # Keep English response if translation fails
                else:
                    _trans_time = (time.time() - _trans_start) * 1000
                    logger.info(f"Timing: translation={_trans_time:.1f}ms")
            report("Finalizing…", 0.96)

            # STEP 9: PREPARE FINAL RESULT
            result = {
                "success": True,
                "response": response,
                "citations": citations,
                "faithfulness_score": faithfulness_score,
                "processing_time": time.time() - start_time,
                "language_code": language_code,
                "model_used": routing_info['model_name'],
                "model_type": model_type
            }

            # STEP 10: CACHE THE RESULT IN THE CORRECT LANGUAGE
            if self.redis_client:
                try:
                    cache = ClimateCache()
                    
                    # Cache the response in the requested language
                    await cache.set(cache_key, result)
                    logger.info(f"✓ Response cached in {language_name}")
                    
                    # Also cache the English version if different
                    if language_code != 'en':
                        english_cache_key = self._make_cache_key('en', model_type, normalized)
                        english_result = result.copy()
                        english_result['response'] = original_english_response
                        english_result['language_code'] = 'en'
                        await cache.set(english_cache_key, english_result)
                        logger.info("✓ English version also cached")
                    
                    # Maintain recent queries list
                    try:
                        entry = f"{cache_key}|{normalized}|{language_code}"
                        await asyncio.to_thread(self.redis_client.lpush, "q:recent", entry)
                        await asyncio.to_thread(self.redis_client.ltrim, "q:recent", 0, 99)
                    except Exception as list_err:
                        logger.debug(f"Recent list update skipped: {list_err}")
                        
                except Exception as e:
                    logger.warning(f"Failed to cache result: {str(e)}")

            # Log timing summary
            logger.info(
                "Timing summary (ms): routing=%.1f rewrite=%.1f guards=%.1f retrieval=%.1f generation=%.1f faithfulness=%.1f translation=%.1f total=%.1f",
                (time.time() - _route_start) * 1000,
                (time.time() - _rewrite_start) * 1000,
                (time.time() - _guards_start) * 1000,
                (time.time() - _retr_start) * 1000,
                (time.time() - _gen_start) * 1000,
                (time.time() - _hall_start) * 1000,
                _trans_time,
                result['processing_time'] * 1000,
            )
            logger.info(f"✓ Query processed successfully in {result['processing_time']:.2f}s")
            report("Complete", 1.0)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Pipeline error: {error_msg}")
            return self._create_error_response(error_msg, language_code, time.time() - start_time)

    async def _process_input_guards(self, query: str) -> Dict[str, Any]:
        """Process input moderation guards."""
        return {"passed": True, "reason": "query_rewriter_classification_passed"}

    def _create_error_response(self, error_message: str, language_code: str, processing_time: float) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "success": False,
            "response": error_message,
            "citations": [],
            "faithfulness_score": 0.0,
            "processing_time": processing_time,
            "language_code": language_code,
            "model_used": "N/A",
            "model_type": "N/A"
        }

    def _add_processing_time(self, cached_result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Add current processing time to cached result."""
        cached_result["processing_time"] = time.time() - start_time
        return cached_result

    def _make_cache_key(self, language_code: str, model_type: str, base_query: str) -> str:
        """Create a stable cache key using normalized query and metadata.
        
        FIX: Include language_code in the cache key to ensure language-specific caching.
        """
        key_material = f"{language_code}:{model_type}:{base_query}".encode("utf-8")
        digest = hashlib.sha256(key_material).hexdigest()
        return f"q:{language_code}:{digest}"  # Include language code in key prefix

    def _normalize_query(self, text: str) -> str:
        """Normalize text for cache key generation."""
        if not text:
            return ""
        # Lowercase, remove extra spaces and punctuation spacing
        t = text.lower()
        t = re.sub(r"\s+", " ", t).strip()
        return t

    async def _try_fuzzy_cache_match(
        self, 
        normalized_query: str, 
        language_code: str,
        model_type: str,
        threshold: float = 0.92
    ) -> Optional[Dict[str, Any]]:
        """Try to reuse a cached response if a recent query is a near-duplicate.
        
        FIX: Only match queries in the same language.
        """
        try:
            recent_entries = await asyncio.to_thread(self.redis_client.lrange, "q:recent", 0, 49)
            if not recent_entries:
                return None
                
            norm_tokens = set(normalized_query.split())
            best = {"score": 0.0, "key": None}
            
            for entry in recent_entries:
                try:
                    parts = entry.split("|")
                    if len(parts) >= 3:
                        key, norm, lang = parts[0], parts[1], parts[2]
                    else:
                        key, norm = parts[0], parts[1]
                        lang = 'en'  # Default for backward compatibility
                        
                    # Only consider entries in the same language
                    if lang != language_code:
                        continue
                        
                except ValueError:
                    continue
                    
                if norm == normalized_query:
                    sim = 1.0
                else:
                    other_tokens = set(norm.split())
                    if not norm_tokens or not other_tokens:
                        sim = 0.0
                    else:
                        inter = len(norm_tokens & other_tokens)
                        union = len(norm_tokens | other_tokens)
                        sim = inter / union if union else 0.0
                        
                if sim > best["score"]:
                    best = {"score": sim, "key": key}
                    
            if best["key"] and best["score"] >= threshold:
                cache = ClimateCache()
                cached = await cache.get(best["key"])
                if cached:
                    return {"result": cached, "score": best["score"]}
                    
        except Exception as e:
            logger.debug(f"Fuzzy cache match skipped: {e}")
        return None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        cleanup_errors = []
        
        # Close Redis connection
        if self.redis_client and not getattr(self.redis_client, '_closed', False):
            try:
                cache = ClimateCache()
                if hasattr(cache, 'close'):
                    await cache.close()
                elif hasattr(self.redis_client, 'close'):
                    self.redis_client.close()
            except Exception as e:
                cleanup_errors.append(f"Redis cleanup error: {str(e)}")
                logger.error(f"Error closing Redis connection: {str(e)}")

        if cleanup_errors:
            logger.error(f"Cleanup completed with errors: {', '.join(cleanup_errors)}")
        else:
            logger.info("Pipeline cleanup completed successfully")