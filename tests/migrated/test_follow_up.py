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
from src.models.input_guardrail import check_follow_up_with_llm

async def test_follow_up_detection():
    """Test the LLM-based follow-up detection with Chinese conversation examples"""
    try:
        logger.info("Initializing BedrockModel...")
        model = BedrockModel()
        logger.info("Model initialized")
        
        # Test Case 1: User asking about government responsibility after a climate question
        print("\n======= TEST CASE 1: Topic shift from snow to government responsibility =======")
        
        history1 = [{
            'query': '多伦多四月下雪和全球变暖有关吗',  # "Is snow in Toronto in April related to global warming?"
            'response': '虽然看起来矛盾，但四月下雪并不否定全球变暖。全球变暖导致天气模式变得不稳定，有时会出现异常寒冷的天气。',  # "Although it seems contradictory, snow in April doesn't negate global warming..."
            'language_code': 'zh',
            'language_name': 'chinese'
        }]
        
        new_query1 = '这都是说个人能做什么但是这是政府的职责。 我们怎么能叫他们负责任'  
        # "This is all about what individuals can do, but it's the government's responsibility. How can we hold them accountable?"
        
        print(f"Previous query: {history1[0]['query']}")
        print(f"Previous response: {history1[0]['response']}")
        print(f"New query: {new_query1}")
        
        result1 = await check_follow_up_with_llm(new_query1, history1, model)
        print(f"\nLLM Classification: {result1}\n")
        print(f"Is follow-up: {result1.get('is_follow_up', False)}")
        print(f"Confidence: {result1.get('confidence', 0)}")
        print(f"LLM result: {result1.get('llm_result', '')}")
        
        
        # Test Case 2: User asking about apartment cooling after a climate vs weather question
        print("\n======= TEST CASE 2: Topic shift from climate/weather to apartment cooling =======")
        
        history2 = [{
            'query': '气候变化和天气有什么区别',  # "What's the difference between climate change and weather?"
            'response': '气候是长期的天气模式，而天气是短期的大气状况。气候变化是指长期气候模式的变化。',  # "Climate is long-term weather patterns, while weather is short-term atmospheric conditions..."
            'language_code': 'zh',
            'language_name': 'chinese'
        }]
        
        new_query2 = '我住在很老的一个租的公寓里夏天很热我怎么办'  
        # "I live in an old rented apartment that gets very hot in summer. What can I do?"
        
        print(f"Previous query: {history2[0]['query']}")
        print(f"Previous response: {history2[0]['response']}")
        print(f"New query: {new_query2}")
        
        result2 = await check_follow_up_with_llm(new_query2, history2, model)
        print(f"\nLLM Classification: {result2}\n")
        print(f"Is follow-up: {result2.get('is_follow_up', False)}")
        print(f"Confidence: {result2.get('confidence', 0)}")
        print(f"LLM result: {result2.get('llm_result', '')}")
        
        
        # Test Case 3: Clear follow-up in Chinese
        print("\n======= TEST CASE 3: Clear follow-up question in Chinese =======")
        
        history3 = [{
            'query': '全球变暖对北极熊有什么影响？',  # "How does global warming affect polar bears?"
            'response': '全球变暖导致北极冰层融化，使北极熊失去栖息地，影响它们觅食和繁殖。',  # "Global warming causes Arctic ice to melt, depriving polar bears of their habitat..."
            'language_code': 'zh',
            'language_name': 'chinese'
        }]
        
        new_query3 = '还有哪些其他动物受到影响？'  # "What other animals are affected?"
        
        print(f"Previous query: {history3[0]['query']}")
        print(f"Previous response: {history3[0]['response']}")
        print(f"New query: {new_query3}")
        
        result3 = await check_follow_up_with_llm(new_query3, history3, model)
        print(f"\nLLM Classification: {result3}\n")
        print(f"Is follow-up: {result3.get('is_follow_up', False)}")
        print(f"Confidence: {result3.get('confidence', 0)}")
        print(f"LLM result: {result3.get('llm_result', '')}")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        raise
        

if __name__ == "__main__":
    asyncio.run(test_follow_up_detection())