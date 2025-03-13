import os
import sys
import asyncio
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Import Redis cache
from src.models.redis_cache import ClimateCache
from src.utils.env_loader import load_environment

async def test_redis_cache():
    """Test Redis cache functionality with the exact same keys used in the application."""
    print("\n=== Testing Redis Cache for Climate Chatbot ===")
    
    # Load environment variables
    load_environment()
    
    # Initialize cache with Redis settings from environment variables
    host = os.getenv('REDIS_HOST', 'localhost')
    port = int(os.getenv('REDIS_PORT', 6379))
    password = os.getenv('REDIS_PASSWORD', None)
    
    print(f"Connecting to Redis at {host}:{port} with password: {'Yes' if password else 'No'}")
    
    try:
        # Create cache instance
        cache = ClimateCache(
            host=host,
            port=port,
            password=password,
            expiration=3600  # 1 hour cache expiration
        )
        
        print("✅ Redis connection established")
        
        # Test data that mimics the application data structure
        test_key = "en:what is climate change"
        test_data = {
            "response": "Climate change refers to long-term shifts in temperatures and weather patterns.",
            "citations": [
                {
                    "title": "Climate Change Overview",
                    "url": "https://example.com/climate",
                    "content": "Climate change refers to long-term shifts in temperatures and weather patterns.",
                    "snippet": "Climate change refers to long-term shifts..."
                }
            ],
            "faithfulness_score": 0.95,
            "metadata": {
                "cached_at": 1714323123.45,
                "language_code": "en",
                "processing_time": 2.5,
                "required_translation": False
            }
        }
        
        # 1. Set cache entry
        print("\n1. Testing cache set...")
        success = await cache.set(test_key, test_data)
        print(f"Cache set result: {'✅ Success' if success else '❌ Failed'}")
        
        # 2. Get cache entry
        print("\n2. Testing cache get - should be a hit...")
        result = await cache.get(test_key)
        if result:
            print(f"✅ Cache hit: {json.dumps(result, indent=2)[:200]}...")
        else:
            print("❌ Cache miss - key not found")
        
        # 3. Verify exact same key format as application
        print("\n3. Testing application-style cache key...")
        app_key = "en:what is climate change"
        app_result = await cache.get(app_key)
        print(f"App cache key result: {'✅ Hit' if app_result else '❌ Miss'}")
        
        # 4. List all keys in Redis to see what's available
        print("\n4. Checking all available keys...")
        try:
            # Use direct Redis client to get all keys
            all_keys = await asyncio.to_thread(
                lambda: cache.redis_client.keys("*") if cache.redis_client else []
            )
            print(f"Found {len(all_keys)} keys:")
            for idx, key in enumerate(all_keys[:10], 1):
                print(f"  {idx}. {key}")
            if len(all_keys) > 10:
                print(f"  ... and {len(all_keys) - 10} more")
        except Exception as e:
            print(f"❌ Error listing keys: {str(e)}")
        
        # 5. Clean up
        print("\n5. Cleaning up test data...")
        await cache.delete(test_key)
        print("✅ Test key deleted")
        
        # Close connection
        await cache.close()
        print("\n✅ Redis connection closed")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_redis_cache())