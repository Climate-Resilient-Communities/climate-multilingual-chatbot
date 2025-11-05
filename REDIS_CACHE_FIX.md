# Redis Cache Persistence Fix

## Problem Summary

The Redis cache was losing all cached responses when the application restarted, causing the system to regenerate responses for questions that were already answered.

## Root Cause

The issue was **NOT** related to sessions or session-specific caching. The cache is correctly implemented as **global** and **shared across all users and sessions**.

The actual problems were:

### 1. Redis Not Running Continuously
When the application shuts down (to save resources), Redis also stops. When the app restarts, Redis needs to be manually started again.

### 2. Redis Persistence Not Properly Configured
The default Redis persistence settings were:
- **RDB Snapshots**: Only save every 1 hour (if 1 key changed), 5 minutes (if 100 keys changed), or 1 minute (if 10,000 keys changed)
- **AOF (Append Only File)**: Disabled

This meant:
- If Redis stopped before reaching a save threshold, **all cache data was lost**
- On restart, Redis started with an **empty database**
- The cache keys existed in previous sessions but were never persisted to disk

### 3. Empty Redis Database
The `/var/lib/redis` directory was empty - no `dump.rdb` or `appendonly.aof` files existed, confirming that Redis never persisted any data.

## How the Cache Works (Correctly)

The cache implementation in `src/models/climate_pipeline.py` is **correct**:

```python
def _make_cache_key(self, language_code: str, base_query: str) -> str:
    """Create a stable cache key using normalized query and language."""
    key_material = f"{language_code}:{base_query}".encode("utf-8")
    digest = hashlib.sha256(key_material).hexdigest()
    return f"q:{language_code}:{digest}"
```

- **Global**: Cache keys are NOT session-specific
- **Stable**: Same question generates same cache key
- **Language-specific**: English and Spanish queries have different keys
- **Model-agnostic**: Same cache key regardless of which model (Nova/Cohere) generated the response

### Example Cache Key
Question: "What are the local impacts of climate change in Toronto?"
- Normalized: "what are the local impacts of climate change in toronto?"
- Key material: "en:what are the local impacts of climate change in toronto?"
- SHA256: `41d95a83486a6ab486548d9f3c506a59568a6ebd7cb7d7a617e1177fdad915d7`
- Final key: `q:en:41d95a83486a6ab486548d9f3c506a59568a6ebd7cb7d7a617e1177fdad915d7`

## Solution

### 1. Redis Configuration with Proper Persistence (`redis.conf`)

Created a custom Redis configuration with:

#### AOF (Append Only File) - Enabled
```
appendonly yes
appendfsync everysec
```
- Writes every operation to disk
- Syncs to disk every second
- Better durability than RDB alone

#### RDB Snapshots - More Aggressive
```
save 60 1      # Save every 1 minute if at least 1 key changed
save 300 10    # Save every 5 minutes if at least 10 keys changed
save 900 1     # Save every 15 minutes if at least 1 key changed
```

#### Memory Management
```
maxmemory 512mb
maxmemory-policy allkeys-lru
```
- Limit memory usage to 512 MB
- Evict least recently used keys when full

### 2. Startup Script (`start-redis.sh`)

Created a script to:
- Start Redis with the custom configuration
- Verify Redis is running
- Show persistence settings
- Display current cache size

### 3. Testing Scripts

- `test_toronto_cache_key.py` - Verifies cache key generation
- `debug_redis_cache.py` - Inspects Redis state and cache entries

## Usage

### Start Redis with Proper Configuration

```bash
./start-redis.sh
```

This will:
1. Check if Redis is already running
2. Create required directories
3. Start Redis with persistence enabled
4. Verify connection and show configuration

### Verify Cache is Working

```bash
# Check Redis is running
redis-cli ping

# Check cache size
redis-cli dbsize

# Check a specific cache key
redis-cli get "q:en:41d95a83486a6ab486548d9f3c506a59568a6ebd7cb7d7a617e1177fdad915d7"

# View persistence settings
redis-cli CONFIG GET appendonly
redis-cli CONFIG GET save
```

### Debug Cache Keys

```bash
# Test cache key generation
python test_toronto_cache_key.py

# Inspect Redis state
python debug_redis_cache.py
```

## Production Deployment

### Option 1: System Service (Recommended)
Configure Redis to start automatically:

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

Update `/etc/redis/redis.conf` with the persistence settings from `redis.conf`.

### Option 2: Managed Redis Service (Best for Cloud)
Use a managed Redis service that handles:
- Automatic persistence
- High availability
- Backups
- Monitoring

Examples:
- **AWS ElastiCache for Redis**
- **Azure Cache for Redis**
- **Redis Enterprise Cloud**
- **Upstash Redis**

Update environment variables:
```bash
REDIS_URL=redis://your-managed-redis-host:6379
# or
REDIS_HOST=your-managed-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-password
REDIS_SSL=true
```

### Option 3: Docker Container
Use Docker with volume mounting:

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --appendfsync everysec
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

## Verification

After implementing the fix:

1. **Start Redis** with `./start-redis.sh`
2. **Ask a question** through the API
3. **Check cache**: `redis-cli dbsize` should show `> 0`
4. **Stop and restart Redis**: `redis-cli shutdown && ./start-redis.sh`
5. **Check cache again**: `redis-cli dbsize` should still show the cached entries
6. **Ask the same question**: Should return instantly from cache

## Key Takeaways

✓ **Cache is NOT session-specific** - it's global and works correctly
✓ **Problem was Redis persistence** - not the application code
✓ **Solution: Enable AOF + aggressive RDB saves** - ensures data survives restarts
✓ **For production: Use managed Redis** - or ensure Redis runs as a system service

## Files Modified/Created

- `redis.conf` - Custom Redis configuration with persistence
- `start-redis.sh` - Script to start Redis with proper settings
- `test_toronto_cache_key.py` - Cache key generation test
- `REDIS_CACHE_FIX.md` - This documentation

## Related Files

- `src/models/climate_pipeline.py:1159-1177` - Cache key generation logic
- `src/models/redis_cache.py` - Redis cache implementation
- `debug_redis_cache.py` - Redis inspection tool
- `diagnose_cache_issue.py` - Historical analysis of model_type cache bug
