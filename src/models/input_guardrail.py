import ray
import torch
import logging
import time
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline
)
from transformers.pipelines.pt_utils import KeyDataset
from datasets import Dataset
from langsmith import traceable

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

def initialize_models():
    """Initialize topic moderation ML model."""
    try:
        # Load model and tokenizer for ClimateBERT
        climatebert_model_name = "climatebert/distilroberta-base-climate-detector"
        climatebert_model = AutoModelForSequenceClassification.from_pretrained(climatebert_model_name)
        climatebert_tokenizer = AutoTokenizer.from_pretrained(climatebert_model_name)

        # Set up topic moderation pipeline with proper settings
        device = 0 if torch.cuda.is_available() else -1
        topic_moderation_pipe = pipeline(
            "text-classification",
            model=climatebert_model,
            tokenizer=climatebert_tokenizer,
            device=device
        )

        print("Models initialized successfully")
        return topic_moderation_pipe, None
        
    except Exception as e:
        print(f"Error initializing models: {e}")
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

