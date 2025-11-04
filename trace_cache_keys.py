#!/usr/bin/env python3
"""
Trace cache key generation throughout the pipeline
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

def make_cache_key(language_code: str, base_query: str) -> str:
    """Create cache key."""
    key_material = f"{language_code}:{base_query}".encode("utf-8")
    digest = hashlib.sha256(key_material).hexdigest()
    return f"q:{language_code}:{digest}"

print("=" * 80)
print("CACHE KEY TRACE FOR YOUR QUESTION")
print("=" * 80)

# Your exact question
original_query = "What are the local impacts of climate change in Toronto?"
language_code = "en"

print(f"\nOriginal query: '{original_query}'")
print(f"Language code: '{language_code}'")

# Step 1: Router - might translate or keep as-is
english_query = original_query  # For English, router returns same query
print(f"\nAfter router:")
print(f"  english_query: '{english_query}'")

# Step 2: Cache check - normalize and create key
normalized = normalize_query(english_query)
cache_key = make_cache_key(language_code, normalized)
print(f"\nCache CHECK (line 516):")
print(f"  normalized: '{normalized}'")
print(f"  cache_key: {cache_key}")

# Step 3: Query rewriter - might modify query
# Simulating different scenarios
scenarios = [
    ("No rewrite", english_query),
    ("Adds context", english_query + " in the context of urban planning"),
    ("Rephrases", "What climate change impacts affect Toronto locally?"),
    ("Strips punctuation", english_query.rstrip("?")),
]

print(f"\nQuery rewriter scenarios:")
for i, (desc, processed) in enumerate(scenarios, 1):
    norm_processed = normalize_query(processed)
    key_processed = make_cache_key(language_code, norm_processed)
    matches = key_processed == cache_key
    print(f"\n  {i}. {desc}:")
    print(f"     processed_query: '{processed}'")
    print(f"     normalized: '{norm_processed}'")
    print(f"     key matches CHECK key? {'✅ YES' if matches else '❌ NO - CACHE MISS!'}")
    if not matches:
        print(f"     Different key: {key_processed}")

print("\n" + "=" * 80)
print("CRITICAL QUESTION:")
print("=" * 80)
print("""
Does the query rewriter MODIFY the query?

If processed_query != english_query, then:
- Cache CHECK uses: hash(english_query)
- Cache STORE uses: hash(processed_query)
- Keys don't match → Cache miss every time!

Check your logs for:
  "Rewriter IN → original_query='What are the local impacts...'"

And see if the processed query is different.
""")

print("\n" + "=" * 80)
print("THE BUG IS PROBABLY HERE:")
print("=" * 80)
print("""
Line 511: normalized = self._normalize_query(english_query)
Line 516: cache_key = self._make_cache_key(language_code, normalized)

But later, if query_rewriter changes the query to processed_query,
and we use processed_query for something, the cache key might be wrong!

Need to check:
1. Is processed_query used for retrieval? ← This would break it
2. Is cache stored with same normalized value from line 511? ← Must be!
""")
