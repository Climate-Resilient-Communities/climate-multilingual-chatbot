import os
import json
import logging
import asyncio
from typing import List, Dict, Union, Optional
from pydantic import BaseModel, Field, field_validator
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

class FaithfulnessEvaluation(BaseModel):
    """Pydantic model for structured faithfulness evaluation responses."""
    faithfulness_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Faithfulness score between 0.0 and 1.0"
    )
    supported_claims: List[str] = Field(
        default_factory=list, 
        description="Claims that are supported by the context"
    )
    unsupported_claims: List[str] = Field(
        default_factory=list, 
        description="Claims that cannot be verified from the context"
    )
    reasoning: str = Field(
        default="", 
        description="Brief explanation of the evaluation"
    )
    
    @field_validator('faithfulness_score')
    @classmethod
    def validate_score(cls, v):
        """Ensure score is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Faithfulness score must be between 0.0 and 1.0, got {v}")
        return v

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
    cohere_api_key: Optional[str] = None,
    threshold: float = 0.7,
    bedrock_model: Optional[BedrockModel] = None
) -> float:
    """Check if the generated answer is faithful to the provided contexts using Nova Lite for speed."""
    try:
        from langsmith import trace
        
        with trace(name="faithfulness_check"):
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            # Use module-level logger
            global logger
            
            # Validate inputs
            if not answer or not question or not contexts:
                logger.warning("Missing required inputs for hallucination check")
                return 0.5  # Return neutral score if inputs are invalid
                
            # Use Nova Lite for faster evaluation; reuse provided model if available
            nova_model = bedrock_model or BedrockModel(model_id="us.amazon.nova-lite-v1:0")
            
            # Prepare the context
            if isinstance(contexts, list):
                combined_context = "\n\n".join(contexts)
            else:
                combined_context = contexts
            
            try:
                # Use Nova Lite for fast LLM-based faithfulness evaluation
                logger.debug("Using Nova Lite for faithfulness evaluation")
                
                # Create a faithful evaluation prompt following RAGAS/SAFE methodology
                evaluation_prompt = f"""You are tasked with evaluating whether a given answer is faithful to the provided context. 

CONTEXT:
{combined_context}

QUESTION: {question}

ANSWER TO EVALUATE: {answer}

Please evaluate the faithfulness by checking if:
1. All factual claims in the answer can be verified from the context
2. The answer does not introduce information not present in the context
3. The answer does not contradict information in the context

You must respond with ONLY a valid JSON object in this exact format:
{{
    "faithfulness_score": <float between 0.0 and 1.0>,
    "supported_claims": [<list of claims supported by context>],
    "unsupported_claims": [<list of claims not supported by context>],
    "reasoning": "<brief explanation of evaluation>"
}}

