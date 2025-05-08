#!/usr/bin/env python
"""
Test script to verify conversation history handling with a specific scenario:
Initial question about car buying with climate context, followed by a question 
about cars that should only be on-topic in the context of the conversation.
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

# Test documents containing information about cars and climate change
test_docs = [
    {
        'title': 'Electric Vehicles and Climate Change',
        'content': 'Electric vehicles (EVs) can help reduce carbon emissions significantly compared to traditional gasoline-powered cars. By switching to an EV, the average driver can reduce their carbon footprint by about 1.5 tons of CO2 per year. However, the environmental impact varies based on how electricity is generated in the region.',
        'url': ['https://example.com/ev-climate']
    },
    {
        'title': 'Fuel Efficiency Standards',
        'content': 'Fuel efficiency standards have been implemented worldwide to reduce greenhouse gas emissions from vehicles. These standards require car manufacturers to improve the average fuel economy of their fleets, leading to less fuel consumption and fewer emissions per mile driven.',
        'url': ['https://example.com/fuel-standards']
    },
    {
        'title': 'Car Buying Guide for Climate-Conscious Consumers',
        'content': 'When buying a car with climate impact in mind, consider electric vehicles, hybrids, or high-efficiency gasoline models. Consider the total lifecycle emissions, including manufacturing and disposal. Used vehicles may sometimes have a lower overall carbon footprint than new ones depending on usage patterns.',
        'url': ['https://example.com/climate-car-buying']
    }
]

async def test_car_conversation():
    """Test conversation history with car-related questions."""
    start_time = time.time()
    
    # Initialize Nova model
    load_environment()
    nova_model = BedrockModel()
    logger.info("Nova model initialized")

    # Get topic moderation pipeline from the main program
    from transformers import pipeline
    from src.models.input_guardrail import initialize_models
    topic_moderation_pipe, _ = initialize_models()
    
    # First query with explicit climate context
    query_1 = "What should I consider when buying a car if I'm concerned about climate change?"
    logger.info(f"FIRST QUERY: {query_1}")
    
    # Empty conversation history for first turn
    conversation_history = []
    
    try:
        # First check if query is on-topic
        mod_result_1 = await topic_moderation(
            query=query_1, 
            moderation_pipe=topic_moderation_pipe
        )
        logger.info(f"First query moderation result: {mod_result_1}")
        
        if mod_result_1['passed']:
            # Generate first response
            response_1 = await nova_model.generate_response(
                query=query_1,
                documents=test_docs,
                description="Provide specific information about climate considerations when buying cars",
                conversation_history=conversation_history
            )
            
            logger.info(f"RESPONSE 1 (excerpt): {response_1[:300]}...")
            
            # Update conversation history
            conversation_history.append({
                'query': query_1,
                'response': response_1
            })
            
            # Second query that references cars but without explicit climate context
            query_2 = "What is the most environmentally friendly type of car to buy?"
            logger.info(f"SECOND QUERY: {query_2}")
            
            # Check if query is on-topic WITH conversation history
            mod_result_2_with_history = await topic_moderation(
                query=query_2, 
                moderation_pipe=topic_moderation_pipe,
                conversation_history=conversation_history
            )
            logger.info(f"Second query moderation WITH conversation history: {mod_result_2_with_history}")
            
            # Check if query is on-topic WITHOUT conversation history
            mod_result_2_without_history = await topic_moderation(
                query=query_2, 
                moderation_pipe=topic_moderation_pipe
            )
            logger.info(f"Second query moderation WITHOUT conversation history: {mod_result_2_without_history}")
            
            if mod_result_2_with_history['passed']:
                # Generate second response with updated conversation history
                response_2 = await nova_model.generate_response(
                    query=query_2,
                    documents=test_docs,
                    description="Provide specific information about environmental aspects of cars",
                    conversation_history=conversation_history
                )
                
                logger.info(f"RESPONSE 2 (excerpt): {response_2[:300]}...")
                
                # Third query with even less explicit climate context
                query_3 = "What about hybrid vs fully electric cars?"
                logger.info(f"THIRD QUERY: {query_3}")
                
                # Update conversation history
                conversation_history.append({
                    'query': query_2,
                    'response': response_2
                })
                
                # Check if third query is on-topic WITH conversation history
                mod_result_3_with_history = await topic_moderation(
                    query=query_3, 
                    moderation_pipe=topic_moderation_pipe,
                    conversation_history=conversation_history
                )
                logger.info(f"Third query moderation WITH conversation history: {mod_result_3_with_history}")
                
                # Check if third query is on-topic WITHOUT conversation history
                mod_result_3_without_history = await topic_moderation(
                    query=query_3, 
                    moderation_pipe=topic_moderation_pipe
                )
                logger.info(f"Third query moderation WITHOUT conversation history: {mod_result_3_without_history}")
                
                if mod_result_3_with_history['passed']:
                    # Generate third response with updated conversation history
                    response_3 = await nova_model.generate_response(
                        query=query_3,
                        documents=test_docs,
                        description="Compare hybrid and electric cars in terms of environmental impact",
                        conversation_history=conversation_history
                    )
                    
                    logger.info(f"RESPONSE 3 (excerpt): {response_3[:300]}...")
                    
                    # Summary of conversation test results
                    logger.info("\n=== CONVERSATION TEST SUMMARY ===")
                    logger.info(f"Query 1 on-topic: {mod_result_1['passed']}")
                    logger.info(f"Query 2 on-topic with history: {mod_result_2_with_history['passed']}")
                    logger.info(f"Query 2 on-topic without history: {mod_result_2_without_history['passed']}")
                    logger.info(f"Query 3 on-topic with history: {mod_result_3_with_history['passed']}")
                    logger.info(f"Query 3 on-topic without history: {mod_result_3_without_history['passed']}")
                    
                    if (mod_result_2_with_history['passed'] and not mod_result_2_without_history['passed']) or \
                       (mod_result_3_with_history['passed'] and not mod_result_3_without_history['passed']):
                        logger.info("SUCCESS: Conversation history is working correctly! Context was maintained for follow-up questions.")
                    else:
                        logger.info("NOTE: Both with and without history passed moderation - this may be expected if the queries contain climate keywords.")
                else:
                    logger.warning("FAILURE: Third query failed moderation even with conversation history.")
            else:
                logger.warning("FAILURE: Second query failed moderation even with conversation history.")
        else:
            logger.warning("FAILURE: First query failed moderation. Check test queries and moderation settings.")
    except Exception as e:
        logger.error(f"Error during conversation test: {str(e)}")
    
    logger.info(f"Total test time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(test_car_conversation())