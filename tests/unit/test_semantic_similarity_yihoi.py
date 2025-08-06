#!/usr/bin/env python3
"""
Test script for the new semantic similarity functionality in input guardrail.
This tests specifically the cases that should now pass with the enhanced system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.input_guardrail import initialize_models, topic_moderation

async def test_semantic_similarity():
    """Test the enhanced semantic similarity functionality."""
    
    print("🚀 Testing Enhanced Input Guardrail with Semantic Similarity")
    print("=" * 60)
    
    try:
        # Initialize models
        print("Initializing models...")
        topic_moderation_pipe, similarity_model = initialize_models()
        
        if similarity_model is None:
            print("❌ Warning: Similarity model failed to initialize. Only testing with ClimateBERT.")
        else:
            print("✅ Successfully initialized both ClimateBERT and sentence transformer models")
        
        # Test cases that should now pass with semantic similarity
        test_cases = [
            # Previously failing cases that should now pass
            {
                "query": "What is the pH of ocean water?",
                "expectation": "SHOULD PASS",
                "reason": "pH is related to ocean acidification from climate change"
            },
            {
                "query": "How do rivers affect the environment?", 
                "expectation": "SHOULD PASS",
                "reason": "Rivers are part of the water cycle affected by climate change"
            },
            {
                "query": "Tell me about coral reefs",
                "expectation": "SHOULD PASS", 
                "reason": "Coral reefs are heavily impacted by climate change"
            },
            {
                "query": "What happens to ice when temperature rises?",
                "expectation": "SHOULD PASS",
                "reason": "Ice melting is a key climate change indicator"
            },
            {
                "query": "How does farming change with weather patterns?",
                "expectation": "SHOULD PASS",
                "reason": "Agriculture adaptation to climate change"
            },
            {
                "query": "What are the effects on marine species?",
                "expectation": "SHOULD PASS",
                "reason": "Marine biodiversity impacts from climate change"
            },
            
            # Edge cases
            {
                "query": "Precipitation patterns in my region",
                "expectation": "SHOULD PASS",
                "reason": "Precipitation changes are climate-related"
            },
            {
                "query": "森林如何影响大气？",  # Chinese: How do forests affect the atmosphere?
                "expectation": "SHOULD PASS",
                "reason": "Multilingual climate query about forests and atmosphere"
            },
            
            # Should still fail
            {
                "query": "Where can I buy new shoes?",
                "expectation": "SHOULD FAIL",
                "reason": "Shopping query, not climate-related"
            },
            {
                "query": "What's the best smartphone to buy?",
                "expectation": "SHOULD FAIL", 
                "reason": "Technology shopping, not climate-related"
            },
        ]
        
        print(f"\nTesting {len(test_cases)} cases:")
        print("-" * 60)
        
        passed_tests = 0
        failed_tests = 0
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expectation = test_case["expectation"]
            reason = test_case["reason"]
            
            print(f"\n{i}. Testing: '{query}'")
            print(f"   Expected: {expectation}")
            print(f"   Reason: {reason}")
            
            # Run the topic moderation
            result = await topic_moderation(
                query, 
                topic_moderation_pipe, 
                similarity_model=similarity_model
            )
            
            passed = result.get("passed", False)
            score = result.get("score", 0.0)
            detection_reason = result.get("reason", "unknown")
            
            # Check if result matches expectation
            expected_pass = expectation == "SHOULD PASS"
            test_passed = (passed == expected_pass)
            
            if test_passed:
                status = "✅ PASS"
                passed_tests += 1
            else:
                status = "❌ FAIL"
                failed_tests += 1
            
            print(f"   Result: {status} - Query {'PASSED' if passed else 'FAILED'} moderation")
            print(f"   Score: {score:.3f}, Detection: {detection_reason}")
        
        print("\n" + "=" * 60)
        print(f"📊 Test Summary:")
        print(f"   ✅ Passed: {passed_tests}/{len(test_cases)}")
        print(f"   ❌ Failed: {failed_tests}/{len(test_cases)}")
        print(f"   Success Rate: {(passed_tests/len(test_cases)*100):.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! The semantic similarity enhancement is working correctly.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Review the results above.")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_semantic_similarity())
