#!/usr/bin/env python
"""
Test script to verify the improved topic moderation logic with follow-up questions about Rexdale
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

def print_results(query, result_without_history, result_with_history):
    """Print formatted results for comparison"""
    print(f"\n--- QUERY: {query} ---")
    print(f"WITHOUT HISTORY: {result_without_history['passed']} (Score: {result_without_history['score']:.2f}, Reason: {result_without_history['reason']})")
    print(f"WITH HISTORY: {result_with_history['passed']} (Score: {result_with_history['score']:.2f}, Reason: {result_with_history['reason']})")

async def test_rexdale_queries():
    """Test the sequence of Rexdale-related queries"""
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
        "What is Rexdale climate action plans?",
        "What else are they doing?",
        "How can i help?",
        # Additional test cases
        "Where can I buy new shoes?",
        "Tell me more about their green initiatives",
    ]
    
    # Conversation history grows as we progress
    conversation_history = []
    
    # Test each query in sequence
    for i, query in enumerate(queries):
        # First test without conversation history
        mod_result_without_history = await topic_moderation(
            query=query, 
            moderation_pipe=topic_moderation_pipe
        )
        
        # Then test with conversation history
        mod_result_with_history = await topic_moderation(
            query=query, 
            moderation_pipe=topic_moderation_pipe,
            conversation_history=conversation_history
        )
        
        # Print results
        print_results(query, mod_result_without_history, mod_result_with_history)
        
        # Only generate a response if topic moderation passes
        if mod_result_with_history['passed']:
            try:
                # Generate response
                response = await nova_model.generate_response(
                    query=query,
                    documents=test_docs,
                    description="Provide information about Rexdale climate initiatives",
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
    print("\n=== TEST SUMMARY ===")
    print(f"Total queries tested: {len(queries)}")
    print(f"Conversation history length: {len(conversation_history)}")
    print(f"On-topic queries that received responses: {len(conversation_history)}")
    print(f"Time taken: {time.time() - start_time:.2f} seconds")

    # Show which queries were accepted and which were rejected
    accepted = []
    rejected = []
    
    for i, query in enumerate(queries):
        result = await topic_moderation(
            query=query,
            moderation_pipe=topic_moderation_pipe,
            conversation_history=conversation_history[:i]  # Use history up to but not including current query
        )
        
        if result['passed']:
            accepted.append(query)
        else:
            rejected.append(query)
    
    print("\nAccepted queries:")
    for q in accepted:
        print(f"  ✓ {q}")
        
    print("\nRejected queries:")
    for q in rejected:
        print(f"  ✗ {q}")

if __name__ == "__main__":
    asyncio.run(test_rexdale_queries())