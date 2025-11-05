#!/usr/bin/env python3
"""
Direct Redis Cache Check
Checks if your specific question is cached in Redis
"""

import os
import sys
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from models.redis_cache import ClimateCache
except ImportError as e:
    print(f"❌ Cannot import ClimateCache: {e}")
    print("Make sure you're in the project root directory")
    sys.exit(1)

print("=" * 80)
print("DIRECT REDIS CACHE CHECK")
print("=" * 80)

# The specific cache key for your question
question = "What are the local impacts of climate change in Toronto?"
cache_key = "q:en:41d95a83486a6ab486548d9f3c506a59568a6ebd7cb7d7a617e1177fdad915d7"

print(f"\nQuestion: '{question}'")
print(f"Cache key: {cache_key}")

try:
    # Initialize cache
    print("\n1. CONNECTING TO REDIS")
    print("-" * 80)
    cache = ClimateCache()

    if not cache.redis_client:
        print("❌ Redis client failed to initialize!")
        print("Check your Redis connection settings:")
        print(f"  REDIS_HOST: {os.getenv('REDIS_HOST', 'localhost')}")
        print(f"  REDIS_PORT: {os.getenv('REDIS_PORT', '6379')}")
        print(f"  REDIS_SSL: {os.getenv('REDIS_SSL', 'false')}")
        sys.exit(1)

    # Test connection
    try:
        cache.redis_client.ping()
        print(f"✅ Connected to Redis: {cache.host}:{cache.port}")
        print(f"   SSL: {cache.ssl}")
    except Exception as e:
        print(f"❌ Cannot ping Redis: {e}")
        sys.exit(1)

    # Check if specific key exists
    print("\n2. CHECKING SPECIFIC QUESTION")
    print("-" * 80)
    exists = cache.redis_client.exists(cache_key)

    if exists:
        print(f"✅ KEY EXISTS IN REDIS!")

        # Get TTL
        ttl = cache.redis_client.ttl(cache_key)
        if ttl > 0:
            print(f"✅ TTL: {ttl} seconds ({ttl/60:.1f} minutes remaining)")
        elif ttl == -1:
            print(f"⚠️  TTL: No expiration set (cached forever)")
        elif ttl == -2:
            print(f"❌ TTL: Key expired!")

        # Get value
        try:
            value = cache.redis_client.get(cache_key)
            if value:
                data = json.loads(value)
                print(f"\n✅ CACHED DATA FOUND:")
                print(f"   - Response length: {len(data.get('response', ''))} chars")
                print(f"   - Model type: {data.get('model_type', 'unknown')}")
                print(f"   - Model used: {data.get('model_used', 'unknown')}")
                print(f"   - Language: {data.get('language_code', 'unknown')}")
                print(f"   - Citations: {len(data.get('citations', []))}")

                # Show preview
                response_preview = data.get('response', '')[:200]
                print(f"\n   Response preview:")
                print(f"   {response_preview}...")

                print("\n🎉 THE QUESTION IS CACHED!")
                print("   If you're still getting cache misses, the problem is:")
                print("   → Pipeline code not reading from Redis correctly")
                print("   → Using different Redis instance (dev vs prod)")
                print("   → Cache check using different key format")
            else:
                print("❌ Key exists but no value (corrupted?)")
        except json.JSONDecodeError as e:
            print(f"❌ Key exists but value is not valid JSON: {e}")
        except Exception as e:
            print(f"❌ Error reading value: {e}")

    else:
        print(f"❌ KEY DOES NOT EXIST IN REDIS")
        print(f"   This means the response was NEVER cached!")
        print(f"\n   Possible reasons:")
        print(f"   1. Question never asked with new code")
        print(f"   2. cache.set() failed with error")
        print(f"   3. Early return bypassed cache.set()")
        print(f"   4. Redis cache was flushed")

    # Check for similar keys
    print("\n3. CHECKING FOR SIMILAR KEYS")
    print("-" * 80)

    # Look for any English query keys
    all_en_keys = cache.redis_client.keys('q:en:*')
    print(f"Total English query keys: {len(all_en_keys)}")

    if len(all_en_keys) > 0:
        print(f"\nShowing first 10 keys:")
        for i, key in enumerate(all_en_keys[:10], 1):
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            ttl = cache.redis_client.ttl(key_str)
            print(f"  {i}. {key_str} (TTL: {ttl}s)")
    else:
        print("❌ NO ENGLISH QUERY KEYS FOUND!")
        print("   This means NO questions have been cached!")

    # Check all keys
    print("\n4. REDIS OVERVIEW")
    print("-" * 80)
    all_keys = cache.redis_client.keys('*')
    print(f"Total keys in Redis: {len(all_keys)}")

    # Group by prefix
    prefixes = {}
    for key in all_keys:
        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
        prefix = key_str.split(':')[0] if ':' in key_str else 'no-prefix'
        prefixes[prefix] = prefixes.get(prefix, 0) + 1

    print("\nKeys by prefix:")
    for prefix, count in sorted(prefixes.items()):
        print(f"  {prefix:20s}: {count:4d} keys")

except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if exists:
    print("""
✅ CACHE KEY EXISTS IN REDIS!

The response IS cached, but you're still getting cache misses.

This means:
→ The pipeline is NOT looking in the right place
→ Code is not deployed (still using old cache key format)
→ Application not restarted after code deploy
→ Testing dev environment but looking at prod Redis

NEXT STEPS:
1. Verify you deployed the new code: git log -1
2. Verify you restarted the app after deploy
3. Add debug logging to see what key the pipeline checks:
   python3 add_debug_logging.py
4. Ask question and compare 🔍 CACHE CHECK key with this key
""")
else:
    print("""
❌ CACHE KEY DOES NOT EXIST!

The response was NEVER stored in Redis.

This means:
→ cache.set() is not being called
→ cache.set() is failing with error
→ Early return (canned response) bypassing cache
→ Question classified as off-topic

NEXT STEPS:
1. Check logs for "Response cached" or "Failed to cache"
2. Run: python3 analyze_cache_logs.py /path/to/app.log
3. Look for "canned intent detected" or "off-topic"
4. Add debug logging to see what's happening:
   python3 add_debug_logging.py
""")

print("=" * 80)
