#!/usr/bin/env python3
"""
Redis Cache Debugging Script
Inspects Redis state and cache key generation for debugging
"""

import os
import sys
import json
import hashlib
import re
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.redis_cache import ClimateCache

def normalize_query(text: str) -> str:
    """Normalize text for cache key generation (matches pipeline logic)."""
    if not text:
        return ""
    # Lowercase, remove extra spaces and punctuation spacing
    t = text.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def make_cache_key(language_code: str, model_type: str, base_query: str) -> str:
    """Create a stable cache key using normalized query and metadata.

    This matches the logic in climate_pipeline.py:1158-1165
    """
    key_material = f"{language_code}:{model_type}:{base_query}".encode("utf-8")
    digest = hashlib.sha256(key_material).hexdigest()
    return f"q:{language_code}:{digest}"

def inspect_redis():
    """Inspect Redis cache state."""
    print("=" * 80)
    print("REDIS CACHE INSPECTION")
    print("=" * 80)

    try:
        cache = ClimateCache()

        # 1. Test connection
        print("\n1. REDIS CONNECTION")
        print("-" * 80)
        if cache.redis_client:
            try:
                cache.redis_client.ping()
                print(f"✅ Connected to Redis: {cache.host}:{cache.port}")
                print(f"   SSL: {cache.ssl}")
                print(f"   Default TTL: {cache.expiration}s ({cache.expiration/3600:.1f} hours)")
            except Exception as e:
                print(f"❌ Cannot ping Redis: {e}")
                return
        else:
            print("❌ Redis client not initialized")
            return

        # 2. Count total keys
        print("\n2. REDIS KEYS")
        print("-" * 80)
        try:
            all_keys = cache.redis_client.keys('*')
            print(f"Total keys in Redis: {len(all_keys)}")

            # Group by prefix
            prefixes = {}
            for key in all_keys:
                prefix = key.split(':')[0] if ':' in key else 'no-prefix'
                prefixes[prefix] = prefixes.get(prefix, 0) + 1

            print("\nKeys by prefix:")
            for prefix, count in sorted(prefixes.items()):
                print(f"  {prefix:20s}: {count:4d} keys")

            # Show sample query keys
            query_keys = [k for k in all_keys if k.startswith('q:')]
            print(f"\nSample query cache keys (showing first 10):")
            for key in query_keys[:10]:
                try:
                    ttl = cache.redis_client.ttl(key)
                    value = cache.redis_client.get(key)
                    if value:
                        data = json.loads(value)
                        response_preview = data.get('response', '')[:100] if isinstance(data, dict) else str(data)[:100]
                        print(f"  {key}")
                        print(f"    TTL: {ttl}s ({ttl/60:.1f}m remaining)")
                        print(f"    Preview: {response_preview}...")
                except Exception as e:
                    print(f"  {key} (error reading: {e})")

        except Exception as e:
            print(f"❌ Error reading keys: {e}")

        # 3. Test specific query
        print("\n3. TEST QUERY CACHE KEY GENERATION")
        print("-" * 80)
        test_query = "Why is summer so hot now in Toronto?"
        print(f"Test query: '{test_query}'")

        normalized = normalize_query(test_query)
        print(f"Normalized: '{normalized}'")

        # Test different model types and languages
        test_cases = [
            ('en', 'nova'),
            ('en', 'cohere'),
            ('en', 'anthropic'),
        ]

        for lang, model in test_cases:
            cache_key = make_cache_key(lang, model, normalized)
            print(f"\n  Language: {lang}, Model: {model}")
            print(f"  Cache key: {cache_key}")

            try:
                cached_value = cache.redis_client.get(cache_key)
                if cached_value:
                    ttl = cache.redis_client.ttl(cache_key)
                    data = json.loads(cached_value)
                    print(f"  ✅ CACHE HIT! TTL: {ttl}s ({ttl/60:.1f}m remaining)")
                    if isinstance(data, dict):
                        response = data.get('response', '')
                        print(f"  Response preview: {response[:200]}...")
                else:
                    print(f"  ❌ CACHE MISS - Key not found in Redis")
            except Exception as e:
                print(f"  ❌ Error checking cache: {e}")

        # 4. Check recent queries list
        print("\n4. RECENT QUERIES LIST")
        print("-" * 80)
        try:
            recent = cache.redis_client.lrange('recent_queries', 0, -1)
            if recent:
                print(f"Recent queries: {len(recent)}")
                for i, q in enumerate(recent[:10], 1):
                    print(f"  {i}. {q}")
            else:
                print("No recent queries tracked")
        except Exception as e:
            print(f"Error reading recent queries: {e}")

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_redis()
