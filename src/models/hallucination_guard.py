import os
import json
import logging
import asyncio
from typing import List, Dict, Union, Optional
from src.utils.env_loader import load_environment
from src.models.nova_flow import BedrockModel
import cohere

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_or_create_event_loop():
    """Get the current event loop or create a new one."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

def truncate_text(text: str, max_length: int = 450) -> str:
    """Truncate text to a maximum number of words while preserving meaning."""
    words = text.split()
    return ' '.join(words[:max_length]) + '...' if len(words) > max_length else text

def extract_contexts(docs_reranked: List[dict], max_contexts: int = 3) -> List[str]:
    """Extract and truncate context from documents."""
    try:
        contexts = [
            truncate_text(doc.get('content', ''))
            for doc in docs_reranked[:max_contexts]
        ]
        logger.debug(f"Extracted {len(contexts)} contexts")
        return contexts
    except Exception as e:
        logger.error(f"Error extracting contexts: {str(e)}")
        raise

async def check_hallucination(
    question: str,
    answer: str,
    contexts: Union[str, List[str]],
    cohere_api_key: str,
    threshold: float = 0.5
) -> float:
    try:
        # Initialize Cohere client
        co = cohere.Client(cohere_api_key)
        
        # Ensure contexts is a list
        if isinstance(contexts, str):
            contexts = [contexts]
            
        # Handle empty or None contexts
        if not contexts or all(not c for c in contexts):
            logger.warning("No valid contexts provided for hallucination check")
            return 0.0

        # Build prompt for validation
        prompt = [
            "Task: You are a balanced fact-checker. Verify if the answer is supported by the provided contexts.",
            "Score from 0 to 1 based on these criteria:",
            "0.0: Complete fabrication or contains clearly false claims",
            "0.4: Contains significant unsupported claims but some accurate information",
            "0.6: Mostly accurate but includes minor details not in context",
            "0.8: Very accurate with minimal unsupported details",
            "1.0: Completely accurate and fully supported by context",
            f"\nQuestion: {question}",
            f"Answer: {answer}",
            "\nContexts:"
        ]
        
        # Add contexts
        for i, ctx in enumerate(contexts, 1):
            if ctx:  # Only add non-empty contexts
                prompt.append(f"\nContext {i}:\n{ctx}")
                
        prompt.append("\nAnalyze the answer's accuracy relative to the contexts.")
        prompt.append("First explain your reasoning, then provide a score (0-1).")

        # Get Nova response for factual validation
        try:
            nova_model = BedrockModel()
            validation_response = await nova_model.query_normalizer("\n".join(prompt), "english")
            
            # Extract score from response
            import re
            numbers = re.findall(r"0\.\d+|\d+", str(validation_response))
            if numbers:
                score = float(numbers[0])
                score = min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
            else:
                # Default to neutral if no score found
                score = 0.5
            
            return score

        except Exception as e:
            logger.error(f"Error in Nova validation: {str(e)}")
            return 0.0

    except Exception as e:
        logger.error(f"Error in hallucination check: {str(e)}")
        return 0.0

async def test_hallucination_guard():
    """Test the hallucination detection functionality"""
    try:
        print("\n=== Testing Hallucination Guard ===")
        load_environment()
        
        # Get API key
        COHERE_API_KEY = os.getenv('COHERE_API_KEY')
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY not found in environment")
        
        # Test cases
        test_cases = [
            {
                'question': 'What is climate change?',
                'answer': 'Climate change is a long-term shift in global weather patterns and temperatures.',
                'context': 'Climate change refers to long-term shifts in temperatures and weather patterns. These shifts may be natural, but since the 1800s, human activities have been the main driver of climate change, primarily due to burning fossil fuels like coal, oil and gas.',
                'expected': 'high score'
            },
            {
                'question': 'What causes climate change?',
                'answer': 'Aliens from Mars are causing climate change by using their heat rays.',
                'context': 'The primary driver of climate change is the burning of fossil fuels, which releases greenhouse gases into the atmosphere.',
                'expected': 'low score'
            },
            {
                'question': 'What is the greenhouse effect?',
                'answer': 'The greenhouse effect is when gases in the atmosphere trap heat.',
                'context': 'The greenhouse effect is a natural process that warms the Earth\'s surface. When the Sun\'s energy reaches the Earth\'s atmosphere, some of it is reflected back to space and some is absorbed and re-radiated by greenhouse gases.',
                'expected': 'medium score'
            }
        ]
        
        for case in test_cases:
            print(f"\nTesting case: {case['question']}")
            print(f"Answer: {case['answer']}")
            print(f"Expected: {case['expected']}")
            
            score = await check_hallucination(
                question=case['question'],
                answer=case['answer'],
                contexts=case['context'],
                cohere_api_key=COHERE_API_KEY
            )
            
            print(f"Faithfulness score: {score:.2f}")
            print('-' * 50)
            
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_hallucination_guard())
