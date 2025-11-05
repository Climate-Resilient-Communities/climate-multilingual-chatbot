# Quick Cache Debugging Guide

## You Just Asked The Question and It's Still Not Caching!

Here's what to do **right now**:

---

## Option 1: Check Existing Logs (FASTEST)

```bash
# Download the analyze script
python3 analyze_cache_logs.py /path/to/your/app.log

# Or if using Docker:
docker logs climate-chatbot 2>&1 | python3 analyze_cache_logs.py -
```

**This will tell you:**
- ✅ Is cache being stored? ("Cache stores found")
- ✅ Is cache being hit? ("Cache hits found")
- ❌ Are there failures? ("Cache failures detected")
- ⚠️ Early returns bypassing cache? ("Canned responses found")

---

## Option 2: Add Debug Logging (MOST DETAILED)

```bash
# Add debug markers to your code
python3 add_debug_logging.py

# Restart your app
docker-compose restart
# OR
sudo systemctl restart your-app

# Ask the question TWICE:
# 1st time: Should see 🔍 CACHE STORE
# 2nd time: Should see Cache hit

# Check logs for 🔍 markers
docker logs climate-chatbot 2>&1 | grep "🔍"

# When done, remove debug logging
python3 remove_debug_logging.py
```

---

## Option 3: Direct Redis Check (IMMEDIATE)

```bash
# Check if the key exists in Redis RIGHT NOW
redis-cli GET "q:en:41d95a83486a6ab486548d9f3c506a59568a6ebd7cb7d7a617e1177fdad915d7"
```

**If returns `(nil)`:**
- The response was NEVER cached
- Check logs for "Response cached" or "Failed to cache"

**If returns JSON data:**
- The response IS in Redis!
- But pipeline isn't finding it → key mismatch or code issue

---

## What Each Tool Does:

### `analyze_cache_logs.py`
- **What:** Scans logs for cache patterns
- **Use:** Understand what's happening without adding code
- **Output:** Clear diagnosis of cache behavior

### `add_debug_logging.py`
- **What:** Adds 🔍 markers to show exact cache keys
- **Use:** See the actual keys being used
- **Output:** Proof of what keys are checked vs stored

### Direct Redis Commands
- **What:** Check Redis directly
- **Use:** Verify if data is actually there
- **Output:** Ground truth of cache state

---

## Expected Good Flow:

**Request 1:**
```
🔍 CACHE INIT: Redis cache initialized successfully
🔍 CACHE CHECK: key=q:en:41d95a83...
Cache miss for english query
(... generates response ...)
🔍 CACHE STORE: key=q:en:41d95a83...
🔍 CACHE STORE: SUCCESS!
✓ Response cached in english (model: nova)
```

**Request 2:**
```
🔍 CACHE CHECK: key=q:en:41d95a83...
✓ Cache hit for english - returning cached response
```

---

## Most Likely Problems & Quick Fixes:

### Problem: "No cache stores found"
**Diagnosis:** `analyze_cache_logs.py` shows no stores
**Cause:** Early return (canned response, classification error)
**Fix:** Check query classifier, look for "canned intent" in logs

### Problem: "Cache stores exist but no hits"
**Diagnosis:** Stores happen, but next request still misses
**Cause:** Key mismatch or Redis flush
**Fix:** Use `add_debug_logging.py` to compare keys

### Problem: "Failed to cache result"
**Diagnosis:** Error message in logs
**Cause:** Redis connection, memory, or permissions
**Fix:** Check Redis status: `redis-cli PING`

### Problem: "CACHE INIT: FAILED"
**Diagnosis:** Debug logging shows cache is None
**Cause:** Redis connection failed at startup
**Fix:** Check Redis connection string, SSL settings

---

## The Nuclear Option:

If nothing works, try this to verify the code itself:

```bash
# Flush ALL cache (WARNING: deletes everything!)
redis-cli FLUSHDB

# Add debug logging
python3 add_debug_logging.py

# Restart app
docker-compose restart

# Ask question ONCE
# Check logs - should see 🔍 CACHE STORE

# Ask question AGAIN
# Check logs - should see ✓ Cache hit

# If STILL not working, send me:
grep "🔍" /path/to/logs.txt
```

---

## What To Send Me:

Run ONE of these and send output:

**Option A - Analyze existing logs:**
```bash
python3 analyze_cache_logs.py /path/to/app.log
```

**Option B - Check Redis directly:**
```bash
redis-cli GET "q:en:41d95a83486a6ab486548d9f3c506a59568a6ebd7cb7d7a617e1177fdad915d7"
```

**Option C - With debug logging:**
```bash
# After adding debug logging and asking question twice:
grep "🔍\|Cache hit\|Cache miss" /path/to/app.log | tail -50
```

---

## Quick Checklist:

- [ ] Did you deploy the new code? (`git log -1` shows `b398277` or later)
- [ ] Did you restart the app after deploying?
- [ ] Is Redis running? (`redis-cli PING` returns `PONG`)
- [ ] Is the question being classified correctly? (not "off-topic")
- [ ] Are you checking the right logs? (not dev logs when testing prod)

---

**Pick ONE method above and run it NOW. Send me the output!**
