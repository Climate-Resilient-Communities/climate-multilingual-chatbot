import os
import sys
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Import required modules
from src.models.nova_flow import BedrockModel
from src.models.input_guardrail import check_follow_up_with_llm, topic_moderation

async def test_follow_up_integration():
    """Test the follow-up detection integration with topic moderation"""
    try:
        logger.info("Initializing BedrockModel...")
        model = BedrockModel()
        logger.info("Model initialized")
        
        # Test Case: User asking about apartment cooling after a climate question
        print("\n======= INTEGRATION TEST: Topic shift in topic moderation =======")
        
        history = [{
            'query': '多伦多四月下雪和全球变暖有关吗',  # "Is snow in Toronto in April related to global warming?"
            'response': '虽然看起来矛盾，但四月下雪并不否定全球变暖。全球变暖导致天气模式变得不稳定，有时会出现异常寒冷的天气。',  # "Although it seems contradictory..."
            'language_code': 'zh',
            'language_name': 'chinese'
        }]
        
        new_query = '我住在很老的一个租的公寓里夏天很热我怎么办'  
        # "I live in an old rented apartment that gets very hot in summer. What can I do?"
        
        print(f"Previous query: {history[0]['query']}")
        print(f"Previous response: {history[0]['response']}")
        print(f"New query: {new_query}")
        
        # First check with the improved follow-up detection
        follow_up_result = await check_follow_up_with_llm(new_query, history, model)
        print(f"\nFollow-up LLM Classification: {follow_up_result}")
        print(f"Is follow-up: {follow_up_result.get('is_follow_up', False)}")
        print(f"Confidence: {follow_up_result.get('confidence', 0)}")
        
        # Now check topic moderation with follow-up detection integrated
        # We're not passing a topic moderation pipeline here since we just want to test the follow-up part
        topic_result = await topic_moderation(
            query=new_query,
            moderation_pipe=None,
            conversation_history=history,
            nova_model=model
        )
        
        print(f"\nTopic moderation result: {topic_result}")
        
        print("\n======= TESTING TRUE FOLLOW-UP =======")
        follow_up_history = [{
            'query': '全球变暖对北极熊有什么影响？',  # "How does global warming affect polar bears?"
            'response': '全球变暖导致北极冰层融化，使北极熊失去栖息地，影响它们觅食和繁殖。',  # "Global warming causes Arctic ice to melt..."
            'language_code': 'zh',
            'language_name': 'chinese'
        }]
        
        follow_up_query = '还有哪些其他动物受到影响？'  # "What other animals are affected?"
        
        print(f"Previous query: {follow_up_history[0]['query']}")
        print(f"Previous response: {follow_up_history[0]['response']}")
        print(f"Follow-up query: {follow_up_query}")
        
        true_follow_up_result = await check_follow_up_with_llm(follow_up_query, follow_up_history, model)
        print(f"\nFollow-up LLM Classification: {true_follow_up_result}")
        
        # Testing topic moderation for true follow-up
        true_topic_result = await topic_moderation(
            query=follow_up_query,
            moderation_pipe=None,
            conversation_history=follow_up_history,
            nova_model=model
        )
        
        print(f"\nTopic moderation result for true follow-up: {true_topic_result}")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_follow_up_integration())