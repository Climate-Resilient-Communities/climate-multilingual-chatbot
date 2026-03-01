#!/usr/bin/env python3
"""
Test script to verify Tiny-Aya model routing across languages.
Tests various languages that route to different Tiny-Aya regional models.

NOTE: This is a manual integration test that requires live API access.
It is NOT designed to run in automated CI/CD pipelines.
"""

import os
import sys
import asyncio
import logging
import time
from typing import Dict, List

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models.climate_pipeline import ClimateQueryPipeline

# Configure logging to capture routing messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TinyAyaRoutingTest:
    """Test class for Tiny-Aya regional model routing."""

    def __init__(self):
        self.pipeline = None
        self.test_results = []

    async def setup(self):
        """Initialize the pipeline."""
        logger.info("Setting up Climate Pipeline...")
        self.pipeline = ClimateQueryPipeline()
        await self.pipeline.prewarm()
        logger.info("Pipeline ready")

    async def run_test_query(self, query: str, language_name: str,
                           expected_model: str) -> Dict:
        """Run a single test query and capture results."""
        logger.info(f"\nTesting: {language_name}")
        logger.info(f"Query: {query}")
        logger.info(f"Expected routing: {expected_model}")

        start_time = time.time()

        try:
            result = await self.pipeline.process_query(
                query=query,
                language_name=language_name
            )

            processing_time = time.time() - start_time

            test_result = {
                'language': language_name,
                'query': query,
                'expected_model': expected_model,
                'success': result.get('success', False),
                'response': result.get('response', '')[:100] + '...' if result.get('response') else '',
                'processing_time': processing_time,
                'model_used': result.get('model_used', 'unknown'),
            }

            if result.get('success'):
                logger.info(f"Query processed successfully in {processing_time:.2f}s")
            else:
                logger.info(f"Query failed: {result.get('message', 'Unknown error')}")

            return test_result

        except Exception as e:
            logger.error(f"Test failed with exception: {str(e)}")
            return {
                'language': language_name,
                'query': query,
                'expected_model': expected_model,
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
            }

    async def run_all_tests(self):
        """Run comprehensive routing tests."""

        # Test cases: (query, language_name, expected_model_tier)
        test_cases = [
            # Tiny-Aya Global (English and fallback)
            ("What causes climate change?", "English", "Tiny-Aya Global"),
            ("Was verursacht den Klimawandel?", "German", "Tiny-Aya Water"),
            ("O que causa as mudanças climáticas?", "Portuguese", "Tiny-Aya Water"),

            # Tiny-Aya Fire (South Asian)
            ("जलवायु परिवर्तन क्या कारण है?", "Hindi", "Tiny-Aya Fire"),

            # Tiny-Aya Earth (African)
            ("Nini kinachosababisha mabadiliko ya hali ya hewa?", "Swahili", "Tiny-Aya Earth"),

            # Tiny-Aya Water (Asia-Pacific + Europe)
            ("Qu'est-ce qui cause le changement climatique?", "French", "Tiny-Aya Water"),
            ("气候变化的原因是什么？", "Chinese", "Tiny-Aya Water"),
            ("¿Qué causa el cambio climático?", "Spanish", "Tiny-Aya Water"),
        ]

        logger.info("=" * 80)
        logger.info("STARTING TINY-AYA ROUTING TESTS")
        logger.info("=" * 80)

        for query, lang_name, expected_model in test_cases:
            result = await self.run_test_query(query, lang_name, expected_model)
            self.test_results.append(result)
            await asyncio.sleep(1)

        await self.print_summary()

    async def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)

        successful_tests = [r for r in self.test_results if r.get('success')]
        failed_tests = [r for r in self.test_results if not r.get('success')]

        logger.info(f"Total tests: {len(self.test_results)}")
        logger.info(f"Successful: {len(successful_tests)}")
        logger.info(f"Failed: {len(failed_tests)}")

        if failed_tests:
            logger.info("\nFAILED TESTS:")
            for test in failed_tests:
                logger.info(f"  - {test['language']}: {test.get('error', 'Unknown error')}")

        logger.info("\nSUCCESSFUL TESTS:")
        for test in successful_tests:
            logger.info(f"  - {test['language']}: {test['processing_time']:.2f}s (model: {test.get('model_used', 'unknown')})")

async def main():
    """Main test function."""
    logger.info("TINY-AYA ROUTING TEST SUITE")

    tester = TinyAyaRoutingTest()
    await tester.setup()
    await tester.run_all_tests()

    logger.info("\nTesting completed!")

if __name__ == "__main__":
    asyncio.run(main())
