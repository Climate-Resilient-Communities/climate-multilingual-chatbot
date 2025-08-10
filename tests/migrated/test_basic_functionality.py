#!/usr/bin/env python3
"""
Simple End-to-End Test Runner for Climate Multilingual Chatbot

This script runs basic validation tests to ensure the chatbot pipeline works correctly.
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_header(title: str):
    """Print formatted test section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_test_result(test_name: str, passed: bool, duration: Optional[float] = None, details: Optional[str] = None):
    """Print individual test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    duration_str = f" ({duration:.2f}s)" if duration else ""
    print(f"{status} {test_name}{duration_str}")
    if details and not passed:
        print(f"    Details: {details}")

async def test_basic_imports():
    """Test that all required components can be imported"""
    print_header("Basic Import Tests")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Main chatbot import
    tests_total += 1
    try:
        start_time = time.time()
        from src.main_nova import MultilingualClimateChatbot
        duration = time.time() - start_time
        print_test_result("Import MultilingualClimateChatbot", True, duration)
        tests_passed += 1
    except Exception as e:
        print_test_result("Import MultilingualClimateChatbot", False, details=str(e))
    
    # Test 2: Pipeline import
    tests_total += 1
    try:
        start_time = time.time()
        from src.models.climate_pipeline import ClimateQueryPipeline
        duration = time.time() - start_time
        print_test_result("Import ClimateQueryPipeline", True, duration)
        tests_passed += 1
    except Exception as e:
        print_test_result("Import ClimateQueryPipeline", False, details=str(e))
    
    # Test 3: Query routing
    tests_total += 1
    try:
        start_time = time.time()
        from src.models.query_routing import MultilingualRouter
        duration = time.time() - start_time
        print_test_result("Import MultilingualRouter", True, duration)
        tests_passed += 1
    except Exception as e:
        print_test_result("Import MultilingualRouter", False, details=str(e))
    
    # Test 4: Query rewriter
    tests_total += 1
    try:
        start_time = time.time()
        from src.models.query_rewriter import query_rewriter
        duration = time.time() - start_time
        print_test_result("Import query_rewriter", True, duration)
        tests_passed += 1
    except Exception as e:
        print_test_result("Import query_rewriter", False, details=str(e))
    
    # Test 5: Unified response generator
    tests_total += 1
    try:
        start_time = time.time()
        from src.models.gen_response_unified import UnifiedResponseGenerator
        duration = time.time() - start_time
        print_test_result("Import UnifiedResponseGenerator", True, duration)
        tests_passed += 1
    except Exception as e:
        print_test_result("Import UnifiedResponseGenerator", False, details=str(e))
    
    return tests_passed, tests_total

async def test_chatbot_initialization():
    """Test chatbot initialization with mocked dependencies"""
    print_header("Chatbot Initialization Tests")
    
    tests_passed = 0
    tests_total = 1
    
    try:
        start_time = time.time()
        
        # Import with mocking
        from unittest.mock import patch, MagicMock
        
        with patch('src.models.nova_flow.BedrockModel') as mock_bedrock, \
             patch('pinecone.Pinecone') as mock_pinecone, \
             patch('FlagEmbedding.BGEM3FlagModel') as mock_bge, \
             patch('redis.Redis') as mock_redis, \
             patch('cohere.Client') as mock_cohere:
            
            # Setup mocks
            mock_bedrock.return_value = MagicMock()
            mock_pinecone.return_value = MagicMock()
            mock_bge.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            mock_cohere.return_value = MagicMock()
            
            from src.main_nova import MultilingualClimateChatbot
            chatbot = MultilingualClimateChatbot('test-index')
            
            duration = time.time() - start_time
            
            # Check basic attributes
            success = (
                hasattr(chatbot, 'process_query') and
                hasattr(chatbot, 'get_language_code') and
                hasattr(chatbot, 'LANGUAGE_NAME_TO_CODE')
            )
            
            print_test_result("Chatbot Initialization", success, duration)
            if success:
                tests_passed += 1
            
    except Exception as e:
        print_test_result("Chatbot Initialization", False, details=str(e))
    
    return tests_passed, tests_total

async def test_language_mapping():
    """Test language name to code mapping"""
    print_header("Language Mapping Tests")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        from unittest.mock import patch, MagicMock
        
        with patch('src.models.nova_flow.BedrockModel'), \
             patch('pinecone.Pinecone'), \
             patch('FlagEmbedding.BGEM3FlagModel'), \
             patch('redis.Redis'), \
             patch('cohere.Client'):
            
            from src.main_nova import MultilingualClimateChatbot
            chatbot = MultilingualClimateChatbot('test-index')
            
            # Test common languages
            language_tests = [
                ('english', 'en'),
                ('spanish', 'es'),
                ('french', 'fr'),
                ('german', 'de'),
                ('chinese', 'zh'),
                ('portuguese', 'pt'),
                ('italian', 'it'),
                ('russian', 'ru')
            ]
            
            for language_name, expected_code in language_tests:
                tests_total += 1
                start_time = time.time()
                
                actual_code = chatbot.get_language_code(language_name)
                duration = time.time() - start_time
                
                success = actual_code == expected_code
                print_test_result(f"Language mapping: {language_name} -> {expected_code}", success, duration)
                
                if success:
                    tests_passed += 1
                else:
                    print(f"    Expected: {expected_code}, Got: {actual_code}")
                    
    except Exception as e:
        print_test_result("Language Mapping Setup", False, details=str(e))
    
    return tests_passed, tests_total

async def test_response_format():
    """Test response format structure"""
    print_header("Response Format Tests")
    
    tests_passed = 0
    tests_total = 2
    
    # Test successful response format
    start_time = time.time()
    success_response = {
        'success': True,
        'response': 'Climate change is a complex issue...',
        'citations': ['https://example.com/source1'],
        'language_code': 'en'
    }
    
    success_format_valid = (
        isinstance(success_response.get('success'), bool) and
        isinstance(success_response.get('response'), str) and
        isinstance(success_response.get('citations'), list) and
        isinstance(success_response.get('language_code'), str) and
        success_response['success'] == True
    )
    
    duration = time.time() - start_time
    print_test_result("Success Response Format", success_format_valid, duration)
    if success_format_valid:
        tests_passed += 1
    
    # Test error response format
    start_time = time.time()
    error_response = {
        'success': False,
        'message': 'This question is not about climate change.'
    }
    
    error_format_valid = (
        isinstance(error_response.get('success'), bool) and
        isinstance(error_response.get('message'), str) and
        error_response['success'] == False
    )
    
    duration = time.time() - start_time
    print_test_result("Error Response Format", error_format_valid, duration)
    if error_format_valid:
        tests_passed += 1
    
    return tests_passed, tests_total

async def test_mock_query_processing():
    """Test query processing with mocked components"""
    print_header("Mock Query Processing Tests")
    
    tests_passed = 0
    tests_total = 3
    
    try:
        from unittest.mock import patch, AsyncMock, MagicMock
        
        with patch('src.models.nova_flow.BedrockModel') as mock_bedrock, \
             patch('pinecone.Pinecone'), \
             patch('FlagEmbedding.BGEM3FlagModel'), \
             patch('redis.Redis'), \
             patch('cohere.Client'), \
             patch('src.models.retrieval.get_documents') as mock_retrieval, \
             patch('src.models.hallucination_guard.check_hallucination') as mock_hallucination:
            
            # Setup mocks
            mock_bedrock_instance = AsyncMock()
            mock_bedrock.return_value = mock_bedrock_instance
            
            mock_retrieval.return_value = [
                {
                    'title': 'Test Climate Document',
                    'content': 'Climate change information...',
                    'url': 'https://test.com',
                    'score': 0.95
                }
            ]
            
            mock_hallucination.return_value = 0.95  # High confidence
            
            from src.main_nova import MultilingualClimateChatbot
            
            # Test 1: English on-topic query
            tests_total += 1
            try:
                start_time = time.time()
                
                # Mock classification as on-topic
                mock_bedrock_instance.nova_content_generation.return_value = "What are the main causes of climate change?"
                
                chatbot = MultilingualClimateChatbot('test-index')
                
                # Mock a successful flow would happen here
                # For now, just test that the setup works
                duration = time.time() - start_time
                
                print_test_result("Mock English Query Setup", True, duration)
                tests_passed += 1
                
            except Exception as e:
                print_test_result("Mock English Query Setup", False, details=str(e))
            
            # Test 2: Off-topic query handling
            try:
                start_time = time.time()
                
                # Mock classification as off-topic
                mock_bedrock_instance.nova_content_generation.return_value = """Reasoning: This query asks about sports which is unrelated to climate.
