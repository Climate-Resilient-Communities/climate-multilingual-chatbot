#!/usr/bin/env python
"""
Debug script to test the integration between main_nova.py and the fixed input_guardrail.py
for handling follow-up questions in a conversation context.
"""
import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from src.main_nova import MultilingualClimateChatbot
from src.models.input_guardrail import topic_moderation
from src.utils.env_loader import load_environment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_input_guardrail_integration():
    """Test that main_nova correctly uses the updated input_guardrail logic."""
    load_environment()
    
    # Initialize chatbot
    print("\nInitializing Climate Chatbot...")
    chatbot = MultilingualClimateChatbot("climate-change-adaptation-index-10-24-prod")
    print("✓ Initialization complete\n")
    
    # Get topic moderation pipeline directly for comparison
    topic_moderation_pipe = chatbot.topic_moderation_pipe
    
    # Test queries
    test_sequences = [
        # Test sequence 1 - Climate followed by follow-up
        [
            "What is climate change?",
            "What else should I know?"
        ],
        
        # Test sequence 2 - Rexdale climate initiatives followed by follow-ups
        [
            "What climate initiatives are happening in Rexdale?",
            "What else are they doing?",
            "How can I help?"
        ],
        
        # Test sequence 3 - Starting with climate but then asking shopping question
        [
            "How does climate change impact coastal cities?",
            "Where can I buy new shoes?"
        ]
    ]
    
    # Run tests for each conversation sequence
    for seq_idx, sequence in enumerate(test_sequences):
        print(f"\n{'='*80}")
        print(f"TEST SEQUENCE {seq_idx + 1}")
        print(f"{'='*80}")
        
        # Initialize conversation history for each sequence
        conversation_history = []
        
        # Process each query in the sequence
        for i, query in enumerate(sequence):
            print(f"\n--- Query {i+1}: {query}")
            
            # First test with the direct topic_moderation function
            print("\nDirect topic_moderation test:")
            
            # Without conversation history
            result_without_history = await topic_moderation(
                query=query,
                moderation_pipe=topic_moderation_pipe
            )
            print(f"WITHOUT history: {result_without_history}")
            
            # With conversation history
            result_with_history = await topic_moderation(
                query=query,
                moderation_pipe=topic_moderation_pipe,
                conversation_history=conversation_history
            )
            print(f"WITH history: {result_with_history}")
            
            # Now test using the chatbot's process_input_guards method
            print("\nChatbot process_input_guards test:")
            
            guardrail_result = await chatbot.process_input_guards(query)
            print(f"Guardrail result without history: {guardrail_result}")
            
            # Now process the query through the actual chatbot process_query method
            print("\nFull chatbot processing:")
            result = await chatbot.process_query(
                query=query,
                language_name="english",
                conversation_history=conversation_history
            )
            
            if result.get('success', False):
                # Add the successfully processed query to conversation history
                if result.get('current_turn'):
                    conversation_history.append(result['current_turn'])
                    print(f"Added to conversation history. History length: {len(conversation_history)}")
                
                response_snippet = result['response'][:150] + "..." if len(result['response']) > 150 else result['response']
                print(f"\nResponse (excerpt): {response_snippet}")
            else:
                # Handle rejection
                print(f"\nQuery rejected: {result.get('message', 'Unknown error')}")
                if result.get('validation_result'):
                    print(f"Validation result: {result['validation_result']}")
    
    # Clean up
    await chatbot.cleanup()
    print("\nTest completed and resources cleaned up successfully")

if __name__ == "__main__":
    asyncio.run(verify_input_guardrail_integration())