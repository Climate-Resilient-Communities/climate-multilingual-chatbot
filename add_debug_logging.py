#!/usr/bin/env python3
"""
Add Debug Logging to Climate Pipeline
This script adds temporary debug statements to track cache operations
"""

import sys

# Read the pipeline file
with open('src/models/climate_pipeline.py', 'r') as f:
    content = f.read()

# Check if already has debug logging
if '🔍 CACHE CHECK:' in content:
    print("❌ Debug logging already present!")
    print("Remove it first with: python3 remove_debug_logging.py")
    sys.exit(1)

# Add debug logging at cache check
debug_check = '''            cache_key = self._make_cache_key(language_code, normalized)
            logger.error(f"🔍 CACHE CHECK: key={cache_key}")
            logger.error(f"🔍 CACHE CHECK: normalized='{normalized}'")
            logger.error(f"🔍 CACHE CHECK: language_code='{language_code}'")'''

content = content.replace(
    '            cache_key = self._make_cache_key(language_code, normalized)',
    debug_check
)

# Add debug logging at cache store
debug_store = '''                    await self.cache.set(cache_key, result)
                    logger.error(f"🔍 CACHE STORE: key={cache_key}")
                    logger.error(f"🔍 CACHE STORE: normalized='{normalized}'")
                    logger.error(f"🔍 CACHE STORE: model_type='{model_type}'")
                    logger.error(f"🔍 CACHE STORE: SUCCESS!")'''

content = content.replace(
    '                    await self.cache.set(cache_key, result)',
    debug_store
)

# Add debug at cache initialization
debug_init = '''            self.cache = self._initialize_cache()
            if self.cache:
                logger.error("🔍 CACHE INIT: Redis cache initialized successfully")
            else:
                logger.error("🔍 CACHE INIT: FAILED - cache is None!")'''

content = content.replace(
    '            self.cache = self._initialize_cache()',
    debug_init
)

# Write back
with open('src/models/climate_pipeline.py', 'w') as f:
    f.write(content)

print("✅ Debug logging added to climate_pipeline.py")
print("")
print("Now:")
print("1. Restart your application")
print("2. Ask: 'What are the local impacts of climate change in Toronto?'")
print("3. Check logs for lines starting with 🔍")
print("")
print("You should see:")
print("  🔍 CACHE INIT: Redis cache initialized successfully")
print("  🔍 CACHE CHECK: key=q:en:41d95a83...")
print("  🔍 CACHE STORE: key=q:en:41d95a83...")
print("  🔍 CACHE STORE: SUCCESS!")
print("")
print("Then ask the same question again and look for:")
print("  🔍 CACHE CHECK: key=q:en:41d95a83...")
print("  ✓ Cache hit for english - returning cached response")
print("")
print("To remove debug logging later:")
print("  git checkout src/models/climate_pipeline.py")
