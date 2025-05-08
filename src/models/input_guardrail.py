import os
import logging
import time
from pathlib import Path
import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline
)
from transformers.pipelines.pt_utils import KeyDataset
from datasets import Dataset
from langsmith import traceable
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import json
import boto3
from botocore.config import Config

# Import Azure configuration
from src.data.config.azure_config import is_running_in_azure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def construct_dataset(question):
    """Return a dataset from a question"""
    return Dataset.from_dict({'question': [question]})

async def topic_moderation(
    query: str, 
    moderation_pipe=None,
    conversation_history: List[Dict] = None
) -> Dict[str, Any]:
    """
    Validate if query is about climate change or is a follow-up question.
    
    Args:
        query (str): The user query
        moderation_pipe: Optional pre-initialized pipeline
        conversation_history (List[Dict], optional): Previous conversation turns
        
    Returns:
        Dict[str, Any]: Result of moderation with passed flag
    """
    try:
        # Lists of climate-related keywords
        climate_keywords = [
            'climate', 'weather', 'warming', 'carbon', 'emission', 'greenhouse', 
            'temperature', 'ocean', 'sea level', 'energy', 'sustainability',
            'renewable', 'arctic', 'icecap', 'glacier', 'environment', 
            'pollution', 'fossil fuel', 'solar', 'wind power', 'deforestation',
            'biodiversity', 'ecosystem', 'conservation', 'adaptation', 'resilience',
            'methane', 'co2', 'atmosphere'
        ]
        
        # List of off-topic keywords that should always be rejected
        off_topic_keywords = [
            'shoes', 'clothing', 'clothes', 'buy', 'purchase', 'shop', 'store', 'mall',
            'fashion', 'outfit', 'dress', 'wear', 'shirt', 'pants', 'jeans',
            'sneakers', 'boots', 'sandals', 'handbag', 'purse', 'wallet', 'shopping',
            'jewelry', 'watch', 'electronics', 'phone', 'computer', 'laptop', 'retail'
        ]
        
        # First check: Is it explicitly about shopping? If yes, reject immediately
        if any(keyword in query.lower() for keyword in off_topic_keywords):
            logger.info(f"Query contains explicit off-topic keywords - rejecting")
            return {"passed": False, "reason": "explicitly_off_topic", "score": 0.1}
        
        # Second check: Is it a follow-up question? If yes, allow immediately
        follow_up_indicators = [
            'else', 'more', 'another', 'additional', 'other', 'also', 'further', 
            'too', 'as well', 'next', 'again', 'they', 'their', 'that', 'this', 
            'those', 'these', 'it', 'them', 'explain', 'elaborate', 'detail',
            'why', 'how', 'what about'
        ]
        
        is_follow_up = any(indicator in query.lower() for indicator in follow_up_indicators)
        
        # If we have previous conversation AND it's a follow-up question, pass it
        if conversation_history and len(conversation_history) > 0 and is_follow_up:
            logger.info("Query is a follow-up question with conversation context - allowing")
            return {"passed": True, "reason": "follow_up_question", "score": 0.9}
        
        # Third check: Does it contain explicit climate keywords?
        if any(keyword in query.lower() for keyword in climate_keywords):
            logger.info("Query contains explicit climate keywords - allowing")
            return {"passed": True, "reason": "climate_keywords", "score": 0.95}
        
        # Last check: If not obvious, use the ML model if available
        if moderation_pipe:
            try:
                # Run classification
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        moderation_pipe,
                        query
                    )
                    result = future.result(timeout=10)
                
                # Extract classification
                classification = result[0] if result else None
                label = classification.get('label', '').lower() if classification else ''
                score = classification.get('score', 0.0) if classification else 0.0
                
                # Make decision based on label and score
                if label == 'yes' and score > 0.6:
                    logger.info(f"Query is about climate change according to ML model, score: {score:.2f}")
                    return {"passed": True, "reason": "climate_related_ml", "score": score}
                else:
                    logger.info(f"Query is not about climate change according to ML model, score: {score:.2f}")
                    return {"passed": False, "reason": "not_climate_related_ml", "score": score}
            except Exception as e:
                logger.error(f"Error in ML classification: {str(e)}")
        
        # Default to rejecting if none of the above checks passed
        logger.info(f"Query does not appear climate-related - rejecting")
        return {"passed": False, "reason": "not_climate_related", "score": 0.3}
        
    except Exception as e:
        logger.error(f"Error in topic moderation: {str(e)}")
        # Default to passing in case of errors
        return {"passed": True, "reason": "error_in_moderation", "error": str(e), "score": 0.5}

async def safe_guard_input(question: str, pipe) -> Dict[str, Any]:
    """Execute topic moderation in a safe way with retries."""
    return await topic_moderation(question, pipe)

def check_dir(path, description="directory"):
    """Utility function to check directory existence and list contents"""
    dir_path = Path(path)
    if dir_path.exists() and is_dir():
        try:
            contents = list(dir_path.iterdir())
            logger.info(f"{description} at {path} exists with {len(contents)} items")
            
            # Log first few items
            if contents:
                item_names = [item.name for item in contents[:5]]
                logger.info(f"First few items: {', '.join(item_names)}")
                
            return True, contents
        except Exception as e:
            logger.error(f"Error checking {description} at {path}: {str(e)}")
            return False, []
    else:
        logger.warning(f"{description} at {path} does not exist or is not a directory")
        return False, []

