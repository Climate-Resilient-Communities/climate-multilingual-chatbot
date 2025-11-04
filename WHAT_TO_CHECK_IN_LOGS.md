# What to Check in Your Application Logs

You said you JUST asked: **"What are the local impacts of climate change in Toronto?"**

And it answered, but the next request still missed the cache.

## Step 1: Check First Request (The one you just made)

Search your logs for this exact sequence:

```
"Step 2: Cache Check"
"Cache miss for english query"  ← Should see this on first request
```

Then later in SAME request, look for:

```
"✓ Response cached in english (model: nova)"  ← CRITICAL: Was this logged?
```

or

```
"Failed to cache result:"  ← ERROR: Cache store failed!
```

## Step 2: Check Second Request (The one that should have hit)

Search logs for SECOND request with same question:

```
"Step 2: Cache Check"
"Cache miss for english query"  ← If you see this, cache didn't work!
```

vs

```
"✓ Cache hit for english - returning cached response"  ← This is what you SHOULD see
```

---

## Possible Scenarios:

### Scenario A: Cache Store Failed
**First request logs:**
```
"Cache miss for english query"
... (response generated) ...
"Failed to cache result: <ERROR MESSAGE>"  ← Look for this!
```

**Problem:** `cache.set()` is failing with an error
**Solutions:**
- Check Redis connection
- Check Redis memory (is it full?)
- Check Redis permissions

---

### Scenario B: Cache Store Succeeded, But Keys Don't Match
**First request logs:**
```
"Cache miss for english query"
... (response generated) ...
"✓ Response cached in english (model: nova)"  ← Success!
```

**Second request logs:**
```
"Cache miss for english query"  ← WTF?!
```

**Problem:** Cache key at line 516 (check) ≠ cache key at line 1091 (store)
**Cause:** Something is modifying `cache_key` or `normalized` between check and store
**Solution:** Need to add debug logging to print the exact keys

---

### Scenario C: Classification Bypass
**First request logs:**
```
"Cache miss for english query"
... (query rewriter runs) ...
"✓ Canned intent detected by query rewriter"  ← Uh oh!
```
or
```
"classification": "off-topic"  ← Wrong classification!
```

**Problem:** Query rewriter is misclassifying and returning canned response
**Result:** Never reaches cache.set() at line 1091
**Solution:** Check query rewriter logic

---

### Scenario D: Early Return
**First request logs:**
```
"Cache miss for english query"
... (processing) ...
"Fallback reason: <some_reason>"  ← Returned early!
```

**Problem:** One of many early return statements (lines 636, 659, etc)
**Result:** Bypassed cache.set() at line 1091
**Solution:** Check which fallback triggered

---

## What to Send Me:

Run this on your production server:

```bash
# Find your most recent request for this question
grep -A 200 "What are the local impacts of climate change in Toronto" /path/to/logs/app.log | tail -250
```

Send me the output, especially look for:
1. ✅ "Response cached in english" - Cache store succeeded
2. ❌ "Failed to cache result" - Cache store failed
3. ❓ Early return with canned/fallback response - Bypassed cache

---

## Quick Debug Commands:

### Check if cache.set() is being called:
```bash
grep "Response cached in" /path/to/logs/app.log | tail -5
```

### Check if cache.set() is failing:
```bash
grep "Failed to cache result" /path/to/logs/app.log | tail -5
```

### Check cache hits/misses:
```bash
grep "Cache hit\|Cache miss" /path/to/logs/app.log | tail -20
```

### Check if queries are being classified wrong:
```bash
grep "classification" /path/to/logs/app.log | tail -10
```

---

## Expected Good Logs:

**Request 1 (first time asking):**
```
Step 2: Cache Check
Cache miss for english query
... (generate response) ...
✓ Response cached in english (model: nova)
✓ Query processed successfully in 8.23s
```

**Request 2 (second time asking):**
```
Step 2: Cache Check
✓ Cache hit for english - returning cached response
✓ Query processed successfully in 0.08s  ← Super fast!
```

---

## If You Can't Find Logs:

Add this to your pipeline temporarily (line 1092):
```python
await self.cache.set(cache_key, result)
logger.error(f"🔍 DEBUG: Stored cache_key={cache_key}, normalized='{normalized}'")
```

And at line 516:
```python
cache_key = self._make_cache_key(language_code, normalized)
logger.error(f"🔍 DEBUG: Looking for cache_key={cache_key}, normalized='{normalized}'")
```

Then ask the question twice and send me both DEBUG lines.
