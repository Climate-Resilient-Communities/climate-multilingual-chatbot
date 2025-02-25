import os
import sys
from pathlib import Path

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

import ray
import time
from datetime import timedelta
import logging
import cohere
from src.utils.env_loader import load_environment  # Updated import path
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import json
from huggingface_hub import login
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline
)
from pinecone import Pinecone
from FlagEmbedding import BGEM3FlagModel
from langsmith import Client
from langchain.callbacks.tracers import LangChainTracer
from langchain.chains.base import Chain
from langchain_core.tracers import ConsoleCallbackHandler
from src.models.query_processing_chain import QueryProcessingChain

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables first
load_environment()

# Set LangSmith environment variables from .env
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "climate-chat-production")

import warnings
warnings.filterwarnings("ignore", category=Warning)

load_environment()

# Import all functions from our custom modules
from src.models.redis_cache import ClimateCache
from src.models.nova_flow import BedrockModel
from src.models.gen_response_nova import nova_chat  # Updated import
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

# Define the correct index name as a constant
#PINECONE_INDEX_NAME = "climate-change-adaptation-index-10-24-prod"

class MultilingualClimateChatbot:
    """
    A multilingual chatbot specialized in climate-related topics.
    
    This chatbot supports multiple languages through Aya translation,
    implements RAG (Retrieval Augmented Generation), and includes
    various guardrails for input validation and output quality.
    """

    # Language mappings from aya_translation.py
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
            # Initialize environment
            env_path = Path(__file__).resolve().parent.parent / ".env"
            if not os.path.exists(env_path):
                raise FileNotFoundError(f".env file not found at {env_path}")
            
            self._initialize_api_keys()
            self._initialize_components(index_name)
            self._initialize_langsmith()
            logger.info("Chatbot initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise

    def _initialize_api_keys(self) -> None:
        """Initialize and validate API keys."""
        self.PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
        self.COHERE_API_KEY = os.getenv('COHERE_API_KEY')
        self.TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

        self.cohere_client = cohere.ClientV2(api_key=self.COHERE_API_KEY)

        self.HF_API_TOKEN = os.getenv("HF_API_TOKEN")
        login(token=self.HF_API_TOKEN, add_to_git_credential=True)
        
        if not all([self.PINECONE_API_KEY, self.COHERE_API_KEY, self.TAVILY_API_KEY]):
            raise ValueError("Missing required API keys in .env file")

        os.environ['PINECONE_API_KEY'] = self.PINECONE_API_KEY 
        os.environ["COHERE_API_KEY"] = self.COHERE_API_KEY
        os.environ["TAVILY_API_KEY"] = self.TAVILY_API_KEY

    def _initialize_components(self, index_name: str) -> None:
        """Initialize all required components."""
        # Initialize Ray if not already initialized
        if not ray.is_initialized():
            ray.init()
            
        # Initialize components
        self._initialize_models()
        self._initialize_retrieval(index_name)
        self._initialize_language_router()
        self._initialize_nova_flow()
        self._initialize_redis()
        
        # Initialize storage
        self.response_cache = {}
        self.conversation_history = []
        self.feedback_metrics = []

    def _initialize_models(self) -> None:
        """Initialize all ML models."""
        # Initialize ClimateBERT for topic moderation
        self.climatebert_model = AutoModelForSequenceClassification.from_pretrained(
            "climatebert/distilroberta-base-climate-detector"
        )
        self.climatebert_tokenizer = AutoTokenizer.from_pretrained(
           "climatebert/distilroberta-base-climate-detector",
           max_len=512
        )
        
        # Set up pipelines
        device = 0 if torch.cuda.is_available() else -1 
        self.topic_moderation_pipe = pipeline(
            "text-classification",
            model=self.climatebert_model,
            tokenizer=self.climatebert_tokenizer,
            device=device,
            truncation=True,
            max_length=512
        )

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
            # Create new event loop for Redis initialization
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.redis_client = ClimateCache()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Redis initialization failed: {str(e)}")
            self.redis_client = None

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
    async def process_input_guards(self, query: str) -> Dict[str, bool]:
        """Run input guardrails for topic moderation only."""
        try:
            logger.info("Running input guardrails")
            # Perform topic check
            topic_check = topic_moderation.remote(
                query,
                self.topic_moderation_pipe
            )
            
            # Get result
            topic_result = ray.get(topic_check)
            
            logger.debug(f"Guard results - Topic: {topic_result}")
            
            # Return only topic moderation result
            return {
                "passed": topic_result == "yes",
                "topic_check": topic_result == "yes"
            }
            
        except Exception as e:
            logger.error(f"Error in input guards: {str(e)}")
            raise

    async def process_query(
            self,
            query: str,
            language_name: str
        ) -> Dict[str, Any]:
            """Process a query through the complete pipeline."""
            try:
                # Create chain instance with LangSmith tracing
                chain = QueryProcessingChain(chatbot=self)
                callbacks = [self.tracer]
                
                # Get or create event loop for cleanup
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Close Redis connection if it exists
                if hasattr(self, 'redis_client') and self.redis_client is not None:
                    try:
                        if not getattr(self.redis_client, '_closed', False):
                            await self.redis_client.close()
                    except Exception as e:
                        cleanup_errors.append(f"Redis cleanup error: {str(e)}")
                        logger.error(f"Error closing Redis connection: {str(e)}")
                    finally:
                        self.redis_client = None

                # Shutdown Ray if initialized
                if ray.is_initialized():
                    try:
                        ray.shutdown()
                    except Exception as e:
                        cleanup_errors.append(f"Ray cleanup error: {str(e)}")
                        logger.error(f"Error shutting down Ray: {str(e)}")
                
                if cleanup_errors:
                    logger.error(f"Cleanup completed with errors: {', '.join(cleanup_errors)}")
                else:
                    logger.info("Cleanup completed successfully")

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
                    print(f"Processing Time: {result.get('processing_time', 0.0):.2f} seconds")
                else:
                    print("\nError:", result.get('response', 'An unknown error occurred'))
                    
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
            print("\nCleaning up resources...")
            await chatbot.cleanup()
            print("✓ Cleanup complete")

# ...existing code...