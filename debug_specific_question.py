#!/usr/bin/env python3
"""
Deep dive diagnostic for specific cache miss issue
Tests: "What are the local impacts of climate change in Toronto?"
"""

import hashlib
import re

def normalize_query(text: str) -> str:
    """Normalize text for cache key generation (matches pipeline)."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def make_cache_key(language_code: str, base_query: str) -> str:
    """Create cache key (NEW implementation)."""
    key_material = f"{language_code}:{base_query}".encode("utf-8")
    digest = hashlib.sha256(key_material).hexdigest()
    return f"q:{language_code}:{digest}"

# The EXACT predefined question from the frontend
question = "What are the local impacts of climate change in Toronto?"

print("=" * 80)
print("DEEP DIVE: Why is this question not hitting cache?")
print("=" * 80)
print(f"\nQuestion: '{question}'")

# Step 1: Normalization
normalized = normalize_query(question)
print(f"\n1. NORMALIZATION:")
print(f"   Original: '{question}'")
print(f"   Normalized: '{normalized}'")
print(f"   Changes: lowercase, multiple spaces collapsed")

# Step 2: Cache key generation
cache_key = make_cache_key('en', normalized)
print(f"\n2. CACHE KEY GENERATION:")
print(f"   Language: en")
print(f"   Key material: 'en:{normalized}'")
print(f"   SHA256 hash: {hashlib.sha256(f'en:{normalized}'.encode('utf-8')).hexdigest()}")
print(f"   Final cache key: {cache_key}")

# Step 3: Check for common issues
print(f"\n3. COMMON CACHE MISS CAUSES:")
print(f"   ❓ Is deployment using new code? (check git commit)")
print(f"   ❓ Was Redis cache cleared/flushed?")
print(f"   ❓ Is skip_cache=true being passed?")
print(f"   ❓ Is cache initialization failing silently?")
print(f"   ❓ Are there multiple Redis instances (dev vs prod)?")
print(f"   ❓ Is cache TTL expired (older than 1 hour)?")

# Step 4: Test different normalization scenarios
print(f"\n4. NORMALIZATION EDGE CASES:")
test_variations = [
    "What are the local impacts of climate change in Toronto?",  # Original
    "What are the local impacts of climate change in Toronto? ",  # Trailing space
    "What are  the local impacts of climate change in Toronto?",  # Double space
    "what are the local impacts of climate change in toronto?",  # Lowercase
    "What are the local impacts of climate change in Toronto",  # No question mark
]

keys = {}
for var in test_variations:
    norm = normalize_query(var)
    key = make_cache_key('en', norm)
    keys[key] = keys.get(key, []) + [var]

print(f"   Tested {len(test_variations)} variations")
print(f"   Generated {len(keys)} unique cache keys")

if len(keys) == 1:
    print(f"   ✅ All variations produce same key (normalization works)")
else:
    print(f"   ❌ PROBLEM: Different variations produce different keys!")
    for i, (key, variations) in enumerate(keys.items(), 1):
        print(f"\n   Key {i}: {key}")
        for v in variations:
            print(f"      - '{v}'")

# Step 5: Generate test script for production
print(f"\n5. PRODUCTION TEST COMMAND:")
print(f"   Run this on production to check if key exists:")
print(f"")
print(f"   redis-cli GET '{cache_key}'")
print(f"")
print(f"   If returns (nil): Cache miss - key doesn't exist")
print(f"   If returns data: Cache hit - key exists but not being used")

print(f"\n6. DEBUG CHECKLIST:")
print(f"   [ ] Check git commit on production: git log --oneline -1")
print(f"   [ ] Check Redis connection: redis-cli PING")
print(f"   [ ] Check cache key exists: redis-cli GET '{cache_key}'")
print(f"   [ ] Check app logs for 'Cache hit' or 'Cache miss' messages")
print(f"   [ ] Check if FORCE_COMMAND_A_RESPONSES changed mid-request")
print(f"   [ ] Check if self.cache is None in pipeline")
print(f"   [ ] Check if skip_cache is being passed as True")

print(f"\n7. NEXT STEPS:")
print(f"   A. If Redis key EXISTS but still cache miss:")
print(f"      → Pipeline code not deployed OR cache initialization failing")
print(f"   B. If Redis key DOESN'T EXIST:")
print(f"      → Question never answered before OR cache was flushed")
print(f"   C. If different key format in Redis:")
print(f"      → Old cache keys still present, new requests using new format")

print("\n" + "=" * 80)
