import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

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
        # Get the last conversation turn
        last_turn = conversation_history[-1]
        prev_query = last_turn.get('query', '')
        prev_response = last_turn.get('response', '')
        
        # Create a broader context summary if conversation is longer than 1 turn
        conversation_context = ""
        if len(conversation_history) > 1:
            # Include up to 3 previous turns for context (without overwhelming the prompt)
            context_window = conversation_history[-min(3, len(conversation_history)):]
            context_summary = []
            
            for turn in context_window:
                context_summary.append(f"Q: {turn.get('query', '')}")
                context_summary.append(f"A: {turn.get('response', '')}")
            
            conversation_context = "Previous conversation turns:\n" + "\n".join(context_summary)
        
        # Create a prompt to ask the LLM if the current query is a follow-up to the conversation
        # This works across all languages without requiring hardcoded phrases
        system_message = "You are an AI assistant helping determine if a message is a follow-up question to a previous conversation or if it represents a new topic. Consider the context carefully."
        
        prompt = f"""Most recent question: {prev_query}
Most recent response: {prev_response}
{conversation_context}

Current user message: {query}

Is the current user message a follow-up to the previous conversation on the SAME TOPIC? Answer with YES or NO and explain briefly.
YES means it's related to or building upon the current topic of conversation.
NO means it's a new independent question or topic shift.
"""
        
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
    """Fallback method using simple heuristics when LLM is unavailable."""
    follow_up_indicators = [
        # English
        'else', 'more', 'another', 'additional', 'other', 'also', 'further', 
        'too', 'as well', 'next', 'again', 'they', 'their', 'that', 'this', 
        'those', 'these', 'it', 'them', 'explain', 'elaborate', 'detail',
        'why', 'how', 'what about', 'what if', 'tell me about', 'and', 'but', 'so',

        # Chinese
        '还有', '更多', '另外', '其他', '也', '还', '进一步', 
        '他们', '它们', '那个', '这个', '那些', '这些', '解释', 
        '详述', '详细', '为什么', '怎样', '关于', '那么', '然后', 
        '此外', '另外呢', '那', '所以', '但是', '和', '以及', '而且',
        '如果', '要是', '既然', '既然如此'
    ]
    
    is_follow_up = any(indicator in query.lower() for indicator in follow_up_indicators)
    
    return {
        "is_follow_up": is_follow_up,
        "confidence": 0.6 if is_follow_up else 0.4,
        "reason": "heuristic_fallback"
    }

async def topic_moderation(
    query: str,
    moderation_pipe=None,
    conversation_history: List[Dict] = None,
    nova_model=None
) -> Dict[str, Any]:
    """
    Validate if query is about climate change or is a follow-up question.
    Uses keyword matching and LLM-based follow-up detection.

    Args:
        query (str): The user query
        moderation_pipe: Deprecated, ignored. Kept for call-site compatibility.
        conversation_history (List[Dict], optional): Previous conversation turns
        nova_model: Optional Nova model for LLM operations

    Returns:
        Dict[str, Any]: Result of moderation with passed flag
    """
    try:
        # Lists of climate-related keywords in multiple languages
        climate_keywords = [
            # English
            'climate', 'weather', 'warming', 'carbon', 'emission', 'greenhouse', 
            'temperature', 'ocean', 'sea level', 'energy', 'sustainability',
            'renewable', 'arctic', 'icecap', 'glacier', 'environment', 
            'pollution', 'fossil fuel', 'solar', 'wind power', 'deforestation',
            'biodiversity', 'ecosystem', 'conservation', 'adaptation', 'resilience',
            'methane', 'co2', 'atmosphere',
            
            # Chinese
            '气候', '天气', '变暖', '全球变暖', '碳', '排放', '温室',
            '温度', '海洋', '海平面', '能源', '可持续性', '再生能源',
            '北极', '冰盖', '冰川', '环境', '污染', '化石燃料',
            '太阳能', '风能', '森林砍伐', '生物多样性', '生态系统',
            
            # Spanish
            'clima', 'tiempo', 'calentamiento', 'carbono', 'emisión', 'invernadero',
            'temperatura', 'océano', 'nivel del mar', 'energía', 'sostenibilidad',
            'renovable', 'ártico', 'casquete polar', 'glaciar', 'ambiente', 
            'contaminación', 'combustible fósil', 'solar', 'eólica',
            
            # French
            'climat', 'météo', 'réchauffement', 'carbone', 'émission', 'serre',
            'température', 'océan', 'niveau de la mer', 'énergie', 'durabilité',
            'renouvelable', 'arctique', 'calotte glaciaire', 'glacier', 'environnement',
            'pollution', 'combustible fossile', 'solaire', 'éolienne'
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

if __name__ == "__main__":
    # Test the topic moderation functionality (no ClimateBERT needed)
    import asyncio

    async def test_moderation():
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

        # Test each question independently (keyword-based, no model needed)
        for question in test_questions:
            print(f"\nTesting standalone: {question}")
            topic_result = await topic_moderation(question)
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
        result = await topic_moderation(follow_up, conversation_history=conversation_history)
        print(f"Result with history: {result}")

        result_no_context = await topic_moderation(follow_up)
        print(f"Result without history: {result_no_context}")

        print('-'*50)

    asyncio.run(test_moderation())

