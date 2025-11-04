#!/usr/bin/env python3
"""
Diagnose Cache Key Issue - Historical Analysis

⚠️  NOTE: This script demonstrates the OLD BROKEN behavior before the fix.
It shows WHY cache wasn't working when model_type was in the cache key.

The fix has been applied in climate_pipeline.py - model_type is now only
in the cache VALUE, not the KEY. See test_cache_fix.py for verification
of the new behavior.
"""

import hashlib
import re

def normalize_query(text: str) -> str:
    """Normalize text for cache key generation."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def make_cache_key(language_code: str, model_type: str, base_query: str) -> str:
    """Create cache key (OLD BROKEN implementation - for demonstration only)."""
    key_material = f"{language_code}:{model_type}:{base_query}".encode("utf-8")
    digest = hashlib.sha256(key_material).hexdigest()
    return f"q:{language_code}:{digest}"

# The question from the predefined list
query = "Why is summer so hot now in Toronto?"
normalized = normalize_query(query)

print("=" * 80)
print("CACHE KEY ISSUE DIAGNOSIS")
print("=" * 80)
print(f"\nOriginal query: '{query}'")
print(f"Normalized query: '{normalized}'")
print("\n" + "-" * 80)
print("PROBLEM: model_type changes between requests!")
print("-" * 80)

# Scenario 1: First request (routed to Nova)
key_nova = make_cache_key("en", "nova", normalized)
print("\n1️⃣  FIRST REQUEST (model_type='nova'):")
print(f"   Cache key: {key_nova}")
print(f"   Key material: en:nova:{normalized}")
print(f"   ✅ Response generated and cached with this key")

# Scenario 2: Second request with FORCE_COMMAND_A_RESPONSES=true
key_cohere = make_cache_key("en", "cohere", normalized)
print("\n2️⃣  SECOND REQUEST (FORCE_COMMAND_A_RESPONSES=true, model_type='cohere'):")
print(f"   Cache key: {key_cohere}")
print(f"   Key material: en:cohere:{normalized}")
print(f"   ❌ CACHE MISS! Looking for different key!")

# Scenario 3: Third request with different routing
key_anthropic = make_cache_key("en", "anthropic", normalized)
print("\n3️⃣  THIRD REQUEST (if model_type='anthropic'):")
print(f"   Cache key: {key_anthropic}")
print(f"   Key material: en:anthropic:{normalized}")
print(f"   ❌ CACHE MISS! Yet another different key!")

print("\n" + "=" * 80)
print("PROOF OF ISSUE:")
print("=" * 80)
print(f"Nova key == Cohere key? {key_nova == key_cohere}")
print(f"Nova key == Anthropic key? {key_nova == key_anthropic}")
print(f"Cohere key == Anthropic key? {key_cohere == key_anthropic}")

print("\n" + "=" * 80)
print("ROOT CAUSE:")
print("=" * 80)
print("""
The cache key includes model_type in the hash:
    key_material = f"{language_code}:{model_type}:{base_query}"

When model_type changes (due to routing changes, env vars, A/B testing):
    - Same question gets different cache key
    - Cache miss even though response was already generated
    - Wastes time and money regenerating the same answer

For predefined questions like "Why is summer so hot now in Toronto?",
users expect instant responses from cache regardless of which model
initially generated the answer.
""")

print("\n" + "=" * 80)
print("SOLUTION:")
print("=" * 80)
print("""
Remove model_type from cache key generation:

    BEFORE:
    key_material = f"{language_code}:{model_type}:{base_query}"

    AFTER:
    key_material = f"{language_code}:{base_query}"

This way, the cache works globally across all model types.
The answer is the answer - doesn't matter if Nova or Cohere generated it.
""")
