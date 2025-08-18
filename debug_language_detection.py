#!/usr/bin/env python3
"""
Debug script to reproduce the language detection bug.
Based on user report: English query "What is toronto doing for climate change?" 
being detected as Portuguese (pt) causing HTTP 500 error.
"""

import sys
import os
import json
import asyncio
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.query_routing import MultilingualRouter
from src.models.query_rewriter import query_rewriter
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_language_detection_bug():
    """Test the specific bug case reported by user."""
    
    # Load environment
    load_environment()
    
    # Initialize components
    router = MultilingualRouter()
    nova_model = BedrockModel()
    
    # Test query from user's report
    test_query = "What is toronto doing for climate change?"
    
    print(f"\n=== DEBUG: Language Detection Bug ===")
    print(f"Query: '{test_query}'")
    print(f"Length: {len(test_query)}")
    
    # Test 1: MultilingualRouter language detection
    print(f"\n--- Step 1: Router Language Detection ---")
    try:
        language_info = router.detect_language(test_query)
        print(f"Router detection result: {json.dumps(language_info, indent=2)}")
    except Exception as e:
        print(f"Router detection error: {e}")
    
    # Test 2: Router simple detection method
    print(f"\n--- Step 2: Router Simple Detection ---")
    try:
        simple_code = router._detect_language_code_simple(test_query)
        print(f"Simple detection code: {simple_code}")
        
        # Test English heuristic
        is_english = router._is_probably_english(test_query)
        print(f"Is probably English: {is_english}")
        
        # Test non-English heuristic  
        is_non_english = router._is_probably_non_english(test_query)
        print(f"Is probably non-English: {is_non_english}")
        
    except Exception as e:
        print(f"Simple detection error: {e}")
    
    # Test 3: Query rewriter with different language settings
    print(f"\n--- Step 3: Query Rewriter Tests ---")
    
    # Test case 1: English selected (normal case)
    print(f"\nTest 3a: English selected")
    try:
        result_en = await query_rewriter(
            conversation_history=[],
            user_query=test_query,
            nova_model=nova_model,
            selected_language_code="en"
        )
        parsed_en = json.loads(result_en)
        print(f"English selected result:")
        print(f"  - Detected language: {parsed_en.get('language')}")
        print(f"  - Expected language: {parsed_en.get('expected_language')}")
        print(f"  - Language match: {parsed_en.get('language_match')}")
        print(f"  - Classification: {parsed_en.get('classification')}")
    except Exception as e:
        print(f"Query rewriter (English) error: {e}")
    
    # Test case 2: Portuguese selected (bug case)
    print(f"\nTest 3b: Portuguese selected (reproducing bug)")
    try:
        result_pt = await query_rewriter(
            conversation_history=[],
            user_query=test_query,
            nova_model=nova_model,
            selected_language_code="pt"
        )
        parsed_pt = json.loads(result_pt)
        print(f"Portuguese selected result:")
        print(f"  - Detected language: {parsed_pt.get('language')}")
        print(f"  - Expected language: {parsed_pt.get('expected_language')}")
        print(f"  - Language match: {parsed_pt.get('language_match')}")
        print(f"  - Classification: {parsed_pt.get('classification')}")
        print(f"  - Message: {parsed_pt.get('message', 'No message')}")
        
        # This should trigger the language mismatch logic
        if not parsed_pt.get('language_match'):
            print(f"🚨 LANGUAGE MISMATCH DETECTED! This reproduces the bug.")
            print(f"Expected: pt, Detected: {parsed_pt.get('language')}")
        
    except Exception as e:
        print(f"Query rewriter (Portuguese) error: {e}")
    
    # Test 4: Test with conversation history (user's context)
    print(f"\n--- Step 4: With Conversation History ---")
    
    # Simulate conversation history that might cause confusion
    history_with_portuguese = [
        "Olá, como está?",  # Portuguese greeting
        "Hi, I'm doing well, thank you!",  # English response
        "What is the weather like in Toronto?"  # Previous English query
    ]
    
    try:
        result_with_history = await query_rewriter(
            conversation_history=history_with_portuguese,
            user_query=test_query,
            nova_model=nova_model,
            selected_language_code="en"  # User has English selected
        )
        parsed_history = json.loads(result_with_history)
        print(f"With Portuguese history result:")
        print(f"  - Detected language: {parsed_history.get('language')}")
        print(f"  - Expected language: {parsed_history.get('expected_language')}")
        print(f"  - Language match: {parsed_history.get('language_match')}")
        print(f"  - Classification: {parsed_history.get('classification')}")
        
    except Exception as e:
        print(f"Query rewriter (with history) error: {e}")
    
    print(f"\n=== Debug Complete ===")

if __name__ == "__main__":
    asyncio.run(test_language_detection_bug())