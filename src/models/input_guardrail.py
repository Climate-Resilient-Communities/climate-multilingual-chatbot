import os
import logging
import time
from pathlib import Path
import torch
import numpy as np
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
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

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

def calculate_semantic_similarity(query: str, reference_texts: List[str], similarity_model) -> float:
    """
    Calculate semantic similarity between query and reference texts using sentence transformers.
    
    Args:
        query (str): The user query to evaluate
        reference_texts (List[str]): List of climate-related reference texts
        similarity_model: Pre-loaded SentenceTransformer model
        
    Returns:
        float: Maximum cosine similarity score (0-1)
    """
    try:
        # Encode the query and reference texts
        query_embedding = similarity_model.encode([query], convert_to_tensor=False)
        reference_embeddings = similarity_model.encode(reference_texts, convert_to_tensor=False)
        
        # Calculate cosine similarities between query and all reference texts
        similarities = cosine_similarity(query_embedding, reference_embeddings)[0]
        
        # Return the maximum similarity score
        max_similarity = float(np.max(similarities))
        
        logger.info(f"Semantic similarity scores: max={max_similarity:.3f}, mean={np.mean(similarities):.3f}")
        
        return max_similarity
        
    except Exception as e:
        logger.error(f"Error calculating semantic similarity: {str(e)}")
        return 0.0

def get_climate_reference_texts() -> List[str]:
    """
    Return a comprehensive list of climate-related reference texts for semantic similarity.
    These texts cover various climate topics and should capture semantic relationships.
    """
    return [
        # Core climate concepts
        "Climate change refers to long-term shifts in temperatures and weather patterns",
        "Global warming is the increase in Earth's average surface temperature",
        "Greenhouse gases trap heat in the atmosphere causing temperature rise",
        "Carbon dioxide emissions from fossil fuels contribute to climate change",
        "Ocean acidification occurs when seawater absorbs carbon dioxide",
        
        # Environmental processes and systems
        "Rivers and watersheds are affected by changing precipitation patterns",
        "Ocean currents distribute heat around the planet",
        "pH levels in oceans are decreasing due to carbon absorption",
        "Coral reefs are bleaching due to rising water temperatures",
        "Arctic ice is melting at accelerating rates",
        "Sea level rise threatens coastal communities worldwide",
        
        # Ecological impacts
        "Ecosystems are shifting due to changing climate conditions",
        "Species migration patterns are changing with temperature",
        "Forest fires are becoming more frequent and intense",
        "Biodiversity loss is accelerated by climate impacts",
        "Agricultural yields are affected by weather changes",
        "Water resources are stressed by drought and flooding",
        
        # Scientific measurements and indicators
        "Temperature records show warming trends over decades",
        "Ice core data reveals historical climate patterns",
        "Atmospheric CO2 concentrations have reached record levels",
        "Weather stations monitor changing precipitation patterns",
        "Satellite data tracks ice sheet thickness changes",
        "Ocean temperature measurements show warming trends",
        
        # Solutions and mitigation
        "Renewable energy reduces greenhouse gas emissions",
        "Carbon capture technology removes CO2 from atmosphere",
        "Energy efficiency reduces fossil fuel consumption",
        "Sustainable agriculture adapts to climate impacts",
        "Conservation efforts protect climate-vulnerable species",
        "Climate adaptation helps communities prepare for changes",
        
        # Multi-language examples
        "气候变化影响全球生态系统和人类社会",  # Chinese: Climate change affects global ecosystems and human society
        "El cambio climático afecta los océanos y ríos",  # Spanish: Climate change affects oceans and rivers
        "Le changement climatique modifie l'acidité des océans",  # French: Climate change modifies ocean acidity
    ]

