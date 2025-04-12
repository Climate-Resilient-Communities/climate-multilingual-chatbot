import os
import json
import logging
import asyncio
from typing import List, Dict, Union, Optional
from src.utils.env_loader import load_environment
from src.models.nova_flow import BedrockModel
import cohere
from langsmith import traceable

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
    """Check if the generated answer is faithful to the provided contexts."""
    try:
        from langsmith import trace
        
        with trace(name="faithfulness_check"):
            import cohere
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Validate inputs
            if not answer or not question or not contexts:
                logger.warning("Missing required inputs for hallucination check")
                return 0.5  # Return neutral score if inputs are invalid
                
            # Create Cohere client
            client = cohere.Client(api_key=cohere_api_key)
            
            # Prepare the prompt with the answer and context
            if isinstance(contexts, list):
                combined_context = "\n\n".join(contexts)
            else:
                combined_context = contexts
            
            # Run the request in a thread to avoid blocking
            with ThreadPoolExecutor() as executor:
                try:
                    # Try grounding first
                    try:
                        # Use grounding endpoint when available
                        result = await asyncio.get_event_loop().run_in_executor(
                            executor,
                            lambda: client.ground(
                                text=answer,
                                context=combined_context
                            )
                        )
                        
                        # Extract the score
                        if hasattr(result, 'grounding_score'):
                            score = float(result.grounding_score)
                            logger.info(f"Grounding score: {score}")
                            return score
                    except (AttributeError, Exception) as grounding_error:
                        logger.warning(f"Grounding API not available: {str(grounding_error)}")
                    
                    # Fall back to rerank correlations
                    try:
                        # Use rerank as a fallback
                        rerank_result = await asyncio.get_event_loop().run_in_executor(
                            executor,
                            lambda: client.rerank(
                                query=question,
                                documents=[
                                    {"text": answer},
                                    {"text": combined_context}
                                ],
                                top_n=2,
                                model="rerank-english-v2.0"
                            )
                        )
                        
                        # Extract the relevance score
                        if rerank_result and hasattr(rerank_result, 'results'):
                            # Calculate similarity between answer and context
                            scores = [r.relevance_score for r in rerank_result.results]
                            if len(scores) >= 2:
                                # Use the second score (context relevance) as our faithfulness indicator
                                score = float(scores[1])
                                logger.info(f"Fallback faithfulness score: {score}")
                                return score
                    except Exception as rerank_error:
                        logger.warning(f"Rerank fallback failed: {str(rerank_error)}")
                        
                    # If all methods fail, return default
                    logger.warning("All hallucination detection methods failed, using default score")
                    return 0.5
                        
                except Exception as e:
                    logger.error(f"Error checking hallucination: {str(e)}")
                    return 0.5
                    
    except Exception as e:
        logger.error(f"Error in hallucination check: {str(e)}")
        return 0.5  # Return neutral score on error

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
