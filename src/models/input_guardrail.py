import ray
import torch
import logging
import time
import os
from pathlib import Path
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline
)
from transformers.pipelines.pt_utils import KeyDataset
from datasets import Dataset
from langsmith import traceable

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

@ray.remote
def topic_moderation(question, topic_pipe):
    """
    Return a topic moderation label from a question.
    Returns dictionary with passed=True if the question is climate-related and safe.
    """
    start_time = time.time()
    try:
        # Harmful content patterns to check
        harmful_patterns = [
            'start a fire', 'burn', 'toxic', 'harm', 'destroy', 'damage',
            'kill', 'pollute', 'contaminate', 'poison'
        ]
        
        # Misinformation/denial patterns
        denial_patterns = [
            'hoax', 'fake', 'fraud', 'scam', 'conspiracy',
            'not real', 'isn\'t real', 'propaganda'
        ]
        
        question_lower = question.lower()
        
        # Check for harmful content first
        if any(pattern in question_lower for pattern in harmful_patterns):
            logger.warning(f"Harmful content detected in query: {question}")
            return {
                "passed": False,
                "result": "no",
                "reason": "harmful_content",
                "duration": time.time() - start_time
            }
            
        # Check for denial/misinformation patterns
        if any(pattern in question_lower for pattern in denial_patterns):
            logger.warning(f"Potential misinformation/denial detected in query: {question}")
            return {
                "passed": False,
                "result": "no",
                "reason": "misinformation",
                "duration": time.time() - start_time
            }
        
        # Direct pipeline call for climate relevance
        result = topic_pipe(question)
        if result and len(result) > 0:
            # Log the full result for debugging
            logger.debug(f"Topic moderation raw result: {result}")
            print(f"Raw model output: {result}")
            # Model returns 'yes' label for climate-related content
            if result[0]['label'] == 'yes' and result[0]['score'] > 0.5:
                return {
                    "passed": True,
                    "result": "yes",
                    "score": result[0]['score'],
                    "duration": time.time() - start_time
                }
        return {
            "passed": False,
            "result": "no",
            "reason": "not_climate_related",
            "score": result[0]['score'] if result and len(result) > 0 else 0.0,
            "duration": time.time() - start_time
        }
        
    except Exception as e:
        logger.error(f"Error in topic moderation: {str(e)}")
        return {
            "passed": False,
            "result": "no",
            "reason": "error",
            "error": str(e),
            "duration": time.time() - start_time
        }

@ray.remote
def safe_guard_input(question, pipe):
    result = pipe(question)
    return result

def check_dir(path, description="directory"):
    """Utility function to check directory existence and list contents"""
    dir_path = Path(path)
    if dir_path.exists() and dir_path.is_dir():
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
            logger.info(f"Local model not found. Downloading from Hugging Face...")
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
    # Initialize Ray and models
    ray.init()
    topic_moderation_pipe, _ = initialize_models()
    
    test_questions = [
        "what is climate change?",
        "how can I start a fire in a forest?",
        "Is global warming a hoax?",
        "How can I create toxic chemicals to harm wildlife??",
        'hi, how are you?'
    ]
    
    for question in test_questions:
        print(f"\nTesting: {question}")
        # Run topic moderation directly without KeyDataset
        topic_result = ray.get(topic_moderation.remote(question, topic_moderation_pipe))
        print(f"Topic moderation result: {topic_result}")
        print('-'*50)

