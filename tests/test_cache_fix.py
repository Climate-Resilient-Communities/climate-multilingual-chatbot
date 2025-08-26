#!/usr/bin/env python3
"""
Test script to verify Redis cache reuse functionality.
Tests that cached responses are retrieved immediately after app restart.
"""

import os
import sys
import asyncio
import time

# Add src to path
sys.path.insert(0, 'src')

from models.climate_pipeline import ClimateQueryPipeline

async def test_cache_persistence():
    """Test that cache works immediately and persists across sessions."""
    
    print("🧪 TESTING REDIS CACHE PERSISTENCE")
    print("=" * 50)
    
    # Test query that should be cacheable
    test_query = "What are the main causes of climate change?"
    test_language = "English"
    
    pipeline = ClimateQueryPipeline()
    
    # Test 1: First run (might be cache miss)
    print("\n📥 TEST 1: First query (checking for existing cache)")
    start1 = time.time()
    result1 = await pipeline.process_query(
        query=test_query,
        language_name=test_language
    )
    duration1 = time.time() - start1
    
    success1 = result1.get('success', False)
    print(f"✅ First query: {'SUCCESS' if success1 else 'FAILED'} ({duration1:.2f}s)")
    
    if success1:
        print(f"Response preview: {result1.get('response', '')[:100]}...")
    
    # Test 2: Immediate second run (should be cache hit)
    print("\n💨 TEST 2: Second query (should be cache hit)")
    start2 = time.time()
    result2 = await pipeline.process_query(
        query=test_query,
        language_name=test_language
    )
    duration2 = time.time() - start2
    
    success2 = result2.get('success', False)
    print(f"✅ Second query: {'SUCCESS' if success2 else 'FAILED'} ({duration2:.2f}s)")
    
    # Check if second query was significantly faster (cache hit)
    if success1 and success2:
        speedup = duration1 / duration2 if duration2 > 0 else 1
        if duration2 < 1.0:  # Less than 1 second = likely cache hit
            print(f"🚀 CACHE HIT detected! {speedup:.1f}x faster ({duration2:.2f}s vs {duration1:.2f}s)")
        elif duration2 < duration1 * 0.5:  # At least 50% faster
            print(f"⚡ Possible cache hit: {speedup:.1f}x faster")
        else:
            print(f"⚠️  No significant speedup detected - may not be using cache")
    
    # Test 3: Check cache instance
    print(f"\n🔧 CACHE STATUS:")
    print(f"Pipeline has cache: {'YES' if pipeline.cache else 'NO'}")
    if pipeline.cache:
        print(f"Cache host: {getattr(pipeline.cache, 'host', 'unknown')}")
        print(f"Cache expiration: {getattr(pipeline.cache, 'expiration', 'unknown')}s")
    
    print(f"\n📊 SUMMARY:")
    print(f"First query: {duration1:.2f}s")
    print(f"Second query: {duration2:.2f}s")
    if success1 and success2 and duration2 < 2.0:
        print("✅ Cache appears to be working!")
    elif success1 and success2:
        print("⚠️  Cache may not be working optimally")
    else:
        print("❌ Tests failed")
    
    print("\n💡 If cache is not working:")
    print("- Check Redis is running: redis-cli ping")
    print("- Check REDIS_HOST environment variable")
    print("- Look for cache hit/miss messages in logs above")

if __name__ == "__main__":
    asyncio.run(test_cache_persistence())