async def check_follow_up_with_llm(query: str, conversation_history: List[Dict] = None, nova_model=None) -> Dict[str, Any]:
    """
    Check if a query is a follow-up question using LLM instead of hardcoded indicators.
    Consider both the most recent turn and the broader conversation context.
    
    Args:
        query (str): The user query
        conversation_history (List[Dict], optional): Previous conversation turns
        nova_model: The Nova model for LLM operations
        
    Returns:
        Dict[str, Any]: Result with is_follow_up flag and confidence score
    """
    # If no conversation history, it can't be a follow-up
    if not conversation_history or len(conversation_history) == 0 or nova_model is None:
        return {"is_follow_up": False, "confidence": 1.0, "reason": "no_conversation_history"}
    
    try:
        # Build comprehensive conversation context
        # Include up to 3 most recent turns for context (without overwhelming the prompt)
        context_window = conversation_history[-min(3, len(conversation_history)):]
        context_lines = []
        
        for i, turn in enumerate(context_window):
            turn_query = turn.get('query', '').strip()
            turn_response = turn.get('response', '').strip()
            
            if turn_query:
                context_lines.append(f"User: {turn_query}")
            if turn_response:
                # Truncate very long responses to avoid overwhelming the prompt
                if len(turn_response) > 200:
                    turn_response = turn_response[:200] + "..."
                context_lines.append(f"Assistant: {turn_response}")
            
            # Add separator between turns (except for the last one)
            if i < len(context_window) - 1:
                context_lines.append("---")
        
        conversation_context = "\n".join(context_lines)
        
        # Create a clearer prompt for follow-up detection
        system_message = """You are an expert at determining whether a user message is a follow-up question to an ongoing conversation. 

A follow-up question:
- Refers to something mentioned in the previous conversation
- Asks for clarification, elaboration, or more details about the current topic
- Uses pronouns (it, this, that, they) referring to previous content
- Builds upon or continues the established topic
- Asks "why", "how", "what about", "tell me more" in relation to the current topic

A new question:
- Introduces a completely different topic
- Is self-contained and doesn't reference previous content
- Could be asked without any prior conversation context"""
        
        prompt = f"""Conversation history:
{conversation_context}

New user message: "{query}"

Based on the conversation history above, is this new message a FOLLOW-UP question to the ongoing conversation, or is it a NEW independent question on a different topic?

Consider:
- Does it reference something from the previous conversation?
- Does it seek clarification or more details about what was already discussed?
- Could it be understood without the conversation context?

Answer with just YES (if it's a follow-up) or NO (if it's a new topic), followed by a brief explanation."""
        
        # Get the LLM's assessment
        try:
            result = await nova_model.nova_classification(
                prompt=prompt,
                system_message=system_message,
                options=["YES", "NO"]
            )
            
            # Parse the result
            is_follow_up = result.lower().startswith("yes")
            confidence = 0.9 if is_follow_up else 0.1
            
            logger.info(f"LLM follow-up classification: {result} (is_follow_up={is_follow_up})")
            
            return {
                "is_follow_up": is_follow_up,
                "confidence": confidence,
                "reason": "llm_classification",
                "llm_result": result
            }
        except Exception as llm_error:
            # Fall back to basic heuristics if LLM classification fails
            logger.warning(f"LLM follow-up classification failed: {str(llm_error)}")
            return _fallback_follow_up_check(query)
            
    except Exception as e:
        logger.error(f"Error in follow-up detection: {str(e)}")
        # In case of error, fall back to basic heuristics
        return _fallback_follow_up_check(query)

def _fallback_follow_up_check(query: str) -> Dict[str, Any]:
    """Fallback method using improved heuristics when LLM is unavailable."""
    
    # Enhanced follow-up indicators
    follow_up_indicators = [
        # English - common follow-up patterns
        'why', 'how', 'what about', 'what if', 'tell me about', 'tell me more',
        'explain', 'elaborate', 'detail', 'clarify', 'expand',
        'else', 'more', 'another', 'additional', 'other', 'also', 'further', 
        'too', 'as well', 'next', 'again', 'continue',
        
        # Pronouns and references
        'they', 'their', 'that', 'this', 'those', 'these', 'it', 'them',
        'which', 'such', 'same',
        
        # Question connectors
        'and', 'but', 'so', 'then', 'because', 'since',
        
        # Importance/significance questions
        'important', 'significance', 'matter', 'relevant', 'impact',
        
        # Chinese
        '还有', '更多', '另外', '其他', '也', '还', '进一步', 
        '他们', '它们', '那个', '这个', '那些', '这些', '解释', 
        '详述', '详细', '为什么', '怎样', '关于', '那么', '然后', 
        '此外', '另外呢', '那', '所以', '但是', '和', '以及', '而且',
        '如果', '要是', '既然', '既然如此', '重要', '意义',
        
        # Spanish
        'por qué', 'cómo', 'qué tal', 'explica', 'detalla', 'importante',
        'también', 'además', 'otro', 'otra', 'más', 'eso', 'esto',
        
        # French  
        'pourquoi', 'comment', 'expliquer', 'détailler', 'important',
        'aussi', 'en plus', 'autre', 'plus', 'cela', 'ceci'
    ]
    
    # Short questions that are likely follow-ups
    short_follow_up_patterns = [
        'why?', 'how?', 'what?', 'where?', 'when?', 'who?',
        'why is it important?', 'how so?', 'what do you mean?',
        'can you explain?', 'tell me more', 'go on',
        '为什么?', '怎么?', '什么?', '重要吗?',  # Chinese
        '¿por qué?', '¿cómo?', '¿qué?',  # Spanish
        'pourquoi?', 'comment?', 'quoi?'  # French
    ]
    
    query_lower = query.lower().strip()
    
    # Check for short follow-up patterns first (higher confidence)
    for pattern in short_follow_up_patterns:
        if query_lower == pattern.lower() or query_lower.startswith(pattern.lower()):
            return {
                "is_follow_up": True,
                "confidence": 0.9,
                "reason": "short_follow_up_pattern",
                "pattern": pattern
            }
    
    # Check for general follow-up indicators
    matches = [indicator for indicator in follow_up_indicators if indicator in query_lower]
    
    if matches:
        # Higher confidence if multiple indicators or if query is short
        confidence = 0.8 if len(matches) > 1 or len(query.split()) <= 5 else 0.6
        return {
            "is_follow_up": True,
            "confidence": confidence,
            "reason": "heuristic_indicators",
            "matched_indicators": matches
        }
    
    # No indicators found
    return {
        "is_follow_up": False,
        "confidence": 0.7,
        "reason": "no_follow_up_indicators"
    }

