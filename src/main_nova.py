import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import logging
import time
import warnings
import json

#remove deprecation warnings from transformers
warnings.filterwarnings(
    "ignore",
    message="`torch.utils._pytree._register_pytree_node` is deprecated",
    module="transformers.utils.generic",
)

# Configure environment variables first
os.environ["PYTORCH_JIT"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_USE_CUDA_DSA"] = "0"

# Add the project root directory to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Import environment loader early
from src.utils.env_loader import load_environment, validate_environment
from src.data.config.azure_config import is_running_in_azure, configure_for_azure

# Load environment variables
load_environment()

# Configure for Azure if running in Azure environment
if is_running_in_azure():
    configure_for_azure()

# Validate required environment variables
env_validation = validate_environment()
if not env_validation["all_present"]:
    missing_vars = env_validation["missing_vars"]
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Configure Azure-specific settings if running in Azure
is_azure = env_validation.get("is_azure", False)
if is_azure:
    logging.info("Running in Azure environment. Configuring Azure-specific settings...")
    # Azure-specific configurations are now handled in configure_for_azure()

# Set environment variables explicitly as they might be needed specifically in this format
# Fix: Use empty string as default for environment variables to avoid None values
os.environ['COHERE_API_KEY'] = os.getenv('COHERE_API_KEY') or ""
os.environ['LANGCHAIN_TRACING_V2'] = os.getenv('LANGCHAIN_TRACING_V2') or ""
os.environ['LANGCHAIN_API_KEY'] = os.getenv('LANGCHAIN_API_KEY') or ""
os.environ['LANGCHAIN_PROJECT'] = os.getenv('LANGSMITH_PROJECT', "climate-chat-production")
os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY') or ""

# Import and configure torch before other imports
import torch
torch.set_num_threads(1)
if torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = True

# Configure torch path settings
if 'torch' in sys.modules:
    import torch.utils.data
    torch.utils.data._utils.MP_STATUS_CHECK_INTERVAL = 0

# Third-party imports
import cohere
from langsmith import Client, traceable, trace

# Local imports
from src.models.redis_cache import ClimateCache
from src.models.nova_flow import BedrockModel
from src.models.gen_response_nova import generate_chat_response  # Fixed import
from src.models.query_routing import MultilingualRouter
from src.models.retrieval import get_documents
from src.models.hallucination_guard import extract_contexts, check_hallucination, evaluate_faithfulness_threshold
from src.models.climate_pipeline import ClimateQueryPipeline  # NEW: Integrated pipeline
from src.data.config.azure_config import get_azure_settings
from src.models.input_guardrail import topic_moderation, check_follow_up_with_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Filter warnings
warnings.filterwarnings("ignore", category=Warning)

# If running in Azure, include Azure settings
AZURE_SETTINGS = get_azure_settings() if is_running_in_azure() else {}

class MultilingualClimateChatbot:
    """
    A multilingual chatbot specialized in climate-related topics.
    
    This chatbot supports multiple languages through translation,
    implements RAG (Retrieval Augmented Generation), and includes
    various guardrails for input validation and output quality.
    """
    
    # Language mappings
    LANGUAGE_NAME_TO_CODE = {
        'afar': 'aa', 'abkhazian': 'ab', 'avestan': 'ae', 'afrikaans': 'af',
        'akan': 'ak', 'amharic': 'am', 'aragonese': 'an', 'arabic': 'ar',
        'assamese': 'as', 'avaric': 'av', 'aymara': 'ay', 'azerbaijani': 'az',
        'bashkir': 'ba', 'belarusian': 'be', 'bulgarian': 'bg', 'bislama': 'bi',
        'bambara': 'bm', 'bengali': 'bn', 'tibetan': 'bo', 'breton': 'br',
        'bosnian': 'bs', 'catalan': 'ca', 'chechen': 'ce', 'chamorro': 'ch',
        'corsican': 'co', 'cree': 'cr', 'czech': 'cs', 'church slavic': 'cu',
        'chuvash': 'cv', 'welsh': 'cy', 'danish': 'da', 'german': 'de',
        'divehi': 'dv', 'dzongkha': 'dz', 'ewe': 'ee', 'greek': 'el',
        'english': 'en', 'esperanto': 'eo', 'spanish': 'es', 'estonian': 'et',
        'basque': 'eu', 'persian': 'fa', 'fulah': 'ff', 'finnish': 'fi',
        'fijian': 'fj', 'faroese': 'fo', 'french': 'fr', 'western frisian': 'fy',
        'irish': 'ga', 'gaelic': 'gd', 'galician': 'gl', 'guarani': 'gn',
        'gujarati': 'gu', 'manx': 'gv', 'hausa': 'ha', 'hebrew': 'he',
        'hindi': 'hi', 'hiri motu': 'ho', 'croatian': 'hr', 'haitian': 'ht',
        'hungarian': 'hu', 'armenian': 'hy', 'herero': 'hz', 'interlingua': 'ia',
        'indonesian': 'id', 'interlingue': 'ie', 'igbo': 'ig', 'sichuan yi': 'ii',
        'inupiaq': 'ik', 'ido': 'io', 'icelandic': 'is', 'italian': 'it',
        'inuktitut': 'iu', 'japanese': 'ja', 'javanese': 'jv', 'georgian': 'ka',
        'kongo': 'kg', 'kikuyu': 'ki', 'kuanyama': 'kj', 'kazakh': 'kk',
        'kalaallisut': 'kl', 'central khmer': 'km', 'kannada': 'kn', 'korean': 'ko',
        'kanuri': 'kr', 'kashmiri': 'ks', 'kurdish': 'ku', 'komi': 'kv',
        'cornish': 'kw', 'kirghiz': 'ky', 'latin': 'la', 'luxembourgish': 'lb',
        'ganda': 'lg', 'limburgan': 'li', 'lingala': 'ln', 'lao': 'lo',
        'lithuanian': 'lt', 'luba-katanga': 'lu', 'latvian': 'lv', 'malagasy': 'mg',
        'marshallese': 'mh', 'maori': 'mi', 'macedonian': 'mk', 'malayalam': 'ml',
        'mongolian': 'mn', 'marathi': 'mr', 'malay': 'ms', 'maltese': 'mt',
        'burmese': 'my', 'nauru': 'na', 'norwegian bokmål': 'nb', 'ndebele, north': 'nd',
        'nepali': 'ne', 'ndonga': 'ng', 'dutch': 'nl', 'norwegian nynorsk': 'nn',
        'norwegian': 'no', 'ndebele, south': 'nr', 'navajo': 'nv', 'chichewa': 'ny',
        'occitan': 'oc', 'ojibwa': 'oj', 'oromo': 'om', 'oriya': 'or',
        'ossetian': 'os', 'panjabi': 'pa', 'pali': 'pi', 'polish': 'pl',
        'pushto': 'ps', 'portuguese': 'pt', 'quechua': 'qu', 'romansh': 'rm',
        'rundi': 'rn', 'romanian': 'ro', 'russian': 'ru', 'kinyarwanda': 'rw',
        'sanskrit': 'sa', 'sardinian': 'sc', 'sindhi': 'sd', 'northern sami': 'se',
        'sango': 'sg', 'sinhala': 'si', 'slovak': 'sk', 'slovenian': 'sl',
        'samoan': 'sm', 'shona': 'sn', 'somali': 'so', 'albanian': 'sq',
        'serbian': 'sr', 'swati': 'ss', 'sotho, southern': 'st', 'sundanese': 'su',
        'swedish': 'sv', 'swahili': 'sw', 'tamil': 'ta', 'telugu': 'te',
        'tajik': 'tg', 'thai': 'th', 'tigrinya': 'ti', 'turkmen': 'tk',
        'tagalog': 'tl', 'tswana': 'tn', 'tonga': 'to', 'turkish': 'tr',
        'tsonga': 'ts', 'tatar': 'tt', 'twi': 'tw', 'tahitian': 'ty',
        'uighur': 'ug', 'ukrainian': 'uk', 'urdu': 'ur', 'uzbek': 'uz',
        'venda': 've', 'vietnamese': 'vi', 'volapük': 'vo', 'walloon': 'wa',
        'wolof': 'wo', 'xhosa': 'xh', 'yiddish': 'yi', 'yoruba': 'yo',
        'zhuang': 'za', 'chinese': 'zh', 'zulu': 'zu'
    }

    LANGUAGE_VARIATIONS = {
        'mandarin': 'zh',
        'mandarin chinese': 'zh',
        'chinese mandarin': 'zh',
        'simplified chinese': 'zh',
        'traditional chinese': 'zh',
        'brazilian portuguese': 'pt',
        'portuguese brazilian': 'pt',
        'castilian': 'es',
        'castellano': 'es',
        'farsi': 'fa',
        'tagalog': 'tl',
        'standard chinese': 'zh'
    }

    def __init__(self, index_name: str):
        """Initialize the chatbot with necessary components."""
        try:
            # Store Azure settings if available
            self.azure_settings = AZURE_SETTINGS if is_running_in_azure() else {}
            self._initialize_api_keys()
            self._initialize_components(index_name)
            logger.info("Chatbot initialized successfully")
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise

    def _initialize_api_keys(self) -> None:
        """Initialize and validate API keys with minimal side effects for faster startup."""
        required_keys = {
            'PINECONE_API_KEY': os.getenv('PINECONE_API_KEY'),
            'COHERE_API_KEY': os.getenv('COHERE_API_KEY'),
            'TAVILY_API_KEY': os.getenv('TAVILY_API_KEY'),
        }
        optional_keys = {
            'HF_API_TOKEN': os.getenv('HF_API_TOKEN')
        }

        # Validate all required keys exist
        missing_keys = [key for key, value in required_keys.items() if not value]
        if missing_keys:
            raise ValueError(f"Missing required API keys: {', '.join(missing_keys)}")

        # Store keys as instance variables
        for key, value in required_keys.items():
            setattr(self, key, value)
        for key, value in optional_keys.items():
            setattr(self, key, value)

        # Initialize clients (lightweight)
        self.cohere_client = cohere.Client(api_key=self.COHERE_API_KEY)

        # Skip Hugging Face login at startup to speed load; legacy paths will handle if needed
        os.environ.update({
            'PINECONE_API_KEY': self.PINECONE_API_KEY,
            'COHERE_API_KEY': self.COHERE_API_KEY,
            'TAVILY_API_KEY': self.TAVILY_API_KEY
        })

    def _initialize_components(self, index_name: str) -> None:
        """Initialize all required components."""
        logger.info("Initializing components...")
        
        # NEW: Initialize the unified pipeline
        try:
            self.pipeline = ClimateQueryPipeline(index_name=index_name)
            logger.info("✓ ClimateQueryPipeline initialized")
            # One-time prewarm to reduce first-query latency
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule and wait briefly in running loop
                    logger.info("Scheduling pipeline.prewarm() in running loop")
                    loop.create_task(self.pipeline.prewarm())
                else:
                    logger.info("Running pipeline.prewarm() before serving")
                    loop.run_until_complete(self.pipeline.prewarm())
            except Exception as e:
                logger.warning(f"Prewarm skipped: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize ClimateQueryPipeline: {str(e)}")
            # Fall back to individual components (without legacy BERT)
            logger.info("Falling back to individual component initialization...")
            self._initialize_retrieval(index_name)
            self._initialize_language_router()
            self._initialize_nova_flow()
            self._initialize_redis()
        
        self._initialize_langsmith()
        
        # Initialize storage
        self.response_cache = {}
        self.conversation_history = []
        self.feedback_metrics = []

    # Legacy BERT initialization removed

    def _initialize_retrieval(self, index_name: str) -> None:
        """Initialize retrieval components."""
        # Lazy imports to avoid heavy libs at module import
        try:
            import pinecone as pc_legacy
            pc_legacy.init(api_key=self.PINECONE_API_KEY, environment=os.getenv('PINECONE_ENVIRONMENT') or os.getenv('PINECONE_ENV') or 'gcp-starter')
            self.index = pc_legacy.Index(index_name)
            logger.info("Pinecone index initialized via legacy client")
        except Exception:
            from pinecone import Pinecone
            self.pinecone_client = Pinecone(api_key=self.PINECONE_API_KEY)
            self.index = self.pinecone_client.Index(index_name)
            logger.info("Pinecone index initialized via v5 client")

        from FlagEmbedding import BGEM3FlagModel
        self.embed_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=False)

    def _initialize_language_router(self) -> None:
        """Initialize language routing components."""
        self.router = MultilingualRouter()

    def _initialize_nova_flow(self) -> None:
        # Initialize only BedrockModel for translations
        self.nova_model = BedrockModel()

    def _initialize_redis(self):
        """Initialize Redis client with Azure support."""
        try:
            # If Redis client exists and is not closed, no need to reinitialize
            if hasattr(self, 'redis_client') and self.redis_client and not getattr(self.redis_client, '_closed', True):
                return

            # Get Redis configuration from environment variables
            redis_host = os.getenv('REDIS_HOST')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD')
            redis_ssl = os.getenv('REDIS_SSL', '').lower() == 'true'

            # Log Redis connection details
            logger.info(f"Initializing Redis connection to {redis_host or 'localhost'}:{redis_port}")
            
            if not redis_host:
                logger.warning("REDIS_HOST environment variable not set")
            
            # Initialize Redis client with environment variables
            self.redis_client = ClimateCache(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                ssl=redis_ssl,
                expiration=3600  # 1 hour cache expiration
            )
            
            # Test connection without using event loop directly
            try:
                # Simple sync test first
                if hasattr(self.redis_client, 'redis_client'):
                    self.redis_client.redis_client.ping()
                    logger.info(f"✓ Redis connection test successful using sync ping")
                else:
                    logger.warning("Redis client initialized but redis_client attribute not found")
            except Exception as e:
                logger.warning(f"Redis sync test failed: {str(e)}")
                self.redis_client = None
                
        except Exception as e:
            logger.error(f"Redis initialization failed: {str(e)}")
            self.redis_client = None

    async def _check_redis_health(self):
        """Check Redis connection health and attempt to reconnect if needed."""
        if not self.redis_client:
            logger.warning("No Redis client available")
            self._initialize_redis()
            return False
            
        if getattr(self.redis_client, '_closed', True):
            logger.warning("Redis connection is closed, attempting to reinitialize")
            self._initialize_redis()
            return False
            
        # Test connection using ping
        try:
            if hasattr(self.redis_client, 'redis_client'):
                success = await asyncio.to_thread(
                    lambda: self.redis_client.redis_client.ping()
                )
                if success:
                    logger.debug("Redis health check: Connection is healthy")
                    return True
                else:
                    logger.warning("Redis health check: Ping failed")
                    return False
            else:
                logger.warning("Redis client exists but redis_client attribute not found")
                return False
        except Exception as e:
            logger.warning(f"Redis health check failed: {str(e)}")
            # Force reinitialization
            self.redis_client = None
            self._initialize_redis()
            return False

    def get_language_code(self, language_name: str) -> str:
        """Convert language name to code."""
        language_name = language_name.lower().strip()
        
        if language_name in self.LANGUAGE_NAME_TO_CODE:
            return self.LANGUAGE_NAME_TO_CODE[language_name]
            
        if language_name in self.LANGUAGE_VARIATIONS:
            return self.LANGUAGE_VARIATIONS[language_name]
        
        available_languages = sorted(set(list(self.LANGUAGE_NAME_TO_CODE.keys()) + 
                                      list(self.LANGUAGE_VARIATIONS.keys())))
        raise ValueError(
            f"Unsupported language: {language_name}\n" +
            f"Available languages:\n" +
            f"{', '.join(available_languages)}"
        )
        
    @traceable(name="process_input_guards")
    async def process_input_guards(self, query: str) -> Dict[str, Any]:
        """
        Process input validation and topic moderation.
        
        Args:
            query (str): The normalized user query
            
        Returns:
            Dict[str, Any]: Results of input validation with 'passed' flag
        """
        try:
            # Input validation checks
            if not query or len(query.strip()) == 0:
                return {
                    "passed": False,
                    "message": "Please provide a question.",
                    "reason": "empty_query"
                }
                
            # Check for very long queries
            if len(query) > 1000:
                return {
                    "passed": False,
                    "message": "Your question is too long. Please provide a more concise question.",
                    "reason": "too_long"
                }
                
           
            try:
                # Direct topic moderation call 
                topic_results = await topic_moderation(query, self.topic_moderation_pipe)
                
                if not topic_results or not topic_results.get('passed', False):
                    result_reason = topic_results.get('reason', 'not_climate_related')
                    
                    if result_reason == 'harmful_content':
                        return {
                            "passed": False,
                            "message": "I cannot provide information on harmful actions. Please ask a question about climate change.",
                            "reason": "harmful_content",
                            "details": topic_results
                        }
                    elif result_reason == 'misinformation':
                        return {
                            "passed": False,
                            "message": "I provide factual information about climate change based on scientific consensus.",
                            "reason": "misinformation",
                            "details": topic_results
                        }
                    else:
                        return {
                            "passed": False,
                            "message": "Oops! Looks like your question isn't about climate change, which is what I specialize in. But I'd love to help if you've got a climate topic in mind!",
                            "reason": "not_climate_related",
                            "details": topic_results
                        }
                    
                # All checks passed
                return {
                    "passed": True,
                    "message": "Input validation passed",
                    "details": topic_results
                }
                
            except Exception as e:
                logger.error(f"Error in topic moderation: {str(e)}")
                # In case of errors, we allow the query to proceed
                return {
                    "passed": True,
                    "message": "Input validation passed with errors in moderation",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error in process_input_guards: {str(e)}")
            # Default to allowing in case of errors
            return {
                "passed": True,
                "message": "Input validation passed with errors",
                "error": str(e)
            }

    @traceable(name="unified_pipeline_processing")
    async def process_query_with_pipeline(
        self,
        query: str,
        language_name: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process query using the new unified pipeline.
        
        This is the new preferred method that uses ClimateQueryPipeline.
        """
        if hasattr(self, 'pipeline'):
            logger.info("Using ClimateQueryPipeline for processing")
            return await self.pipeline.process_query(
                query=query,
                language_name=language_name,
                conversation_history=conversation_history
            )
        else:
            logger.info("Pipeline not available, falling back to legacy processing")
            return await self.process_query(query, language_name, conversation_history)

    async def _process_query_internal(
        self,
        query: str,
        language_name: str,
        run_manager=None
    ) -> Dict[str, Any]:
        """Backwards compatibility method for QueryProcessingChain."""
        return await self.process_query(query, language_name, [])

    @traceable(name="main_query_processing")
    async def process_query(
            self,
            query: str,
            language_name: str,
            conversation_history: List[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Process a query through the complete pipeline.
            
            Args:
                query (str): The user's query
                language_name (str): The language name (e.g., "english", "spanish")
                conversation_history (List[Dict[str, Any]], optional): Previous conversation turns
                
            Returns:
                Dict[str, Any]: The processing results including the response
            """
            
            # NEW: Try to use the unified pipeline first
            if hasattr(self, 'pipeline') and self.pipeline:
                try:
                    logger.info("🚀 Using ClimateQueryPipeline for processing")
                    return await self.pipeline.process_query(
                        query=query,
                        language_name=language_name,
                        conversation_history=conversation_history
                    )
                except Exception as e:
                    logger.warning(f"Pipeline processing failed, falling back to legacy: {str(e)}")
            
            # FALLBACK: Legacy processing logic
            logger.info("Using legacy processing pipeline")
            try:
                start_time = time.time()
                step_times = {}
                pipeline_trace = None
                
                # Initialize conversation history if None
                if conversation_history is None:
                    conversation_history = []
                
                # Immediate query normalization for cache check
                norm_query = query.lower().strip()
                language_code = self.get_language_code(language_name)
                
                # Create a cache key that doesn't include the conversation history
                # We only cache based on the current query for consistent responses
                cache_key = f"{language_code}:{norm_query}"
                
                # Ensure Redis connection is available immediately
                if not self.redis_client or getattr(self.redis_client, '_closed', True):
                    logger.info("Redis client not available, initializing...")
                    self._initialize_redis()
                
                # Check cache before starting the pipeline
                if self.redis_client and not getattr(self.redis_client, '_closed', False):
                    try:
                        logger.info(f"📝 Checking cache for key: '{cache_key}'")
                        cached_result = await self.redis_client.get(cache_key)
                        if cached_result:
                            cache_time = time.time() - start_time
                            logger.info(f"✨ Cache hit - returning cached response")
                            # Create current turn with cached response for conversation history
                            current_turn = {
                                "query": norm_query,
                                "response": cached_result.get('response'),
                                "language_code": language_code,
                                "language_name": language_name,
                                "timestamp": time.time()
                            }
                            return {
                                "success": True,
                                "language_code": language_code,
                                "query": norm_query,
                                "response": cached_result.get('response'),
                                "citations": cached_result.get('citations', []),
                                "faithfulness_score": cached_result.get('faithfulness_score', 0.8),
                                "processing_time": cache_time,
                                "cache_hit": True,
                                "step_times": {"cache_lookup": cache_time},
                                "current_turn": current_turn  # Add current turn for conversation history tracking
                            }
                    except Exception as e:
                        logger.warning(f"⚠️ Cache check failed: {str(e)}")
                
                # Initialize pipeline variables
                step_times = {}
                translated_query = None
                query_versions = {}
                # Start pipeline with all query processing in one block
                with trace(name="query_processing") as process_trace:
                    # Initialize timing
                    step_times = {}
                    norm_start = time.time()
                    
                    # First normalize the query in original language
                    norm_query = query.lower().strip()
                    
                    # Add translation to English
                    if language_code != 'en':
                        english_query = await self.nova_model.nova_translation(norm_query, language_name, 'english')
                        logger.info("✓ Query translated to English for processing")
                    else:
                        english_query = norm_query
                        
                    # Store both versions for reference
                    query_versions = {
                        'original_normalized': norm_query,
                        'english': english_query
                    }
                    step_times['normalization'] = time.time() - norm_start
                    
                    # Topic moderation check using English query - now passing the nova_model for LLM-based detection
                    validation_start = time.time()
                    # Pass conversation history to topic_moderation along with nova_model
                    # Use lightweight, LLM-based moderation without legacy BERT pipeline
                    topic_results = await topic_moderation(
                        query=english_query,
                        moderation_pipe=None,
                        conversation_history=conversation_history,
                        nova_model=self.nova_model
                    )
                    step_times['validation'] = time.time() - validation_start
                    
                    if not topic_results.get('passed', False):
                        total_time = time.time() - start_time
                        return {
                            "success": False,
                            "message": topic_results.get('message', "Oops! Looks like your question isn't about climate change, which is what I specialize in. But I'd love to help if you've got a climate topic in mind!"),
                            "validation_result": topic_results,
                            "processing_time": total_time,
                            "step_times": step_times,
                            "trace_id": getattr(pipeline_trace, 'id', None)
                        }
                    logger.info("🔍 Input validation passed")
                    # Language routing with English query
                    with trace(name="language_routing") as route_trace:
                        route_start = time.time()
                        logger.info("🌐 Processing language routing...")
                        route_result = await self.router.route_query(
                            query=english_query,
                            language_code=language_code,
                            language_name=language_name,
                            translation=self.nova_model.nova_translation 
                        )
                        step_times['routing'] = time.time() - route_start
                        
                        if not route_result['should_proceed']:
                            total_time = time.time() - start_time
                            return {
                                "success": False,
                                "message": route_result['routing_info']['message'],
                                "processing_time": total_time,
                                "step_times": step_times,
                                "trace_id": pipeline_trace.id
                            }
                        logger.info("🌐 Language routing complete")
                    # Document retrieval chain - Use English query for retrieval
                    with trace(name="document_retrieval") as retrieval_trace:
                        retrieval_start = time.time()
                        try:
                            logger.info("📚 Starting retrieval and reranking...")
                            
                            # Enhanced query for better retrieval with follow-up questions
                            retrieval_query = english_query
                            
                            # Determine if current query is a follow-up and enhance it with context if needed
                            if conversation_history and len(conversation_history) > 0:
                                # Use the improved follow-up detection with LLM
                                follow_up_result = await check_follow_up_with_llm(
                                    query=english_query, 
                                    conversation_history=conversation_history,
                                    nova_model=self.nova_model
                                )
                                
                                is_follow_up = follow_up_result.get('is_follow_up', False)
                                
                                if is_follow_up:
                                    # For follow-up questions, create an enhanced retrieval query that includes
                                    # important context from the conversation history
                                    
                                    # Collect recent conversation context to help the LLM understand the topic
                                    context_turns = conversation_history[-min(3, len(conversation_history)):]
                                    context_text = ""
                                    for turn in context_turns:
                                        context_text += f"{turn.get('query', '')} {turn.get('response', '')} "
                                    
                                    # Use LLM to extract key topics from the conversation context
                                    try:
                                        topic_prompt = f"""Based on this conversation history and current query, extract 3-5 key 
                                        topic keywords that would help retrieve relevant information:
                                        
                                        Conversation history: {context_text}
                                        Current query: {english_query}
                                        
                                        Return only the most important keywords separated by commas. The keywords should help
                                        retrieve relevant climate-related information for the current query.
                                        """
                                        
                                        topic_result = await self.nova_model.nova_content_generation(
                                            prompt=topic_prompt,
                                            system_message="Extract key topics from text. Be brief and precise."
                                        )
                                        
                                        # Use these extracted topics to enhance the current query
                                        if topic_result and len(topic_result.strip()) > 0:
                                            # Create a retrieval query that includes context from the conversation
                                            retrieval_query = f"{english_query} {topic_result}"
                                            logger.info(f"Enhanced retrieval query with conversation context: '{retrieval_query}'")
                                    except Exception as topic_err:
                                        logger.warning(f"Error extracting topics from conversation: {str(topic_err)}")
                            
                            # Document retrieval includes hybrid search and reranking
                            reranked_docs = await get_documents(retrieval_query, self.index, self.embed_model, self.cohere_client)
                            step_times['retrieval'] = time.time() - retrieval_start
                            logger.info(f"📚 Retrieved and reranked {len(reranked_docs)} documents")
                        except Exception as e:
                            logger.error(f"📚 Error in retrieval process: {str(e)}")
                            raise
                    # 7. Response generation chain - Use English query and include conversation history
                    with trace(name="response_generation") as gen_trace:
                        generation_start = time.time()
                        try:
                            logger.info("✍️ Starting response generation with conversation history...")
                            
                            # Format conversation history for the model
                            formatted_history = []
                            if conversation_history and len(conversation_history) > 0:
                                logger.info(f"Processing conversation history with {len(conversation_history)} previous turns")
                                for turn in conversation_history:
                                    # Translate history items if needed
                                    if language_code != 'en' and turn.get('language_code') != 'en':
                                        user_msg = await self.nova_model.nova_translation(
                                            turn.get('query', ''), 
                                            turn.get('language_name', language_name), 
                                            'english'
                                        )
                                        assistant_msg = await self.nova_model.nova_translation(
                                            turn.get('response', ''), 
                                            turn.get('language_name', language_name), 
                                            'english'
                                        )
                                    else:
                                        user_msg = turn.get('query', '')
                                        assistant_msg = turn.get('response', '')
                                    
                                    # Add properly formatted conversation turns
                                    formatted_history.append({"role": "user", "content": user_msg})
                                    formatted_history.append({"role": "assistant", "content": assistant_msg})
                                
                                logger.info(f"Formatted {len(formatted_history)//2} conversation turns for model context")
                                
                                # Log a sample of the conversation history for debugging
                                if formatted_history:
                                    logger.debug(f"Sample conversation turn: {formatted_history[:2]}")
                            
                            # Call nova_chat with conversation history
                            response, citations = await generate_chat_response(
                                english_query, 
                                reranked_docs, 
                                self.nova_model,
                                conversation_history=formatted_history
                            )
                            step_times['generation'] = time.time() - generation_start
                            logger.info("✍️ Response generation complete")
                        except Exception as e:
                            logger.error(f"✍️ Error in response generation: {str(e)}")
                            raise
                    # 8. Quality checks chain - Using English query and response
                    with trace(name="quality_checks") as quality_trace:
                        quality_start = time.time()
                        logger.info("✔️ Starting quality checks...")
                        try:
                            contexts = extract_contexts(reranked_docs, max_contexts=5)
                            # For hallucination check - we already have english_query
                            with trace(name="hallucination_check") as hall_trace:
                                faithfulness_score = await check_hallucination(
                                    question=english_query,
                                    answer=response,  # Response is already in English at this point
                                    contexts=contexts,
                                    cohere_api_key=self.COHERE_API_KEY,
                                    threshold=0.7  # Set proper threshold for faithfulness
                                )
                            
                            # Evaluate against threshold and log detailed results
                            evaluation = evaluate_faithfulness_threshold(faithfulness_score, threshold=0.7)
                            
                            step_times['quality_check'] = time.time() - quality_start
                            logger.info(f"✔️ Hallucination check complete - Score: {faithfulness_score:.3f}")
                            logger.info(f"✔️ Assessment: {evaluation['assessment']}")
                            logger.info(f"✔️ Recommendation: {evaluation['recommendation']}")
                            
                            # If faithfulness is too low, add warning
                            if not evaluation['is_faithful']:
                                logger.warning(f"Nova response faithfulness below threshold: {faithfulness_score:.3f} < 0.7")
                            
                            # Fallback to web search if needed
                            if faithfulness_score < 0.1:
                                with trace(name="fallback_search") as fallback_trace:
                                    fallback_start = time.time()
                                    logger.warning("Low faithfulness score - attempting fallback")
                                    fallback_response, fallback_citations, fallback_score = await self._try_tavily_fallback(
                                        query=norm_query,  # Use normalized query for display
                                        english_query=english_query,  # Use English for processing
                                        language_name=language_name
                                    )
                                    step_times['fallback'] = time.time() - fallback_start
                                    if fallback_score > faithfulness_score:
                                        response = fallback_response
                                        citations = fallback_citations
                                        faithfulness_score = fallback_score
                        except Exception as e:
                            logger.error(f"✔️ Error in quality checks: {str(e)}")
                            faithfulness_score = 0.0
                    # 9. Final translation if needed - translate from English to target language
                    with trace(name="final_translation") as trans_trace:
                        if route_result['routing_info']['needs_translation']:
                            translation_start = time.time()
                            logger.info(f"🌐 Translating response from English to {language_name}")
                            response = await self.nova_model.nova_translation(response, 'english', language_name)
                            step_times['translation'] = time.time() - translation_start
                            logger.info("🌐 Translation complete")
                    # 10. Store results - Use original normalized query for caching
                    with trace(name="result_storage") as storage_trace:
                        total_time = time.time() - start_time
                        
                        # Create a new conversation turn to return and store
                        current_turn = {
                            "query": norm_query,
                            "response": response,
                            "language_code": language_code,
                            "language_name": language_name,
                            "timestamp": time.time()
                        }
                        
                        await self._store_results(
                            query=norm_query,  # Use normalized query for storage
                            response=response,
                            language_code=language_code,
                            language_name=language_name,
                            citations=citations,
                            faithfulness_score=faithfulness_score,
                            processing_time=total_time,
                            route_result=route_result
                        )
                        logger.info(f"Processing time: {total_time} seconds")
                        logger.info("✨ Processing complete!")
                        return {
                            "success": True,
                            "language_code": language_code,
                            "language_name": language_name,
                            "query": norm_query,
                            "response": response,
                            "citations": citations,
                            "faithfulness_score": faithfulness_score,
                            "processing_time": total_time,
                            "step_times": step_times,
                            "cache_hit": False,
                            "trace_id": getattr(pipeline_trace, 'id', None),
                            "current_turn": current_turn
                        }
                    
            except Exception as e:
                logger.error(f"❌ Error processing query: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "message": f"Error processing query: {str(e)}",
                    "trace_id": getattr(pipeline_trace, 'id', None) if 'pipeline_trace' in locals() else None
                }

    async def _try_tavily_fallback(self, query: str, english_query: str, language_name: str) -> Tuple[Optional[str], Optional[List], float]:
        """
        Attempt to get a response using Tavily search when primary response fails verification.
        """
        try:
            # Lazy import to avoid cost until needed
            from langchain_community.tools.tavily_search import TavilySearchResults
            logger.info("Attempting Tavily fallback search")
            tavily_search = TavilySearchResults()

            # Perform web search
            search_results = await tavily_search.ainvoke(query)
            
            if not search_results:
                logger.warning("No results from Tavily search")
                return None, None, 0.0
                
            # Format documents for nova_chat
            documents_for_nova = []
            for result in search_results:
                document = {
                        'title': result.get('url', ''),
                        'url': result.get('url', ''),
                        'content': result.get('content', '')
                    }
                documents_for_nova.append(document)
            
            # Generate new response with Tavily results
            description = """Please provide accurate information based on the search results. Always cite your sources. Ensure strict factual accuracy"""
            fallback_response, fallback_citations = await generate_chat_response(
                query=query, 
                documents=documents_for_nova, 
                model=self.nova_model,  # Fixed parameter name
                description=description
            )
            
            # Verify fallback response
            web_contexts = [f"{result.get('title', '')}: {result.get('content', '')}" for result in search_results]
            
            # Translate if needed
            if query != english_query:
                processed_response = await self.nova_model.nova_translation(fallback_response, language_name, 'english')
                processed_context = await self.nova_model.nova_translation(web_contexts, language_name, 'english')
            else:
                processed_response = fallback_response
                processed_context = web_contexts
            
            # Check faithfulness with proper threshold
            fallback_score = await check_hallucination(
                question=english_query,
                answer=processed_response,
                contexts=processed_context,
                cohere_api_key=self.COHERE_API_KEY,
                threshold=0.7
            )
            
            # Evaluate and log fallback faithfulness
            evaluation = evaluate_faithfulness_threshold(fallback_score, threshold=0.7)
            logger.info(f"✔️ Fallback faithfulness: {fallback_score:.3f} ({evaluation['assessment']})")
            
            return fallback_response, fallback_citations, fallback_score
            
        except Exception as e:
            logger.error(f"Error in Tavily fallback: {str(e)}")
            return None, None, 0.0

    async def _store_results(
        self,
        query: str,
        response: str,
        language_code: str,
        language_name: str,
        citations: List[Any],
        faithfulness_score: float,
        processing_time: float,
        route_result: Dict[str, Any]
    ) -> None:
        """Store query results in cache and update metrics."""
        try:
            # 1. Store in Redis cache first
            cache_key = f"{language_code}:{query.lower().strip()}"
            
            if self.redis_client and not getattr(self.redis_client, '_closed', False):
                try:
                    logger.info(f"📝 Storing results in Redis with key: '{cache_key}'")
                    
                    # Prepare cache data
                    cache_data = {
                        "response": response,
                        "citations": citations,
                        "faithfulness_score": faithfulness_score,
                        "metadata": {
                            "cached_at": time.time(),
                            "language_code": language_code,
                            "language_name": language_name,
                            "processing_time": processing_time,
                            "required_translation": route_result['routing_info']['needs_translation']
                        }
                    }
                    
                    # Try to store in Redis
                    success = await self.redis_client.set(cache_key, cache_data)
                    if success:
                        logger.info(f"✨ Response cached successfully in Redis with key: '{cache_key}'")
                    else:
                        logger.warning(f"⚠️ Failed to cache response in Redis for key: '{cache_key}'")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cache in Redis: {str(e)}")
            else:
                logger.warning(f"⚠️ Redis client not available for caching key: '{cache_key}'")
            
            # 2. Store in memory cache as backup
            self.response_cache[cache_key] = {
                "response": response,
                "citations": citations,
                "faithfulness_score": faithfulness_score,
                "cached_at": time.time()
            }
            logger.debug(f"✨ Response cached in memory with key: '{cache_key}'")
            
            # 3. Update conversation history
            self.conversation_history.append({
                "query": query,
                "response": response,
                "language_code": language_code,
                "language_name": language_name,
                "faithfulness_score": faithfulness_score,
                "timestamp": time.time()
            })
            
            # 4. Store metrics
            self.feedback_metrics.append({
                "language": language_code,
                "processing_time": processing_time,
                "required_translation": route_result['routing_info']['needs_translation'],
                "faithfulness_score": faithfulness_score,
                "cached": False,
                "timestamp": time.time()
            })
            
            logger.debug(f"Results stored successfully for query: {query[:50]}...")
            logger.info(f"Processing time: {processing_time} seconds")
        except Exception as e:
            logger.error(f"Error storing results: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        cleanup_tasks = []
        cleanup_errors = []

        # Close Redis connection if it exists
        if hasattr(self, 'redis_client') and self.redis_client is not None:
            try:
                if not getattr(self.redis_client, '_closed', False):
                    cleanup_tasks.append(self.redis_client.close())
            except Exception as e:
                cleanup_errors.append(f"Redis cleanup error: {str(e)}")
                logger.error(f"Error closing Redis connection: {str(e)}")

        # Wait for all cleanup tasks to complete
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks)
            except Exception as e:
                cleanup_errors.append(f"Cleanup tasks error: {str(e)}")
                logger.error(f"Error in cleanup tasks: {str(e)}")

        # Close Bedrock async client if present
        try:
            if hasattr(self, 'nova_model') and self.nova_model and hasattr(self.nova_model, 'close'):
                await self.nova_model.close()
        except Exception as e:
            cleanup_errors.append(f"Bedrock close error: {str(e)}")
            logger.error(f"Error closing Bedrock async client: {str(e)}")

        # Reset instance variables
        self.redis_client = None
        self.response_cache = {}
        self.conversation_history = []
        self.feedback_metrics = []

        if cleanup_errors:
            logger.error(f"Cleanup completed with errors: {', '.join(cleanup_errors)}")
        else:
            logger.info("Cleanup completed successfully")

    def _initialize_langsmith(self) -> None:
        """Initialize LangSmith for tracing."""
        try:
            # Set environment variables first to ensure proper tracing setup
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
            os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "climate-chat-production")
            
            # Initialize LangSmith client
            self.langsmith_client = Client()
            
            # Verify initialization
            if not self.langsmith_client:
                raise ValueError("Failed to initialize LangSmith client")
                
            logger.info(f"LangSmith tracing initialized successfully for project: {os.getenv('LANGSMITH_PROJECT')}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangSmith tracing: {str(e)}")
            self.langsmith_client = None

async def main() -> None:
    """Main entry point for the climate chatbot application."""
    try:
        # Validate command line arguments
        if len(sys.argv) < 2:
            print("Usage: python main.py <index_name>")
            print("Example: python main.py climate-change-adaptation-index-10-24-prod")
            sys.exit(1)
            
        index_name = sys.argv[1]
        
        # Initialize chatbot
        print("\nInitializing Climate Chatbot...")
        chatbot = MultilingualClimateChatbot(index_name)
        print("✓ Initialization complete\n")
        
        # Print welcome message
        print("Welcome to the Multilingual Climate Chatbot!")
        print("Available languages:")
        languages = sorted(set(list(chatbot.LANGUAGE_NAME_TO_CODE.keys()) + 
                             list(chatbot.LANGUAGE_VARIATIONS.keys())))
        
        # Print languages in columns
        col_width = 20
        num_cols = 4
        for i in range(0, len(languages), num_cols):  
            row = languages[i:i + num_cols]
            print("".join(lang.ljust(col_width) for lang in row))
            
        # Get language choice once at the start
        while True:
            language_name = input("\nPlease select your language for this session: ").strip()
            if language_name:
                try:
                    # Validate language selection
                    chatbot.get_language_code(language_name)
                    print(f"\nLanguage set to: {language_name}")
                    break
                except ValueError as e:
                    print(f"\nError: {str(e)}")
                    continue

        print("\nType 'quit' to exit, 'language' to see your current language setting\n")
        
        # Initialize conversation history for the CLI session
        conversation_history = []

        # Main interaction loop
        while True:
            try:
                # Get query
                query = input("\nEnter your question: ").strip()
                if not query:
                    print("Please enter a question.")
                    continue
                    
                if query.lower() == 'quit':
                    print("\nThank you for using the Climate Chatbot!")
                    break
                    
                if query.lower() == 'languages':
                    print(f"\nCurrent language: {language_name}")
                    continue

                print("\nProcessing your query...")
                
                # Process query with conversation history
                result = await chatbot.process_query(
                    query=query,
                    language_name=language_name,
                    conversation_history=conversation_history
                )
                
                # Display results
                if result.get('success', False):
                    print("\nResponse:", result.get('response', 'No response generated'))
                    
                    if result.get('citations', []):
                        print("\nSources:")
                        for citation in result.get('citations'):
                            print(f"- {citation}")
                            
                    print(f"\nFaithfulness Score: {result.get('faithfulness_score', 0.0):.2f}")
                    
                    # Store the current turn in conversation history for context in future queries
                    if result.get('current_turn'):
                        conversation_history.append(result.get('current_turn'))
                        # Keep conversation history to a reasonable size (last 5 turns)
                        if len(conversation_history) > 5:
                            conversation_history = conversation_history[-5:]
                else:
                    print("\nError:", result.get('message', 'An unknown error occurred'))
                    
                print("\n" + "-"*50)  # Separator line
                    
            except KeyboardInterrupt as e:
                print("\n\nExiting gracefully...")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again.")
                
    except KeyboardInterrupt as e:
        print("\n\nExiting gracefully...")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        raise
    finally:
        if 'chatbot' in locals():
            try:
                await chatbot.cleanup()
                print("\nResources cleaned up successfully")
            except Exception as e:
                print(f"\nError during cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt as e:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"\nProgram terminated due to error: {str(e)}")
        sys.exit(1)