def initialize_models():
    """Initialize topic moderation ML model."""
    try:
        # Model name for downloading
        climatebert_model_name = "climatebert/distilroberta-base-climate-detector"
        
        # Check for local model in Azure App Service path first
        azure_model_path = Path("/home/site/wwwroot/models/climatebert")
        project_root = Path(__file__).resolve().parent.parent.parent
        local_model_path = project_root / "models" / "climatebert"
        
        # Verify directory existence and contents
        logger.info("Checking model directories...")
        is_azure = is_running_in_azure()
        logger.info(f"Running in Azure: {is_azure}")
        
        azure_exists, azure_files = check_dir(azure_model_path, "Azure model directory")
        local_exists, local_files = check_dir(local_model_path, "Local model directory")
        
        # Extra debug info for Azure environment
        if is_azure:
            try:
                azure_wwwroot = Path("/home/site/wwwroot")
                wwwroot_exists, wwwroot_contents = check_dir(azure_wwwroot, "Azure wwwroot directory")
                
                # Check for models dir directly under wwwroot
                models_dir = azure_wwwroot / "models"
                models_exists, models_contents = check_dir(models_dir, "Models directory")
            except Exception as e:
                logger.error(f"Error checking Azure directories: {str(e)}")
        
        # Set Hugging Face cache dir explicitly to a known writable location
        if is_azure:
            os.environ["HF_HOME"] = "/tmp/huggingface"
            os.environ["TRANSFORMERS_CACHE"] = "/tmp/huggingface/transformers"
            logger.info(f"Set HF_HOME to {os.environ.get('HF_HOME')}")
        
        # Try Azure path first, then local path, then fallback to HF download
        climatebert_model = None
        climatebert_tokenizer = None
        
        if is_azure and azure_exists and azure_files:
            logger.info(f"Loading ClimateBERT model from Azure path: {azure_model_path}")
            try:
                # Set offline mode to force local file usage
                os.environ["HF_HUB_OFFLINE"] = "1"
                climatebert_model = AutoModelForSequenceClassification.from_pretrained(
                    str(azure_model_path),
                    local_files_only=True
                )
                climatebert_tokenizer = AutoTokenizer.from_pretrained(
                    str(azure_model_path),
                    local_files_only=True
                )
                os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                logger.info("✓ Successfully loaded ClimateBERT from Azure directory")
            except Exception as azure_err:
                os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                logger.warning(f"Failed to load from Azure path: {str(azure_err)}")
                logger.info("Falling back to local directory...")
        
        # If model still not loaded, try local path
        if (climatebert_model is None) and local_exists and local_files:
            logger.info(f"Loading ClimateBERT model from local path: {local_model_path}")
            try:
                # Set offline mode to force local file usage
                os.environ["HF_HUB_OFFLINE"] = "1"
                climatebert_model = AutoModelForSequenceClassification.from_pretrained(
                    str(local_model_path),
                    local_files_only=True
                )
                climatebert_tokenizer = AutoTokenizer.from_pretrained(
                    str(local_model_path),
                    local_files_only=True
                )
                os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                logger.info("✓ Successfully loaded ClimateBERT from local directory")
            except Exception as local_err:
                os.environ.pop("HF_HUB_OFFLINE", None)  # Remove offline mode
                logger.warning(f"Failed to load from local path: {str(local_err)}")
        
        # If model still not loaded, try downloading
        if climatebert_model is None:
            logger.info(f"Local model not found. Downloading from Hugging Face.")
            try:
                climatebert_model = AutoModelForSequenceClassification.from_pretrained(climatebert_model_name)
                climatebert_tokenizer = AutoTokenizer.from_pretrained(climatebert_model_name)
                logger.info("✓ Successfully downloaded ClimateBERT from Hugging Face")
            except Exception as download_err:
                logger.error(f"Failed to download model: {str(download_err)}")
                raise  # Re-raise if we can't load the model any way
        
        # Set up topic moderation pipeline with proper settings
        device = 0 if torch.cuda.is_available() else -1
        topic_moderation_pipe = pipeline(
            "text-classification",
            model=climatebert_model,
            tokenizer=climatebert_tokenizer,
            device=device
        )
        
        logger.info("Models initialized successfully")
        return topic_moderation_pipe, None
        
    except Exception as e:
        logger.error(f"Error initializing models: {e}")
        raise

if __name__ == "__main__":
    # Test the topic moderation functionality
    import asyncio
    
    async def test_moderation():
        topic_moderation_pipe, _ = initialize_models()
        
        test_questions = [
            "what is climate change?",
            "how can I start a fire in a forest?",
            "Is global warming a hoax?",
            "How can I create toxic chemicals to harm wildlife??",
            'hi, how are you?',
            'where can I buy new shoes?',
            'what else can i do to help?',
            'tell me more about CO2 emissions',
        ]
        
        # Test each question independently
        for question in test_questions:
            print(f"\nTesting standalone: {question}")
            topic_result = await topic_moderation(question, topic_moderation_pipe)
            print(f"Topic moderation result: {topic_result}")
            
        # Now test with conversation history
        print("\n=== Testing with conversation history ===")
        conversation_history = [
            {
                'query': 'What is climate change?',
                'response': 'Climate change refers to long-term shifts in temperatures and weather patterns caused by human activities.'
            }
        ]
        
        follow_up = "what else should I know?"
        print(f"\nFollow-up with context: {follow_up}")
        result = await topic_moderation(follow_up, topic_moderation_pipe, conversation_history)
        print(f"Result with history: {result}")
        
        result_no_context = await topic_moderation(follow_up, topic_moderation_pipe)
        print(f"Result without history: {result_no_context}")
        
        print('-'*50)
    
    asyncio.run(test_moderation())

