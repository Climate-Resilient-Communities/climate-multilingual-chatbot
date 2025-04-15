import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import logging
import time
import warnings
import json

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
os.environ['COHERE_API_KEY'] = os.getenv('COHERE_API_KEY')
os.environ['LANGCHAIN_TRACING_V2'] = os.getenv('LANGCHAIN_TRACING_V2')
os.environ['LANGCHAIN_API_KEY'] = os.getenv('LANGCHAIN_API_KEY')
os.environ['LANGCHAIN_PROJECT'] = os.getenv('LANGSMITH_PROJECT', "climate-chat-production")
os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY')

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
import ray
import cohere
from huggingface_hub import login
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline
)
from pinecone import Pinecone
from FlagEmbedding import BGEM3FlagModel
from langsmith import Client, traceable, trace
from langchain_community.tools.tavily_search import TavilySearchResults

# Local imports
from src.models.redis_cache import ClimateCache
from src.models.nova_flow import BedrockModel
from src.models.gen_response_nova import nova_chat
from src.models.query_routing import MultilingualRouter
from src.models.input_guardrail import topic_moderation
from src.models.retrieval import get_documents
from src.models.hallucination_guard import extract_contexts, check_hallucination
from src.data.config.azure_config import get_azure_settings

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
        'afrikaans': 'af', 'amharic': 'am', 'arabic': 'ar', 'azerbaijani': 'az',
        'belarusian': 'be', 'bengali': 'bn', 'bulgarian': 'bg', 'catalan': 'ca',
        'cebuano': 'ceb', 'czech': 'cs', 'welsh': 'cy', 'danish': 'da',
        'german': 'de', 'greek': 'el', 'english': 'en', 'esperanto': 'eo',
        'spanish': 'es', 'estonian': 'et', 'basque': 'eu', 'persian': 'fa',
        'finnish': 'fi', 'filipino': 'fil', 'french': 'fr', 'western frisian': 'fy',
        'irish': 'ga', 'scots gaelic': 'gd', 'galician': 'gl', 'gujarati': 'gu',
        'hausa': 'ha', 'hebrew': 'he', 'hindi': 'hi', 'croatian': 'hr',
        'hungarian': 'hu', 'armenian': 'hy', 'indonesian': 'id', 'igbo': 'ig',
        'icelandic': 'is', 'italian': 'it', 'japanese': 'ja', 'javanese': 'jv',
        'georgian': 'ka', 'kazakh': 'kk', 'khmer': 'km', 'kannada': 'kn',
        'korean': 'ko', 'kurdish': 'ku', 'kyrgyz': 'ky', 'latin': 'la',
        'luxembourgish': 'lb', 'lao': 'lo', 'lithuanian': 'lt', 'latvian': 'lv',
        'malagasy': 'mg', 'macedonian': 'mk', 'malayalam': 'ml', 'mongolian': 'mn',
        'marathi': 'mr', 'malay': 'ms', 'maltese': 'mt', 'burmese': 'my',
        'nepali': 'ne', 'dutch': 'nl', 'norwegian': 'no', 'nyanja': 'ny',
        'odia': 'or', 'punjabi': 'pa', 'polish': 'pl', 'pashto': 'ps',
        'portuguese': 'pt', 'romanian': 'ro', 'russian': 'ru', 'sindhi': 'sd',
        'sinhala': 'si', 'slovak': 'sk', 'slovenian': 'sl', 'samoan': 'sm',
        'shona': 'sn', 'somali': 'so', 'albanian': 'sq', 'serbian': 'sr',
        'sesotho': 'st', 'sundanese': 'su', 'swedish': 'sv', 'swahili': 'sw',
        'tamil': 'ta', 'telugu': 'te', 'tajik': 'tg', 'thai': 'th', 'turkish': 'tr',
        'ukrainian': 'uk', 'urdu': 'ur', 'uzbek': 'uz', 'vietnamese': 'vi',
        'xhosa': 'xh', 'yiddish': 'yi', 'yoruba': 'yo', 'chinese': 'zh',
        'zulu': 'zu'
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
        'tagalog': 'fil',
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
        """Initialize and validate API keys."""
        required_keys = {
            'PINECONE_API_KEY': os.getenv('PINECONE_API_KEY'),
            'COHERE_API_KEY': os.getenv('COHERE_API_KEY'),
            'TAVILY_API_KEY': os.getenv('TAVILY_API_KEY'),
            'HF_API_TOKEN': os.getenv('HF_API_TOKEN')
        }

        # Validate all required keys exist
        missing_keys = [key for key, value in required_keys.items() if not value]
        if (missing_keys):
            raise ValueError(f"Missing required API keys: {', '.join(missing_keys)}")
        # Store keys as instance variables
        for key, value in required_keys.items():
            setattr(self, key, value)

        # Initialize clients
        self.cohere_client = cohere.Client(api_key=self.COHERE_API_KEY)
        
        # Login to Hugging Face - make it optional in Azure environments
        try:
            if is_running_in_azure():
                logger.info("Running in Azure - skipping Hugging Face git credential setup")
                # Use simple login without git credential helper
                login(token=self.HF_API_TOKEN, add_to_git_credential=False)
            else:
                # Regular login with git credential helper
                login(token=self.HF_API_TOKEN, add_to_git_credential=True)
        except Exception as e:
            logger.warning(f"Hugging Face login warning: {str(e)}")
            logger.info("Continuing without HF login - some features may be limited")

        # Set environment variables
        os.environ.update({
            'PINECONE_API_KEY': self.PINECONE_API_KEY,
            'COHERE_API_KEY': self.COHERE_API_KEY,
            'TAVILY_API_KEY': self.TAVILY_API_KEY
        })

    def _initialize_components(self, index_name: str) -> None:
        """Initialize all required components."""
        logger.info("Initializing components...")
        self._initialize_models()
        self._initialize_retrieval(index_name)
        self._initialize_language_router()
        self._initialize_nova_flow()
        self._initialize_redis()
        self._initialize_langsmith()
        
        # Initialize storage
        self.response_cache = {}
        self.conversation_history = []
        self.feedback_metrics = []

    def _initialize_models(self) -> None:
        """Initialize all ML models."""
        try:
            # Initialize ClimateBERT for topic moderation
            model_name = "climatebert/distilroberta-base-climate-detector"
            
            # Check for models in Azure App Service path first
            azure_model_path = Path("/home/site/wwwroot/models/climatebert")
            local_model_path = Path(__file__).resolve().parent.parent / "models" / "climatebert"
            
            # Verify directory existence and contents
            logger.info("Checking model directories...")
            
            # Debug Azure environment
            if is_running_in_azure():
                try:
                    # Set Hugging Face cache dir explicitly to a known writable location
                    os.environ["HF_HOME"] = "/tmp/huggingface"
                    os.environ["TRANSFORMERS_CACHE"] = "/tmp/huggingface/transformers"
                    logger.info(f"Set HF_HOME to {os.environ.get('HF_HOME')}")
                    
                    # Check Azure directories
                    if azure_model_path.exists() and azure_model_path.is_dir():
                        contents = list(azure_model_path.iterdir())
                        logger.info(f"Azure model directory exists with {len(contents)} items")
                        if contents:
                            file_names = [item.name for item in contents[:5]]
                            logger.info(f"First few files: {', '.join(file_names)}")
                    else:
                        logger.warning(f"Azure model path {azure_model_path} does not exist or is not a directory")
                        
                        # Check if models dir exists
                        parent_dir = Path("/home/site/wwwroot/models")
                        if parent_dir.exists() and parent_dir.is_dir():
                            logger.info(f"Parent models directory exists with contents: {list(parent_dir.iterdir())}")
                        else:
                            logger.warning("Parent models directory does not exist")
                            
                            # Check wwwroot
                            wwwroot_dir = Path("/home/site/wwwroot")
                            if wwwroot_dir.exists() and wwwroot_dir.is_dir():
                                wwwroot_contents = list(wwwroot_dir.iterdir())
                                logger.info(f"wwwroot directory exists with {len(wwwroot_contents)} items")
                                if wwwroot_contents:
                                    logger.info(f"First few wwwroot items: {', '.join([item.name for item in wwwroot_contents[:5]])}")
                except Exception as e:
                    logger.error(f"Error checking Azure directories: {str(e)}")
            
            # Try Azure path first, then local path, then fallback to HF download
            if is_running_in_azure() and azure_model_path.exists() and azure_model_path.is_dir():
                logger.info(f"Loading ClimateBERT model from Azure path: {azure_model_path}")
                try:
                    # Set offline mode to force local file usage
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    self.climatebert_model = AutoModelForSequenceClassification.from_pretrained(
                        str(azure_model_path),
                        local_files_only=True
                    )
                    self.climatebert_tokenizer = AutoTokenizer.from_pretrained(
                        str(azure_model_path),
                        max_length=512,
                        local_files_only=True
                    )
                    os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                    logger.info("✓ Successfully loaded ClimateBERT from Azure directory")
                except Exception as azure_err:
                    os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                    logger.warning(f"Failed to load from Azure path: {str(azure_err)}")
                    logger.info("Falling back to local directory...")
                    
                    # Try alternate Azure model path
                    alt_azure_path = Path("/home/site/wwwroot/models")
                    try:
                        # Find any model directories under models/
                        model_dirs = [d for d in alt_azure_path.iterdir() if d.is_dir()]
                        if model_dirs:
                            logger.info(f"Found alternate model directories: {[d.name for d in model_dirs]}")
                            # Try each directory
                            for model_dir in model_dirs:
                                try:
                                    logger.info(f"Attempting to load from {model_dir}")
                                    os.environ["HF_HUB_OFFLINE"] = "1"
                                    self.climatebert_model = AutoModelForSequenceClassification.from_pretrained(
                                        str(model_dir),
                                        local_files_only=True
                                    )
                                    self.climatebert_tokenizer = AutoTokenizer.from_pretrained(
                                        str(model_dir),
                                        max_length=512,
                                        local_files_only=True
                                    )
                                    os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                                    logger.info(f"✓ Successfully loaded from alternate directory {model_dir}")
                                    break
                                except Exception as alt_err:
                                    os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                                    logger.warning(f"Failed to load from {model_dir}: {alt_err}")
                    except Exception as search_err:
                        logger.warning(f"Error searching for alternate model directories: {search_err}")
            
            # If model still not loaded, try local path
            if not hasattr(self, 'climatebert_model') and local_model_path.exists() and local_model_path.is_dir():
                logger.info(f"Loading ClimateBERT model from local path: {local_model_path}")
                try:
                    # Set offline mode to force local file usage
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    self.climatebert_model = AutoModelForSequenceClassification.from_pretrained(
                        str(local_model_path),
                        local_files_only=True
                    )
                    self.climatebert_tokenizer = AutoTokenizer.from_pretrained(
                        str(local_model_path),
                        max_length=512,
                        local_files_only=True
                    )
                    os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                    logger.info("✓ Successfully loaded ClimateBERT from local directory")
                except Exception as local_err:
                    os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                    logger.warning(f"Failed to load from local path: {str(local_err)}")
            
            # If model still not loaded, try downloading
            if not hasattr(self, 'climatebert_model'):
                logger.info(f"Local model not found. Downloading from Hugging Face.")
                self.climatebert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.climatebert_tokenizer = AutoTokenizer.from_pretrained(model_name, max_length=512)
            
            # Set up pipeline
            device = 0 if torch.cuda.is_available() else -1 
            self.topic_moderation_pipe = pipeline(
                "text-classification",
                model=self.climatebert_model,
                tokenizer=self.climatebert_tokenizer,
                device=device,
                truncation=True,
                max_length=512
            )
            logger.info("✓ Topic moderation pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing models: {str(e)}")
            raise

    def _initialize_retrieval(self, index_name: str) -> None:
        """Initialize retrieval components."""
        self.pinecone_client = Pinecone(api_key=self.PINECONE_API_KEY)
        self.index = self.pinecone_client.Index(index_name)
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
            if not query or len(query.strip()) < 3:
                return {
                    "passed": False,
                    "message": "Please provide a more detailed question.",
                    "reason": "too_short"
                }
                
            # Check for very long queries
            if len(query) > 1000:
                return {
                    "passed": False,
                    "message": "Your question is too long. Please provide a more concise question.",
                    "reason": "too_long"
                }
                
            # Apply topic moderation using Ray remote
            try:
                # Direct topic moderation call instead of using Ray
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
                            "message": "I apologize, but I can only help with climate-related questions.",
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

    @traceable(name="main_query_processing")
    async def process_query(
            self,
            query: str,
            language_name: str
        ) -> Dict[str, Any]:
            """Process a query through the complete pipeline."""
            try:
                start_time = time.time()
                step_times = {}
                pipeline_trace = None
                
                # Immediate query normalization for cache check
                norm_query = query.lower().strip()
                language_code = self.get_language_code(language_name)
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
                            return {
                                "success": True,
                                "language_code": language_code,
                                "query": norm_query,
                                "response": cached_result.get('response'),
                                "citations": cached_result.get('citations', []),
                                "faithfulness_score": cached_result.get('faithfulness_score', 0.8),
                                "processing_time": cache_time,
                                "cache_hit": True,
                                "step_times": {"cache_lookup": cache_time}
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
                    
                    # Topic moderation check using English query
                    validation_start = time.time()
                    topic_results = await topic_moderation(english_query, self.topic_moderation_pipe)
                    step_times['validation'] = time.time() - validation_start
                    
                    if not topic_results.get('passed', False):
                        total_time = time.time() - start_time
                        return {
                            "success": False,
                            "message": topic_results.get('reason', "I apologize, but I can only help with climate-related questions."),
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

                    # 6. Document retrieval chain - Use English query for retrieval
                    with trace(name="document_retrieval") as retrieval_trace:
                        retrieval_start = time.time()
                        try:
                            logger.info("📚 Starting retrieval and reranking...")
                            # Document retrieval includes hybrid search and reranking
                            reranked_docs = await get_documents(english_query, self.index, self.embed_model, self.cohere_client)
                            step_times['retrieval'] = time.time() - retrieval_start
                            logger.info(f"📚 Retrieved and reranked {len(reranked_docs)} documents")
                        except Exception as e:
                            logger.error(f"📚 Error in retrieval process: {str(e)}")
                            raise

                    # 7. Response generation chain - Use English query
                    with trace(name="response_generation") as gen_trace:
                        generation_start = time.time()
                        try:
                            logger.info("✍️ Starting response generation...")
                            response, citations = await nova_chat(english_query, reranked_docs, self.nova_model)
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
                                    cohere_api_key=self.COHERE_API_KEY
                                )
                            
                            step_times['quality_check'] = time.time() - quality_start
                            logger.info(f"✔️ Hallucination check complete - Score: {faithfulness_score}")
                            
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
                        await self._store_results(
                            query=norm_query,  # Use normalized query for storage
                            response=response,
                            language_code=language_code,
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
                            "query": norm_query,
                            "response": response,
                            "citations": citations,
                            "faithfulness_score": faithfulness_score,
                            "processing_time": total_time,
                            "step_times": step_times,
                            "cache_hit": False,
                            "trace_id": getattr(pipeline_trace, 'id', None)
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
            fallback_response, fallback_citations = await nova_chat(
                query=query, 
                documents=documents_for_nova, 
                nova_model=self.nova_model, 
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
            
            # Check faithfulness
            fallback_score = await check_hallucination(
                question=english_query,
                answer=processed_response,
                contexts=processed_context,
                cohere_api_key=self.COHERE_API_KEY
            )
            
            return fallback_response, fallback_citations, fallback_score
            
        except Exception as e:
            logger.error(f"Error in Tavily fallback: {str(e)}")
            return None, None, 0.0

    async def _store_results(
        self,
        query: str,
        response: str,
        language_code: str,
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
                "language": language_code,
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
                
                # Process query
                result = await chatbot.process_query(
                    query=query,
                    language_name=language_name
                )
                
                # Display results
                if result.get('success', False):
                    print("\nResponse:", result.get('response', 'No response generated'))
                    
                    if result.get('citations', []):
                        print("\nSources:")
                        for citation in result.get('citations'):
                            print(f"- {citation}")
                            
                    print(f"\nFaithfulness Score: {result.get('faithfulness_score', 0.0):.2f}")
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