Important: Return ONLY the JSON object, no other text."""

                # Use Nova Lite for faster response
                response = await asyncio.wait_for(
                    nova_model.content_generation(
                        prompt=evaluation_prompt,
                        system_message="You are an expert evaluator. Respond only with valid JSON."
                    ),
                    timeout=15.0  # Nova Lite is faster, so shorter timeout
                )
                
                if response:
                    try:
                        # Clean and parse the JSON response
                        response_text = response.strip()
                        if response_text.startswith('```json'):
                            response_text = response_text[7:-3].strip()
                        elif response_text.startswith('```'):
                            response_text = response_text[3:-3].strip()
                        
                        # Parse JSON and validate with Pydantic
                        json_data = json.loads(response_text)
                        evaluation = FaithfulnessEvaluation(**json_data)
                        
                        # Log detailed results
                        logger.info(f"Faithfulness score: {evaluation.faithfulness_score}")
                        logger.debug(f"Supported claims: {evaluation.supported_claims}")
                        logger.debug(f"Unsupported claims: {evaluation.unsupported_claims}")
                        logger.debug(f"Reasoning: {evaluation.reasoning}")
                        
                        return evaluation.faithfulness_score
                        
                    except (json.JSONDecodeError, ValueError) as parse_error:
                        # Extract score from text if JSON parsing fails
                        logger.debug(f"JSON parsing failed, extracting score: {str(parse_error)}")
                        import re
                        score_match = re.search(r'(\d+\.?\d*)', response)
                        if score_match:
                            score = float(score_match.group(1))
                            if score > 1.0:  # If score is out of range, normalize it
                                score = score / 100.0 if score <= 100 else 0.5
                            logger.info(f"Extracted faithfulness score: {score}")
                            return max(0.0, min(1.0, score))
                            
            except Exception as eval_error:
                logger.warning(f"Nova Lite faithfulness evaluation failed: {str(eval_error)}")
                
                # Fallback to semantic similarity if available (keep Cohere fallback for embedding)
                if cohere_api_key:
                    try:
                        logger.debug("Falling back to semantic similarity evaluation")
                        import cohere
                        client = cohere.Client(api_key=cohere_api_key)
                        
                        # Get embeddings for answer and context
                        embed_response = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: client.embed(
                                    texts=[answer, combined_context],
                                    model="embed-english-v3.0",
                                    input_type="search_document"
                                )
                            ),
                            timeout=10.0  # Shorter timeout for fallback
                        )
                        
                        if embed_response and hasattr(embed_response, 'embeddings'):
                            import numpy as np
                            
                            # Calculate cosine similarity - handle different embedding response formats
                            embeddings = embed_response.embeddings
                            if hasattr(embeddings, '__iter__') and not isinstance(embeddings, str):
                                # Convert to list if it's iterable
                                embedding_list = list(embeddings)
                                if len(embedding_list) >= 2:
                                    answer_embedding = np.array(embedding_list[0])
                                    context_embedding = np.array(embedding_list[1])
                                else:
                                    logger.warning("Insufficient embeddings returned")
                                    return 0.3
                            else:
                                logger.warning("Embeddings response format not supported")
                                return 0.3
                            
                            similarity = np.dot(answer_embedding, context_embedding) / (
                                np.linalg.norm(answer_embedding) * np.linalg.norm(context_embedding)
                            )
                            
                            # Convert similarity to faithfulness score (semantic similarity as proxy)
                            score = float(max(0.0, min(1.0, similarity)))
                            logger.info(f"Semantic similarity faithfulness score: {score}")
                            return score
                            
                    except Exception as similarity_error:
                        logger.warning(f"Semantic similarity fallback failed: {str(similarity_error)}")
                
            # If all methods fail, return conservative score
            logger.warning("All faithfulness evaluation methods failed, using conservative score")
            return 0.3  # Conservative score indicating potential issues
                    
    except Exception as e:
        logger.error(f"Error in hallucination check: {str(e)}")
        return 0.3  # Return conservative score on error

def evaluate_faithfulness_threshold(score: float, threshold: float = 0.7) -> Dict[str, Union[bool, str, float]]:
    """
    Evaluate faithfulness score against threshold with detailed assessment.
    
    Args:
        score: Faithfulness score between 0.0 and 1.0
        threshold: Minimum acceptable faithfulness score (default: 0.7)
        
    Returns:
        Dictionary with evaluation results
    """
    try:
        is_faithful = score >= threshold
        
        # Provide detailed assessment categories
        if score >= 0.9:
            assessment = "Highly Faithful"
            confidence = "High"
        elif score >= 0.7:
            assessment = "Faithful"
            confidence = "Medium-High"
        elif score >= 0.5:
            assessment = "Moderately Faithful"
            confidence = "Medium"
        elif score >= 0.3:
            assessment = "Potentially Unfaithful"
            confidence = "Low"
        else:
            assessment = "Likely Unfaithful"
            confidence = "Very Low"
            
        return {
            "is_faithful": is_faithful,
            "score": score,
            "threshold": threshold,
            "assessment": assessment,
            "confidence": confidence,
            "recommendation": "Accept" if is_faithful else "Review/Reject"
        }
        
    except Exception as e:
        logger.error(f"Error evaluating faithfulness threshold: {str(e)}")
        return {
            "is_faithful": False,
            "score": 0.0,
            "threshold": threshold,
            "assessment": "Error",
            "confidence": "Unknown",
            "recommendation": "Reject"
        }

async def test_hallucination_guard():
    """Test the hallucination detection functionality with Nova Lite"""
    try:
        print("\n=== Testing Enhanced Hallucination Guard (Nova Lite) ===")
        load_environment()
        
        # Get API key (optional now since we use Nova Lite primarily)
        COHERE_API_KEY = os.getenv('COHERE_API_KEY')  # Only needed for fallback
        
        # Test cases with expected outcomes
        test_cases = [
            {
                'question': 'What is climate change?',
                'answer': 'Climate change is a long-term shift in global weather patterns and temperatures, primarily driven by human activities since the 1800s.',
                'context': 'Climate change refers to long-term shifts in temperatures and weather patterns. These shifts may be natural, but since the 1800s, human activities have been the main driver of climate change, primarily due to burning fossil fuels like coal, oil and gas.',
                'expected': 'high score (>0.8)'
            },
            {
                'question': 'What causes climate change?',
                'answer': 'Aliens from Mars are causing climate change by using their heat rays.',
                'context': 'The primary driver of climate change is the burning of fossil fuels, which releases greenhouse gases into the atmosphere.',
                'expected': 'very low score (<0.2)'
            },
            {
                'question': 'What is the greenhouse effect?',
                'answer': 'The greenhouse effect is when gases in the atmosphere trap heat from the sun.',
                'context': 'The greenhouse effect is a natural process that warms the Earth\'s surface. When the Sun\'s energy reaches the Earth\'s atmosphere, some of it is reflected back to space and some is absorbed and re-radiated by greenhouse gases.',
                'expected': 'good score (0.6-0.8)'
            },
            {
                'question': 'What are renewable energy sources?',
                'answer': 'Nuclear power is the only renewable energy source available.',
                'context': 'Renewable energy sources include solar, wind, hydroelectric, geothermal, and biomass. These sources naturally replenish themselves and are sustainable over time.',
                'expected': 'low score (0.2-0.4) - partially incorrect'
            }
        ]
        
        threshold = 0.7
        for i, case in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i} ---")
            print(f"Question: {case['question']}")
            print(f"Answer: {case['answer']}")
            print(f"Expected: {case['expected']}")
            
            try:
                import time
                start_time = time.time()
                
                score = await check_hallucination(
                    question=case['question'],
                    answer=case['answer'],
                    contexts=case['context'],
                    cohere_api_key=COHERE_API_KEY,
                    threshold=threshold
                )
                
                elapsed_time = time.time() - start_time
                
                # Evaluate against threshold
                evaluation = evaluate_faithfulness_threshold(score, threshold)
                
                print(f"Faithfulness Score: {score:.3f}")
                print(f"Assessment: {evaluation['assessment']}")
                print(f"Confidence: {evaluation['confidence']}")
                print(f"Recommendation: {evaluation['recommendation']}")
                print(f"Passes Threshold ({threshold}): {evaluation['is_faithful']}")
                print(f"⏱️ Response Time: {elapsed_time:.2f}s (Nova Lite)")
                
            except Exception as test_error:
                print(f"Test case failed: {str(test_error)}")
                
            print('-' * 60)
            
        print(f"\n=== Test Complete ===")
        print(f"Using: Nova Lite (faster than Cohere Command-R-Plus)")
        print(f"Threshold used: {threshold} (70% faithfulness required)")
        print("Note: Scores ≥0.7 are considered faithful and acceptable")
            
    except Exception as e:
        print(f"Test suite failed: {str(e)}")
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
