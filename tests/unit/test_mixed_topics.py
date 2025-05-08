#!/usr/bin/env python
"""
Test script to verify how the system handles a sequence of climate and non-climate related queries,
checking if the topic moderation correctly identifies which questions are on-topic.
"""
import asyncio
import logging
import time
from src.models.nova_flow import BedrockModel
from src.models.input_guardrail import topic_moderation
from src.utils.env_loader import load_environment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test documents containing information about climate change
test_docs = [
    {
        'title': 'Climate Change Overview',
        'content': 'Climate change refers to long-term shifts in temperatures and weather patterns. Human activities have been the main driver of climate change, primarily due to burning fossil fuels like coal, oil and gas, which produces heat-trapping gases.',
        'url': ['https://example.com/climate-overview']
    },
    {
        'title': 'Community Climate Action',
        'content': 'Communities can address climate change through local initiatives like tree planting, community gardens, and advocating for sustainable policies. Educational workshops help raise awareness about climate issues and empower residents to take action.',
        'url': ['https://example.com/community-action']
    }
]

async def test_mixed_topics():
    """Test a sequence of climate and non-climate related questions."""
    start_time = time.time()
    
    # Initialize Nova model
    load_environment()
    nova_model = BedrockModel()
    logger.info("Nova model initialized")

    # Get topic moderation pipeline
    from src.models.input_guardrail import initialize_models
    topic_moderation_pipe, _ = initialize_models()
    
    # Define the sequence of questions to test
    queries = [
        "What is climate change?",
        "How can I buy a car?",
        "Where can I get new clothes to go out with a friend?",
        "How can I help my community with climate change?"
    ]
    
    # Conversation history grows as we progress
    conversation_history = []
    
    # Test each question in sequence
    for i, query in enumerate(queries):
        logger.info(f"\n--- QUERY {i+1}: {query} ---")
        
        # First test without conversation history
        mod_result_without_history = await topic_moderation(
            query=query, 
            moderation_pipe=topic_moderation_pipe
        )
        logger.info(f"Moderation WITHOUT conversation history: {mod_result_without_history}")
        
        # Then test with conversation history
        mod_result_with_history = await topic_moderation(
            query=query, 
            moderation_pipe=topic_moderation_pipe,
            conversation_history=conversation_history
        )
        logger.info(f"Moderation WITH conversation history: {mod_result_with_history}")
        
        # Only generate a response if topic moderation passes
        if mod_result_with_history['passed']:
            try:
                # Generate response
                response = await nova_model.generate_response(
                    query=query,
                    documents=test_docs,
                    description="Provide climate-related information",
                    conversation_history=conversation_history
                )
                
                # Add to conversation history
                conversation_history.append({
                    'query': query,
                    'response': response
                })
                
                logger.info(f"RESPONSE (excerpt): {response[:150]}...")
                
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
        else:
            logger.warning(f"Query failed topic moderation: {query}")
            logger.info("No response generated - query is off-topic")
    
    # Summary 
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"Total queries tested: {len(queries)}")
    logger.info(f"Conversation history length: {len(conversation_history)}")
    logger.info(f"On-topic queries that received responses: {len(conversation_history)}")
    logger.info(f"Time taken: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(test_mixed_topics())