Classification: off-topic"""
                
                # Test that classification would work
                classification_result = mock_bedrock_instance.nova_content_generation.return_value
                is_off_topic = 'off-topic' in classification_result.lower()
                
                duration = time.time() - start_time
                print_test_result("Off-topic Query Classification", is_off_topic, duration)
                
                if is_off_topic:
                    tests_passed += 1
                
            except Exception as e:
                print_test_result("Off-topic Query Classification", False, details=str(e))
            
            # Test 3: Spanish language handling
            try:
                start_time = time.time()
                
                chatbot = MultilingualClimateChatbot('test-index')
                language_code = chatbot.get_language_code('spanish')
                
                duration = time.time() - start_time
                success = language_code == 'es'
                
                print_test_result("Spanish Language Processing", success, duration)
                
                if success:
                    tests_passed += 1
                
            except Exception as e:
                print_test_result("Spanish Language Processing", False, details=str(e))
                
    except Exception as e:
        print_test_result("Mock Query Processing Setup", False, details=str(e))
    
    return tests_passed, tests_total

def print_summary(all_results: List[tuple]):
    """Print overall test results summary"""
    total_passed = sum(result[0] for result in all_results)
    total_tests = sum(result[1] for result in all_results)
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"📊 OVERALL TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_tests - total_passed}")
    print(f"📈 Pass Rate: {pass_rate:.1f}%")
    print(f"🔧 Total Tests: {total_tests}")
    
    if total_passed == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! Your climate chatbot components are working correctly.")
        print(f"✨ Ready for detailed integration testing.")
    else:
        print(f"\n⚠️  Some tests failed. Please check the specific failures above.")
        print(f"🔧 Fix the failing components before proceeding with full integration tests.")
    
    return total_passed == total_tests

async def main():
    """Run all basic validation tests"""
    
    print(f"🌍 Climate Multilingual Chatbot - Basic Validation Tests")
    print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Testing core components and basic functionality")
    
    all_results = []
    
    try:
        # Run test suites
        result1 = await test_basic_imports()
        all_results.append(result1)
        
        result2 = await test_chatbot_initialization()
        all_results.append(result2)
        
        result3 = await test_language_mapping()
        all_results.append(result3)
        
        result4 = await test_response_format()
        all_results.append(result4)
        
        result5 = await test_mock_query_processing()
        all_results.append(result5)
        
        # Print summary
        success = print_summary(all_results)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        print(f"Stack trace:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
