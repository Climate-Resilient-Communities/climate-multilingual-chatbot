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
from src.utils.env_loader import load_environment
from src.models.redis_cache import ClimateCache
from src.models.nova_flow import BedrockModel
from src.models.gen_response_nova import nova_chat
from src.models.query_routing import MultilingualRouter
from src.models.input_guardrail import topic_moderation
from src.models.retrieval import get_documents
from src.models.hallucination_guard import extract_contexts, check_hallucination

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables once
load_environment()

# Set up LangSmith environment variables
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "climate-chat-production")

# Filter warnings
warnings.filterwarnings("ignore", category=Warning)

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
        
        # Login to Hugging Face
        login(token=self.HF_API_TOKEN, add_to_git_credential=True)

        # Set environment variables
        os.environ.update({
            'PINECONE_API_KEY': self.PINECONE_API_KEY,
            'COHERE_API_KEY': self.COHERE_API_KEY,
            'TAVILY_API_KEY': self.TAVILY_API_KEY
        })

    def _initialize_components(self, index_name: str) -> None:
        """Initialize all required components."""
        if not ray.is_initialized():
            ray.init()
            
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
        """Initialize Redis client with proper event loop handling."""
        try:
            # If Redis client exists and is not closed, no need to reinitialize
            if self.redis_client and not getattr(self.redis_client, '_closed', True):
                return

            host = os.getenv('REDIS_HOST', 'localhost')
            port = int(os.getenv('REDIS_PORT', 6379))
            password = os.getenv('REDIS_PASSWORD', None) or None  # Convert empty string to None
            
            logger.info(f"Initializing Redis connection to {host}:{port}")
            
            # Direct initialization without event loop dependency
            self.redis_client = ClimateCache(
                host=host,
                port=port,
                password=password,
                expiration=3600  # 1 hour cache expiration
            )
            
            # Test connection to ensure it's working
            loop = asyncio.get_event_loop()
            test_result = loop.run_until_complete(self._test_redis_connection())
            if test_result:
                logger.info("Redis cache initialized and connected successfully")
            else:
                logger.error("Redis connection test failed")
                self.redis_client = None
                
        except Exception as e:
            logger.error(f"Redis initialization failed: {str(e)}")
            self.redis_client = None
    
    async def _test_redis_connection(self):
        """Test Redis connection by setting and getting a test value."""
        try:
            if not self.redis_client or getattr(self.redis_client, '_closed', True):
                return False
                
            test_key = "test:connection"
            test_value = {"test": "value", "timestamp": time.time()}
            
            # Test setting a value
            set_result = await self.redis_client.set(test_key, test_value)
            if not set_result:
                logger.error("Failed to set test value in Redis")
                return False
                
            # Test getting the value
            get_result = await self.redis_client.get(test_key)
            if not get_result:
                logger.error("Failed to get test value from Redis")
                return False
                
            # Clean up test key
            await self.redis_client.delete(test_key)
            return True
        except Exception as e:
            logger.error(f"Redis connection test failed: {str(e)}")
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

    @traceable(name="input_validation")
    async def process_input_guards(self, query: str) -> Dict[str, Any]:
        """Run input guardrails."""
        try:
            logger.info("Running input guardrails")
            guard_start = time.time()
            
            # Basic input validation
            with trace(name="basic_validation"):
                if not query or len(query.strip()) == 0:
                    return {
                        "passed": False,
                        "reason": "empty_query",
                        "message": "Please provide a question to get started.",
                        "duration": time.time() - guard_start
                    }
                    
                if len(query.split()) < 2:
                    return {
                        "passed": False,
                        "reason": "too_short",
                        "message": "Could you please provide a more detailed question about climate change?",
                        "duration": time.time() - guard_start
                    }

            # Perform topic check with nested tracing
            with trace(name="topic_moderation") as topic_trace:
                try:
                    # Call the remote function which returns an ObjectRef
                    topic_ref = topic_moderation.remote(
                        question=query,
                        topic_pipe=self.topic_moderation_pipe
                    )
                    
                    # Get the result from the ObjectRef
                    topic_result = await asyncio.to_thread(ray.get, topic_ref)
                    
                    # Add trace metadata
                    topic_result['trace_id'] = topic_trace.id
                    topic_result['duration'] = time.time() - guard_start
                    return topic_result
                    
                except Exception as e:
                    logger.error(f"Topic moderation error: {str(e)}", exc_info=True)
                    return {
                        "passed": False,
                        "reason": "moderation_error",
                        "message": "I'm having trouble processing your question. Could you try rephrasing it or ask a different climate-related question?",
                        "duration": time.time() - guard_start,
                        "error": str(e)
                    }
            
        except Exception as e:
            logger.error(f"Error in input guards: {str(e)}", exc_info=True)
            return {
                "passed": False,
                "reason": "system_error",
                "message": "I apologize, but I'm experiencing technical difficulties. Please try again with a climate-related question.",
                "duration": time.time() - guard_start,
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
                
                # Main pipeline trace that wraps everything
                with trace(name="complete_pipeline") as pipeline_trace:
                    # 1. Basic query normalization and language setup
                    with trace(name="query_preprocessing") as preprocess_trace:
                        norm_query = query.lower().strip()
                        language_code = self.get_language_code(language_name)
                        cache_key = f"{language_code}:{norm_query}"
                        
                        # Ensure Redis connection is active
                        if not self.redis_client or getattr(self.redis_client, '_closed', True):
                            logger.info("Redis client not available, reinitializing...")
                            self._initialize_redis()
                        
                        logger.info(f"🔍 Checking cache with key: '{cache_key}'")
                    
                    # 2. Check cache first before any processing
                    with trace(name="cache_check") as cache_trace:
                        if self.redis_client and not getattr(self.redis_client, '_closed', False):
                            try:
                                logger.info(f"📝 Redis client exists, attempting to get value for key: '{cache_key}'")
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
                                        "step_times": {"cache_lookup": cache_time},
                                        "trace_id": pipeline_trace.id
                                    }
                                else:
                                    logger.info(f"❓ Cache miss for key: '{cache_key}'")
                            except Exception as e:
                                logger.warning(f"⚠️ Cache retrieval failed: {str(e)}")

                    logger.info("🔍 Starting full processing pipeline...")
                    
                    # 3. Query normalization
                    with trace(name="query_normalization") as norm_trace:
                        norm_start = time.time()
                        norm_query = await self.nova_model.query_normalizer(norm_query, language_name)
                        step_times['normalization'] = time.time() - norm_start

                    # 4. Input validation and topic moderation
                    with trace(name="input_validation") as validation_trace:
                        validation_start = time.time()
                        logger.info("🔍 Validating input...")
                        
                        # Run input guards which includes nested topic moderation
                        guard_results = await self.process_input_guards(norm_query)
                        step_times['validation'] = time.time() - validation_start
                        
                        if not guard_results['passed']:
                            total_time = time.time() - start_time
                            return {
                                "success": False,
                                "message": guard_results.get('message', "I apologize, but I can only help with climate-related questions."),
                                "validation_result": guard_results,
                                "processing_time": total_time,
                                "step_times": step_times,
                                "trace_id": pipeline_trace.id
                            }
                        logger.info("🔍 Input validation passed")

                    # 5. Language routing
                    with trace(name="language_routing") as route_trace:
                        route_start = time.time()
                        logger.info("🌐 Processing language routing...")
                        route_result = await self.router.route_query(
                            query=norm_query,
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
                        
                        processed_query = route_result['processed_query']
                        english_query = route_result['english_query']
                        logger.info("🌐 Language routing complete")

                    # 6. Document retrieval chain
                    with trace(name="document_retrieval") as retrieval_trace:
                        retrieval_start = time.time()
                        try:
                            logger.info("📚 Starting retrieval and reranking...")
                            # Document retrieval includes hybrid search and reranking
                            reranked_docs = await get_documents(processed_query, self.index, self.embed_model, self.cohere_client)
                            step_times['retrieval'] = time.time() - retrieval_start
                            logger.info(f"📚 Retrieved and reranked {len(reranked_docs)} documents")
                        except Exception as e:
                            logger.error(f"📚 Error in retrieval process: {str(e)}")
                            raise

                    # 7. Response generation chain
                    with trace(name="response_generation") as gen_trace:
                        generation_start = time.time()
                        try:
                            logger.info("✍️ Starting response generation...")
                            response, citations = await nova_chat(processed_query, reranked_docs, self.nova_model)
                            step_times['generation'] = time.time() - generation_start
                            logger.info("✍️ Response generation complete")
                        except Exception as e:
                            logger.error(f"✍️ Error in response generation: {str(e)}")
                            raise

                    # 8. Quality checks chain
                    with trace(name="quality_checks") as quality_trace:
                        quality_start = time.time()
                        logger.info("✔️ Starting quality checks...")
                        try:
                            contexts = extract_contexts(reranked_docs, max_contexts=5)

                            # Translate response for hallucination check if needed
                            if route_result['routing_info']['support_level']=='command_r_plus' and language_code!='en':
                                processed_response = await self.nova_model.nova_translation(response, language_name, 'english')
                            else:
                                processed_response = response

                            # Nested hallucination check within quality checks
                            with trace(name="hallucination_check") as hall_trace:
                                faithfulness_score = await check_hallucination(
                                    question=english_query,
                                    answer=processed_response,
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
                                        query=processed_query,
                                        english_query=english_query,
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

                    # 9. Final translation if needed
                    with trace(name="final_translation") as trans_trace:
                        translation_start = time.time()
                        if route_result['routing_info']['needs_translation']:
                            logger.info(f"🌐 Translating response back to {language_name}")
                            response = await self.nova_model.nova_translation(response, 'english', language_name)
                            step_times['translation'] = time.time() - translation_start
                            logger.info("🌐 Translation complete")

                    # 10. Store results
                    with trace(name="result_storage") as storage_trace:
                        total_time = time.time() - start_time
                        await self._store_results(
                            query=norm_query,
                            response=response,
                            language_code=language_code,
                            citations=citations,
                            faithfulness_score=faithfulness_score,
                            processing_time=total_time,
                            route_result=route_result
                        )

                        logger.info(f"Processing time: {total_time} seconds")
                        logger.info("✨ Processing complete!")

                        # Return final results with full tracing info
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
                            "trace_id": pipeline_trace.id
                        }
                    
            except Exception as e:
                logger.error(f"❌ Error processing query: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "message": f"Error processing query: {str(e)}",
                    "trace_id": getattr(pipeline_trace, 'id', None)  # Include trace ID even in error case
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
        cleanup_tasks = []  # Initialize cleanup_tasks list
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

        # Shutdown Ray if initialized
        if ray.is_initialized():
            try:
                ray.shutdown()
            except Exception as e:
                cleanup_errors.append(f"Ray cleanup error: {str(e)}")
                logger.error(f"Error shutting down Ray: {str(e)}")

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

async def main():
    """Main entry point for the climate chatbot application."""
    try:
        # Validate command line arguments
        if len(sys.argv) < 2:
            print("Usage: python main.py <index_name> ")
            print("Example: python main.py climate-change-adaptation-index-10-24-prod ")
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
                    
            except KeyboardInterrupt:
                print("\n\nExiting gracefully...")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again.")
                
    except KeyboardInterrupt:
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
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"\nProgram terminated due to error: {str(e)}")
        sys.exit(1)