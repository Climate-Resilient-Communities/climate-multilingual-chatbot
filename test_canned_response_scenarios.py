#!/usr/bin/env python3
"""
Test to verify canned responses are correctly identified and 
export button should be hidden for them
"""

import sys
import os
import json
import asyncio
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.query_rewriter import query_rewriter, CANNED_MAP
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_canned_response_scenarios():
    """Test various scenarios that should trigger canned responses"""
    
    print("=== Testing Canned Response Scenarios ===")
    print("These responses should have retrieval_source='canned' and hide export button\n")
    
    # Load environment
    load_environment()
    
    # Initialize components
    nova_model = BedrockModel()
    
    # Test cases for different canned response types
    test_cases = [
        # Greeting responses
        ("Hello", "greeting", "Should trigger greeting canned response"),
        ("Hi there", "greeting", "Should trigger greeting canned response"),
        ("Good morning", "greeting", "Should trigger greeting canned response"),
        ("Hey", "greeting", "Should trigger greeting canned response"),
        
        # Goodbye responses
        ("Goodbye", "goodbye", "Should trigger goodbye canned response"),
        ("Bye", "goodbye", "Should trigger goodbye canned response"),
        ("See you later", "goodbye", "Should trigger goodbye canned response"),
        ("Take care", "goodbye", "Should trigger goodbye canned response"),
        
        # Thanks responses
        ("Thank you", "thanks", "Should trigger thanks canned response"),
        ("Thanks", "thanks", "Should trigger thanks canned response"),
        ("I appreciate it", "thanks", "Should trigger thanks canned response"),
        
        # Emergency responses (should be canned)
        ("I'm having a heart attack", "emergency", "Should trigger emergency canned response"),
        ("This is a medical emergency", "emergency", "Should trigger emergency canned response"),
        ("I need an ambulance", "emergency", "Should trigger emergency canned response"),
        
        # Instruction responses (how to use)
        ("How do I use this chatbot?", "instruction", "Should trigger instruction canned response"),
        ("Help", "instruction", "Should trigger instruction canned response"),
        ("How does this work?", "instruction", "Should trigger instruction canned response"),
        
        # Non-canned responses (should show export button)
        ("What is climate change?", "on-topic", "Should NOT trigger canned response"),
        ("How does global warming affect Toronto?", "on-topic", "Should NOT trigger canned response"),
        ("Tell me about renewable energy", "on-topic", "Should NOT trigger canned response"),
    ]
    
    canned_count = 0
    non_canned_count = 0
    
    for query, expected_classification, description in test_cases:
        print(f"Testing: '{query}'")
        print(f"Expected: {expected_classification}")
        print(f"Description: {description}")
        
        try:
            # Test with English selected
            result = await query_rewriter(
                conversation_history=[],
                user_query=query,
                nova_model=nova_model,
                selected_language_code="en"
            )
            
            parsed = json.loads(result)
            classification = parsed.get('classification', 'unknown')
            canned_info = parsed.get('canned', {})
            canned_enabled = canned_info.get('enabled', False)
            canned_text = canned_info.get('text', '')
            
            print(f"Result:")
            print(f"  - Classification: {classification}")
            print(f"  - Canned enabled: {canned_enabled}")
            print(f"  - Canned text preview: {canned_text[:50]}{'...' if len(canned_text) > 50 else ''}")
            
            # Check if this matches expected canned response
            expected_canned = expected_classification in ['greeting', 'goodbye', 'thanks', 'emergency', 'instruction']
            
            if expected_canned:
                if canned_enabled:
                    print(f"  ✅ CORRECT: Canned response detected (export button should be HIDDEN)")
                    canned_count += 1
                else:
                    print(f"  ❌ ERROR: Expected canned response but got regular response")
            else:
                if not canned_enabled:
                    print(f"  ✅ CORRECT: Regular response (export button should be SHOWN)")
                    non_canned_count += 1
                else:
                    print(f"  ❌ ERROR: Expected regular response but got canned response")
            
            # Verify classification matches expectation
            if classification == expected_classification:
                print(f"  ✅ Classification matches expectation")
            else:
                print(f"  ⚠️  Classification mismatch: got {classification}, expected {expected_classification}")
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
        
        print()
    
    print("=== SUMMARY ===")
    print(f"Canned responses detected: {canned_count}")
    print(f"Non-canned responses detected: {non_canned_count}")
    print(f"Total test cases: {len(test_cases)}")
    
    print(f"\n=== CANNED RESPONSE TYPES ===")
    print("These response types should hide the export button:")
    for response_type, config in CANNED_MAP.items():
        if config.get('enabled'):
            print(f"- {response_type}: {config.get('type')}")
            print(f"  Text: {config.get('text', '')[:100]}{'...' if len(config.get('text', '')) > 100 else ''}")
    
    print(f"\n=== FRONTEND IMPLEMENTATION ===")
    print("In chat-message.tsx, the export button is hidden when:")
    print("message.retrieval_source === 'canned'")
    print()
    print("The pipeline sets retrieval_source='canned' when:")
    print("- Classification is one of: greeting, goodbye, thanks, emergency, instruction")
    print("- canned_enabled = true in the query rewriter response")

if __name__ == "__main__":
    asyncio.run(test_canned_response_scenarios())