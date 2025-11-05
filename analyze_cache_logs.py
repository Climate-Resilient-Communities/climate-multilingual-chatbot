#!/usr/bin/env python3
"""
Analyze Cache Behavior from Logs
Extracts and analyzes cache-related log entries
"""

import sys
import re
from collections import defaultdict

if len(sys.argv) < 2:
    print("Usage: python3 analyze_cache_logs.py /path/to/app.log")
    print("")
    print("Or pipe logs:")
    print("  tail -1000 /path/to/app.log | python3 analyze_cache_logs.py -")
    sys.exit(1)

log_file = sys.argv[1]

if log_file == '-':
    lines = sys.stdin.readlines()
else:
    with open(log_file, 'r') as f:
        lines = f.readlines()

print("=" * 80)
print("CACHE BEHAVIOR ANALYSIS")
print("=" * 80)

# Patterns to search for
patterns = {
    'init': r'🔍 CACHE INIT:|Redis cache instance initialized',
    'check': r'🔍 CACHE CHECK:|Step 2: Cache Check',
    'hit': r'Cache hit|✓ Cache hit',
    'miss': r'Cache miss',
    'store': r'🔍 CACHE STORE:|Response cached in',
    'fail': r'Failed to cache|Cache unavailable|Cache initialization failed',
    'canned': r'Canned intent detected|classification.*off-topic',
    'key': r'cache_key=|Cache key:',
}

# Extract relevant lines
findings = defaultdict(list)
for i, line in enumerate(lines):
    for name, pattern in patterns.items():
        if re.search(pattern, line, re.IGNORECASE):
            findings[name].append((i, line.strip()))

# Print findings
print("\n1. CACHE INITIALIZATION")
print("-" * 80)
if findings['init']:
    for i, line in findings['init'][-5:]:  # Last 5
        print(f"  Line {i}: {line}")
else:
    print("  ❌ No cache initialization found in logs!")

print("\n2. CACHE CHECKS (last 10)")
print("-" * 80)
if findings['check']:
    for i, line in findings['check'][-10:]:
        print(f"  Line {i}: {line}")
else:
    print("  ❌ No cache checks found!")

print("\n3. CACHE HITS")
print("-" * 80)
if findings['hit']:
    print(f"  ✅ Found {len(findings['hit'])} cache hits")
    for i, line in findings['hit'][-5:]:
        print(f"  Line {i}: {line}")
else:
    print("  ❌ NO CACHE HITS FOUND!")

print("\n4. CACHE MISSES")
print("-" * 80)
if findings['miss']:
    print(f"  Found {len(findings['miss'])} cache misses")
    for i, line in findings['miss'][-5:]:
        print(f"  Line {i}: {line}")
else:
    print("  No cache misses (or not logged)")

print("\n5. CACHE STORES")
print("-" * 80)
if findings['store']:
    print(f"  ✅ Found {len(findings['store'])} cache stores")
    for i, line in findings['store'][-5:]:
        print(f"  Line {i}: {line}")
else:
    print("  ❌ NO CACHE STORES FOUND!")
    print("  This means responses are NOT being cached!")

print("\n6. CACHE FAILURES")
print("-" * 80)
if findings['fail']:
    print(f"  ❌ Found {len(findings['fail'])} cache failures!")
    for i, line in findings['fail']:
        print(f"  Line {i}: {line}")
else:
    print("  ✅ No cache failures found")

print("\n7. CANNED RESPONSES / EARLY RETURNS")
print("-" * 80)
if findings['canned']:
    print(f"  ⚠️  Found {len(findings['canned'])} canned responses")
    for i, line in findings['canned'][-5:]:
        print(f"  Line {i}: {line}")
    print("  → These bypass cache storage!")
else:
    print("  ✅ No canned responses found")

print("\n8. CACHE KEYS (if using debug logging)")
print("-" * 80)
if findings['key']:
    keys_seen = set()
    for i, line in findings['key']:
        # Extract the key
        match = re.search(r'(q:en:[a-f0-9]+)', line)
        if match:
            key = match.group(1)
            keys_seen.add(key)
            print(f"  {key}")

    if len(keys_seen) > 1:
        print(f"\n  ⚠️  FOUND {len(keys_seen)} DIFFERENT KEYS!")
        print("  This could indicate key mismatch between check and store")
    elif len(keys_seen) == 1:
        print(f"\n  ✅ Consistent key usage")
else:
    print("  No debug key logging found (add with add_debug_logging.py)")

# Analysis
print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if not findings['store']:
    print("🔴 CRITICAL: No cache stores found!")
    print("   Responses are NOT being cached at all!")
    print("   Possible causes:")
    print("   - Early returns (canned responses, classification errors)")
    print("   - cache.set() is never reached")
    print("   - Pipeline is using old code")

elif not findings['hit']:
    print("🟡 WARNING: Cache stores exist but no cache hits!")
    print("   Responses ARE being cached, but not being retrieved!")
    print("   Possible causes:")
    print("   - Key mismatch between check and store")
    print("   - Cache being flushed between requests")
    print("   - Different Redis instance for read vs write")
    print("   - TTL expired (but unlikely if testing quickly)")

elif findings['hit'] and findings['store']:
    hit_count = len(findings['hit'])
    store_count = len(findings['store'])
    print(f"✅ Cache is working!")
    print(f"   Cache hits: {hit_count}")
    print(f"   Cache stores: {store_count}")
    if hit_count > store_count * 0.5:
        print(f"   Good hit rate: {hit_count / (hit_count + len(findings['miss'])) * 100:.1f}%")
    else:
        print(f"   Low hit rate - investigate why")

if findings['fail']:
    print("\n🔴 Cache failures detected - check Redis connection!")

if findings['canned']:
    print(f"\n⚠️  {len(findings['canned'])} requests used canned responses")
    print("   These bypass cache - check query classifier!")

print("\n" + "=" * 80)
