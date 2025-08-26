#!/usr/bin/env python3
"""
Simple test script to verify FORCE_COMMAND_A_RESPONSES override functionality.
Tests a few key languages to ensure the override works.
"""

import os
import sys
import asyncio
import logging
import time

# Set up logging to capture override messages clearly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, 'src')

from models.climate_pipeline import ClimateQueryPipeline

async def test_query(pipeline, query, lang_name, test_name):
    """Test a single query and report results."""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"Query: {query}")
    print(f"Language: {lang_name}")
    print('='*60)
    
    start_time = time.time()
    
    try:
        result = await pipeline.process_query(
            query=query,
            language_name=lang_name
        )
        
        duration = time.time() - start_time
        
        if result.get('success'):
            response = result.get('response', '')
            print(f"✅ SUCCESS ({duration:.2f}s)")
            print(f"Response preview: {response[:200]}...")
            return True
        else:
            print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        return False

async def main():
    """Main test function."""
    
    # Check override status
    force_command_a = os.getenv('FORCE_COMMAND_A_RESPONSES', '').lower() in ('true', '1', 'yes')
    
    print("🚀 COMMAND A OVERRIDE TEST")
    print(f"Override Status: {'🟢 ENABLED' if force_command_a else '🔴 DISABLED'}")
    
    if force_command_a:
        print("⚠️  All responses should use Command A model")
        print("💡 Look for override messages in logs: '⚠️ Overriding model selection'")
    else:
        print("ℹ️  Using default routing (English→Nova, others as configured)")
    
    print("\nInitializing pipeline...")
    pipeline = ClimateQueryPipeline()
    
    # Test cases: languages that normally route to Nova (should be overridden)
    test_cases = [
        {
            'query': 'What are the main causes of climate change?',
            'lang_name': 'English',
            'test_name': 'TEST 1: English (normally routes to Nova)'
        },
        {
            'query': '¿Cuáles son las principales causas del cambio climático?',
            'lang_name': 'Spanish',
            'test_name': 'TEST 2: Spanish (normally routes to Nova)'
        },
        {
            'query': 'Quelles sont les principales causes du changement climatique?',
            'lang_name': 'French', 
            'test_name': 'TEST 3: French (normally routes to Command A)'
        }
    ]
    
    successful_tests = 0
    total_tests = len(test_cases)
    
    for test_case in test_cases:
        success = await test_query(
            pipeline, 
            test_case['query'],
            test_case['lang_name'],
            test_case['test_name']
        )
        if success:
            successful_tests += 1
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    
    if force_command_a:
        print("\n💡 VERIFICATION TIPS:")
        print("- Check logs above for '⚠️ Overriding model selection' messages")
        print("- English and Spanish should show override messages")
        print("- French may or may not show override (already uses Command A)")
    else:
        print("\n💡 TO TEST OVERRIDE:")
        print("Set environment variable: export FORCE_COMMAND_A_RESPONSES=true")
        print("Then run this test again")
    
    print(f"\n🎉 Testing completed! Override: {'ENABLED' if force_command_a else 'DISABLED'}")

if __name__ == "__main__":
    asyncio.run(main())