async def topic_moderation(
    query: str, 
    moderation_pipe=None,
    conversation_history: List[Dict] = None,
    nova_model=None,
    similarity_model=None
) -> Dict[str, Any]:
    """
    Validate if query is about climate change or is a follow-up question.
    Now uses semantic similarity for more flexible topic detection.
    
    Args:
        query (str): The user query
        moderation_pipe: Optional pre-initialized pipeline
        conversation_history (List[Dict], optional): Previous conversation turns
        nova_model: Optional Nova model for LLM operations
        similarity_model: Optional SentenceTransformer model for semantic similarity
        
    Returns:
        Dict[str, Any]: Result of moderation with passed flag
    """
    try:
        # Lists of climate-related keywords in multiple languages (still used for explicit matches)
        climate_keywords = [
            # English
            'climate', 'weather', 'warming', 'carbon', 'emission', 'greenhouse', 
            'temperature', 'ocean', 'sea level', 'energy', 'sustainability',
            'renewable', 'arctic', 'icecap', 'glacier', 'environment', 
            'pollution', 'fossil fuel', 'solar', 'wind power', 'deforestation',
            'biodiversity', 'ecosystem', 'conservation', 'adaptation', 'resilience',
            'methane', 'co2', 'atmosphere', 'ph', 'river', 'rivers', 'water',
            'precipitation', 'drought', 'flood', 'coral', 'reef', 'species',
            'forest', 'agriculture', 'farming', 'ice', 'snow', 'precipitation',
            
            # Chinese
            '气候', '天气', '变暖', '全球变暖', '碳', '排放', '温室',
            '温度', '海洋', '海平面', '能源', '可持续性', '再生能源',
            '北极', '冰盖', '冰川', '环境', '污染', '化石燃料',
            '太阳能', '风能', '森林砍伐', '生物多样性', '生态系统',
            '河流', '水', '降水', '干旱', '洪水', '珊瑚', '物种',
            
            # Spanish
            'clima', 'tiempo', 'calentamiento', 'carbono', 'emisión', 'invernadero',
            'temperatura', 'océano', 'nivel del mar', 'energía', 'sostenibilidad',
            'renovable', 'ártico', 'casquete polar', 'glaciar', 'ambiente', 
            'contaminación', 'combustible fósil', 'solar', 'eólica',
            'río', 'ríos', 'agua', 'precipitación', 'sequía', 'inundación',
            
            # French
            'climat', 'météo', 'réchauffement', 'carbone', 'émission', 'serre',
            'température', 'océan', 'niveau de la mer', 'énergie', 'durabilité',
            'renouvelable', 'arctique', 'calotte glaciaire', 'glacier', 'environnement',
            'pollution', 'combustible fossile', 'solaire', 'éolienne',
            'rivière', 'rivières', 'eau', 'précipitation', 'sécheresse', 'inondation'
        ]
        
        # List of off-topic keywords that should always be rejected
        # (keeping these simple and primarily in English since they're less critical)
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
        # Use LLM-based follow-up detection if Nova model is available
        if conversation_history and len(conversation_history) > 0:
            if nova_model:
                follow_up_result = await check_follow_up_with_llm(query, conversation_history, nova_model)
                is_follow_up = follow_up_result.get('is_follow_up', False)
                follow_up_confidence = follow_up_result.get('confidence', 0.5)
                
                if is_follow_up:
                    logger.info(f"Query is a follow-up question (LLM detected) - allowing with confidence {follow_up_confidence}")
                    return {"passed": True, "reason": "follow_up_question_llm", "score": max(0.7, follow_up_confidence)}
            else:
                # Fallback to heuristic approach if Nova model is not available
                fallback_result = _fallback_follow_up_check(query)
                is_follow_up = fallback_result.get('is_follow_up', False)
                
                if is_follow_up:
                    logger.info("Query is a follow-up question (heuristic) - allowing")
                    return {"passed": True, "reason": "follow_up_question_heuristic", "score": 0.7}
        
        # Third check: Does it contain explicit climate keywords?
        if any(keyword in query.lower() for keyword in climate_keywords):
            logger.info("Query contains explicit climate keywords - allowing")
            return {"passed": True, "reason": "climate_keywords", "score": 0.95}
        
        # Fourth check: Use semantic similarity if available (NEW - more flexible approach)
        if similarity_model:
            try:
                logger.info("Running semantic similarity analysis...")
                reference_texts = get_climate_reference_texts()
                similarity_score = calculate_semantic_similarity(query, reference_texts, similarity_model)
                
                # More lenient threshold than previous ML model (0.4 vs 0.6)
                # This allows queries like "pH" or "rivers" to pass through
                similarity_threshold = 0.4
                
                if similarity_score >= similarity_threshold:
                    logger.info(f"Query passed semantic similarity check: {similarity_score:.3f} >= {similarity_threshold}")
                    return {"passed": True, "reason": "semantic_similarity", "score": similarity_score}
                else:
                    logger.info(f"Query failed semantic similarity check: {similarity_score:.3f} < {similarity_threshold}")
                    # Don't immediately reject - still try the ClimateBERT model below
                    
            except Exception as e:
                logger.error(f"Error in semantic similarity analysis: {str(e)}")
        
        # Fifth check: Use ClimateBERT ML model as backup if semantic similarity not available or failed
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

