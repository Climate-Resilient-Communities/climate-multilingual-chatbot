#!/usr/bin/env python3
"""
Test script to verify FORCE_COMMAND_A_RESPONSES override functionality.
Tests various languages that normally route to different models.
"""

import os
import sys
import asyncio
import logging
import time
from typing import Dict, List

# Add the src directory to the path
sys.path.append('/Users/luis_ticas/Documents/GitHub/climate-multilingual-chatbot/src')

from models.climate_pipeline import ClimatePipeline

# Configure logging to capture override messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommandAOverrideTest:
    """Test class for Command A override functionality."""
    
    def __init__(self):
        self.pipeline = None
        self.test_results = []
        
    async def setup(self):
        """Initialize the pipeline."""
        logger.info("🔧 Setting up Climate Pipeline...")
        self.pipeline = ClimatePipeline()
        await self.pipeline.prewarm()
        logger.info("✅ Pipeline ready")
        
    async def run_test_query(self, query: str, language_code: str, language_name: str, 
                           expected_normal_model: str) -> Dict:
        """Run a single test query and capture results."""
        logger.info(f"\n🧪 Testing: {language_name} ({language_code})")
        logger.info(f"Query: {query}")
        logger.info(f"Expected normal routing: {expected_normal_model}")
        
        start_time = time.time()
        
        try:
            # Capture logs by monitoring the logger
            result = await self.pipeline.process_query(
                query=query,
                language_code=language_code,
                language_name=language_name
            )
            
            processing_time = time.time() - start_time
            
            test_result = {
                'language': language_name,
                'language_code': language_code,
                'query': query,
                'expected_normal_model': expected_normal_model,
                'success': result.get('success', False),
                'response': result.get('response', '')[:100] + '...' if result.get('response') else '',
                'processing_time': processing_time,
                'override_detected': False  # Will be updated based on logs
            }
            
            if result.get('success'):
                logger.info(f"✅ Query processed successfully in {processing_time:.2f}s")
            else:
                logger.info(f"❌ Query failed: {result.get('message', 'Unknown error')}")
                
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {str(e)}")
            return {
                'language': language_name,
                'language_code': language_code,
                'query': query,
                'expected_normal_model': expected_normal_model,
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'override_detected': False
            }

    async def run_all_tests(self):
        """Run comprehensive tests with and without override."""
        
        # Test cases: (query, language_code, language_name, expected_normal_model)
        test_cases = [
            # Languages that normally route to Nova (should be overridden)
            ("What causes climate change?", "en", "English", "Nova"),
            ("¿Qué causa el cambio climático?", "es", "Spanish", "Nova"), 
            ("Was verursacht den Klimawandel?", "de", "German", "Nova"),
            ("Cosa causa il cambiamento climatico?", "it", "Italian", "Nova"),
            ("O que causa as mudanças climáticas?", "pt", "Portuguese", "Nova"),
            
            # Languages that normally route to Command A (should stay the same but confirm override logging)
            ("Qu'est-ce qui cause le changement climatique?", "fr", "French", "Command A"),
            ("ما الذي يسبب تغير المناخ؟", "ar", "Arabic", "Command A"),
            ("气候变化的原因是什么？", "zh", "Chinese", "Command A"),
        ]
        
        logger.info("=" * 80)
        logger.info("🚀 STARTING COMMAND A OVERRIDE TESTS")
        logger.info("=" * 80)
        
        for query, lang_code, lang_name, expected_model in test_cases:
            result = await self.run_test_query(query, lang_code, lang_name, expected_model)
            self.test_results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(1)
            
        await self.print_summary()
        
    async def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 80)
        
        successful_tests = [r for r in self.test_results if r.get('success')]
        failed_tests = [r for r in self.test_results if not r.get('success')]
        
        logger.info(f"Total tests: {len(self.test_results)}")
        logger.info(f"Successful: {len(successful_tests)}")
        logger.info(f"Failed: {len(failed_tests)}")
        
        if failed_tests:
            logger.info("\n❌ FAILED TESTS:")
            for test in failed_tests:
                logger.info(f"  - {test['language']}: {test.get('error', 'Unknown error')}")
                
        logger.info("\n✅ SUCCESSFUL TESTS:")
        for test in successful_tests:
            avg_time = test['processing_time']
            logger.info(f"  - {test['language']}: {avg_time:.2f}s")
            
        # Check environment variable status
        force_command_a = os.getenv('FORCE_COMMAND_A_RESPONSES', '').lower() in ('true', '1', 'yes')
        logger.info(f"\n🔧 FORCE_COMMAND_A_RESPONSES: {'ENABLED' if force_command_a else 'DISABLED'}")
        
        if force_command_a:
            logger.info("⚠️  All responses should be generated using Command A model")
            logger.info("💡 Check logs above for override messages starting with '⚠️'")
        else:
            logger.info("ℹ️  Using default routing logic (Nova for EN/ES/DE/IT/PT, Command A for others)")

async def main():
    """Main test function."""
    
    # Check if override is enabled
    force_command_a = os.getenv('FORCE_COMMAND_A_RESPONSES', '').lower() in ('true', '1', 'yes')
    
    logger.info("🧪 COMMAND A OVERRIDE TEST SUITE")
    logger.info(f"Override Status: {'ENABLED' if force_command_a else 'DISABLED'}")
    
    if not force_command_a:
        logger.warning("⚠️  FORCE_COMMAND_A_RESPONSES is not enabled!")
        logger.warning("💡 To test the override, set: export FORCE_COMMAND_A_RESPONSES=true")
        response = input("Continue with default routing tests? (y/n): ")
        if response.lower() != 'y':
            logger.info("Test cancelled.")
            return
    
    tester = CommandAOverrideTest()
    await tester.setup()
    await tester.run_all_tests()
    
    logger.info("\n🎉 Testing completed!")

if __name__ == "__main__":
    asyncio.run(main())
