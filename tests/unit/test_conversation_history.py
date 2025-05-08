#!/usr/bin/env python
"""
Test script to validate conversation history handling in the gen_response_nova module.
This script simulates a two-turn conversation to check if context from previous
turns is properly maintained.
"""

import asyncio
import logging
import time
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test documents containing information about Rexdale
test_docs = [
    {
        'title': 'Rexdale Community Climate Initiatives',
        'content': 'Rexdale is a neighborhood in Toronto that has started several community-led climate initiatives. These include tree planting programs, community gardens, and educational workshops about sustainable living practices. The Rexdale Community Hub coordinates many of these environmental programs.',
        'url': ['https://example.com/rexdale-climate']
    },
    {
        'title': 'Toronto Neighborhood Climate Action',
        'content': 'Several Toronto neighborhoods are implementing climate action plans. Rexdale has established a green energy cooperative that allows residents to invest in renewable energy projects. The community also hosts regular cleanup events for local parks and waterways.',
        'url': ['https://example.com/toronto-neighborhoods']
    },
    {
        'title': 'Urban Climate Resilience',
        'content': 'Urban communities across Canada are developing climate resilience strategies. Communities like Rexdale are focusing on green infrastructure, including permeable pavements, rain gardens, and native plant landscaping to reduce urban heat island effects and manage stormwater.',
        'url': ['https://example.com/urban-resilience']
    }
]

async def test_conversation_history():
    """Test conversation history handling in gen_response_nova."""
    start_time = time.time()
    
    # Initialize Nova model
    load_environment()
    nova_model = BedrockModel()
    logger.info("Nova model initialized")
    
    # Test description
    description = "Provide specific information about community initiatives mentioned in previous conversation turns."
    
    # First query
    query_1 = "What is Rexdale doing for climate change?"
    logger.info(f"FIRST QUERY: {query_1}")
    
    # Empty conversation history for first turn
    conversation_history = []
    
    try:
        # Generate first response
        response_1 = await nova_model.generate_response(
            query=query_1,
            documents=test_docs,
            description=description,
            conversation_history=conversation_history
        )
        
        logger.info(f"RESPONSE 1: {response_1}")
        
        # Update conversation history
        conversation_history.append({
            'query': query_1,
            'response': response_1
        })
        
        # Second query that references previous content without explicitly mentioning Rexdale
        query_2 = "What else is this community doing for climate change?"
        logger.info(f"SECOND QUERY: {query_2}")
        
        # Generate second response with updated conversation history
        response_2 = await nova_model.generate_response(
            query=query_2,
            documents=test_docs,
            description=description,
            conversation_history=conversation_history
        )
        
        logger.info(f"RESPONSE 2: {response_2}")
        
        # Check if the second response contains "Rexdale" to verify conversation context is maintained
        if "Rexdale" in response_2:
            logger.info("SUCCESS: Conversation history is working correctly! The second response maintains context about Rexdale.")
        else:
            logger.warning("FAILURE: Conversation history may not be working correctly. The second response does not mention Rexdale.")
        
    except Exception as e:
        logger.error(f"Error during conversation test: {str(e)}")
    
    logger.info(f"Total processing time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(test_conversation_history())