async def safe_guard_input(question: str, pipe, similarity_model=None) -> Dict[str, Any]:
    """Execute topic moderation in a safe way with retries."""
    return await topic_moderation(question, pipe, similarity_model=similarity_model)

def check_dir(path, description="directory"):
    """Utility function to check directory existence and list contents"""
    dir_path = Path(path)
    if dir_path.exists() and dir_path.is_dir():  # Fixed: Changed is_dir() to dir_path.is_dir()
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
        
        # Initialize sentence transformer model for semantic similarity
        # Using a multilingual model that works well across languages
        logger.info("Initializing sentence transformer model for semantic similarity...")
        try:
            # Use a compact but effective multilingual model
            similarity_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("✓ Successfully initialized semantic similarity model")
        except Exception as sim_err:
            logger.warning(f"Failed to initialize similarity model: {str(sim_err)}")
            logger.info("Falling back to basic multilingual model...")
            try:
                # Fallback to an even smaller model
                similarity_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
                logger.info("✓ Successfully initialized fallback similarity model")
            except Exception as fallback_err:
                logger.error(f"Failed to initialize any similarity model: {str(fallback_err)}")
                similarity_model = None
        
        logger.info("Models initialized successfully")
        return topic_moderation_pipe, similarity_model
        
    except Exception as e:
        logger.error(f"Error initializing models: {e}")
        raise

if __name__ == "__main__":
    # Test the topic moderation functionality
    import asyncio
    
    async def test_moderation():
        topic_moderation_pipe, similarity_model = initialize_models()
        
        test_questions = [
            "what is climate change?",
            "how can I start a fire in a forest?",
            "Is global warming a hoax?",
            "How can I create toxic chemicals to harm wildlife??",
            'hi, how are you?',
            'where can I buy new shoes?',
            'what else can i do to help?',
            'tell me more about CO2 emissions',
            # NEW TEST CASES for semantic similarity
            'What is the pH of ocean water?',
            'How do rivers affect the environment?',
            'Tell me about coral reefs',
            'What happens to ice when it melts?',
            'How does agriculture relate to weather?',
            'What are the effects on marine species?',
            'Can you explain precipitation patterns?',
        ]
        
        # Test each question independently
        for question in test_questions:
            print(f"\nTesting standalone: {question}")
            topic_result = await topic_moderation(question, topic_moderation_pipe, similarity_model=similarity_model)
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
        result = await topic_moderation(follow_up, topic_moderation_pipe, conversation_history, similarity_model=similarity_model)
        print(f"Result with history: {result}")
        
        result_no_context = await topic_moderation(follow_up, topic_moderation_pipe, similarity_model=similarity_model)
        print(f"Result without history: {result_no_context}")
        
        print('-'*50)
    
    asyncio.run(test_moderation())

