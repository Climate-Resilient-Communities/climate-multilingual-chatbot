# Caching (Redis) Guide

This guide explains how caching works to speed up responses in the Climate Multilingual Chatbot.

---

## Why Caching?

Processing a query takes 3-4 seconds:
- Embedding generation
- Vector search
- LLM calls
- Reranking

**Caching** stores responses so repeated questions are instant:

```
First request: 3.2 seconds
Cached request: 0.05 seconds (60x faster!)
```

---

## Cache Architecture

**Technology**: [Redis](https://redis.io/) - an in-memory data store

**File**: [`src/models/redis_cache.py`](../../src/models/redis_cache.py)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CACHE FLOW                                   │
│                                                                      │
│   Query: "What is climate change?"                                  │
│          │                                                          │
│          ▼                                                          │
│   ┌──────────────┐                                                  │
│   │  Normalize   │ "what is climate change"                        │
│   └──────────────┘                                                  │
│          │                                                          │
│          ▼                                                          │
│   ┌──────────────┐                                                  │
│   │    Hash      │ SHA256 → "a7b9c3d..."                           │
│   └──────────────┘                                                  │
│          │                                                          │
│          ▼                                                          │
│   ┌──────────────┐                                                  │
│   │  Cache Key   │ "q:en:a7b9c3d..."                               │
│   └──────────────┘                                                  │
│          │                                                          │
│          ▼                                                          │
│   ┌──────────────┐      ┌──────────────┐                           │
│   │    Redis     │──────│  Response    │                           │
│   │   Lookup     │      │  (if cached) │                           │
│   └──────────────┘      └──────────────┘                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Cache Key Structure

Keys are language-specific to handle multilingual responses:

```
Format: q:{language_code}:{query_hash}

Examples:
  q:en:a7b9c3d...  (English query)
  q:es:f8e2a1b...  (Spanish query)
  q:fr:c3d4e5f...  (French query)
```

**Why language in key?**
- Same query in different languages → different responses
- "What is climate?" (en) ≠ "¿Qué es el clima?" (es)

---

## Cache Implementation

### ClimateCache Class

**File**: [`src/models/redis_cache.py`](../../src/models/redis_cache.py)

```python
class ClimateCache:
    """Redis-based cache for climate chatbot responses."""

    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true"
        )
        self.expiration = 3600  # 1 hour TTL

    async def get(self, key: str) -> Optional[dict]:
        """Get cached value."""
        value = await asyncio.to_thread(self.client.get, key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: dict) -> None:
        """Cache a value with TTL."""
        await asyncio.to_thread(
            self.client.setex,
            key,
            self.expiration,
            json.dumps(value)
        )
```

### Key Generation

**File**: [`src/models/climate_pipeline.py`](../../src/models/climate_pipeline.py) (lines 1159-1177)

```python
def _make_cache_key(self, query: str, language: str) -> str:
    """Generate cache key for a query."""
    # Normalize query
    normalized = self._normalize_query(query)
    # Hash for consistent length
    query_hash = hashlib.sha256(normalized.encode()).hexdigest()
    # Combine with language
    return f"q:{language}:{query_hash}"

def _normalize_query(self, query: str) -> str:
    """Normalize query for cache matching."""
    # Lowercase
    query = query.lower()
    # Remove extra whitespace
    query = re.sub(r'\s+', ' ', query).strip()
    return query
```

---

## Fuzzy Cache Matching

We also match *similar* queries (not just exact):

```
Exact match: "What is climate change?"
Fuzzy match: "What's climate change?"  (92% similar → HIT!)
```

### How It Works

**File**: [`src/models/climate_pipeline.py`](../../src/models/climate_pipeline.py) (lines 1179-1241)

```python
async def _try_fuzzy_cache_match(self, query: str, language: str) -> Optional[dict]:
    """Find similar cached queries."""

    # Get recent queries for this language
    recent_key = f"q:recent:{language}"
    recent_queries = await self.cache.get_list(recent_key, 0, 50)

    # Normalize current query
    normalized = self._normalize_query(query)
    query_tokens = set(normalized.split())

    # Check each recent query
    for cached_query in recent_queries:
        cached_tokens = set(cached_query.split())

        # Jaccard similarity
        intersection = query_tokens & cached_tokens
        union = query_tokens | cached_tokens
        similarity = len(intersection) / len(union)

        # 92% threshold
        if similarity >= 0.92:
            return await self.cache.get(f"q:{language}:{hash(cached_query)}")

    return None
```

---

## Cache Bypass

Users can force fresh responses:

```python
# In ChatRequest
{
    "query": "What is climate change?",
    "skip_cache": true  # Force fresh processing
}
```

Used for:
- Testing changes
- Refreshing stale data
- Debugging

---

## Cache Storage

### What's Cached

```python
{
    "success": True,
    "response": "Climate change refers to...",
    "citations": [
        {"title": "IPCC Report", "url": "...", "snippet": "..."}
    ],
    "faithfulness_score": 0.85,
    "language_used": "en",
    "model_used": "nova",
    "cached_at": "2024-01-15T10:30:00Z"
}
```

### TTL (Time To Live)

| Data Type | TTL | Purpose |
|-----------|-----|---------|
| Query responses | 1 hour | Balance freshness/performance |
| Consent records | 30 days | User preferences |
| Feedback | Forever | Analytics |
| Recent queries | 1 hour | Fuzzy matching |

---

## Redis Configuration

### Connection Settings

**File**: [`src/data/config/config.py`](../../src/data/config/config.py) (lines 111-116)

```python
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": 0,
    "expiration": 3600  # 1 hour
}
```

### Persistence Settings

**File**: [`redis.conf`](../../redis.conf)

```bash
# Append-Only File (recommended)
appendonly yes
appendfsync everysec

# RDB Snapshots (backup)
save 60 1       # Every 60s if 1+ change
save 300 10     # Every 5min if 10+ changes

# Memory limit
maxmemory 512mb
maxmemory-policy allkeys-lru  # Evict least-recently-used
```

---

## Performance Impact

### Without Cache

```
User 1: "What is climate change?" → 3.2s
User 2: "What is climate change?" → 3.1s
User 3: "What is climate change?" → 3.3s
```

### With Cache

```
User 1: "What is climate change?" → 3.2s (cache miss)
User 2: "What is climate change?" → 0.05s (cache hit!)
User 3: "What is climate change?" → 0.04s (cache hit!)
User 4: "What's climate change?" → 0.05s (fuzzy hit!)
```

**Hit rate typically: 30-50%** of queries are cached

---

## Other Cached Data

### Consent Records

```python
# Key: consent:{session_id}
# Value: "accepted"
# TTL: 30 days

await cache.set(f"consent:{session_id}", "accepted", ttl=2592000)
```

### Feedback

```python
# Key: feedback:{feedback_id}
# Value: {message_id, type, categories, comment, ...}
# TTL: None (permanent)

await cache.store_feedback(f"feedback:{feedback_id}", feedback_data)
```

### Message Feedback List

```python
# Key: message_feedback:{message_id}
# Value: List of feedback IDs
# Used to retrieve all feedback for a message

await cache.add_to_list(f"message_feedback:{msg_id}", feedback_id)
```

---

## Running Redis

### Local Development

```bash
# Option 1: Use the startup script
./start-redis.sh

# Option 2: Direct start
redis-server --daemonize yes

# Option 3: With custom config
redis-server redis.conf
```

### Docker

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
```

### Verify Connection

```bash
redis-cli ping
# Should return: PONG

redis-cli keys "q:*"
# Lists all cached queries
```

---

## Debugging Cache

### Check Cache Contents

```bash
# Connect to Redis
redis-cli

# Count cached queries
KEYS q:en:*
# Returns all English query keys

# Get a cached response
GET q:en:a7b9c3d...

# Check TTL
TTL q:en:a7b9c3d...
# Returns remaining seconds
```

### Clear Cache

```bash
# Clear all cache (development only!)
redis-cli FLUSHDB

# Clear specific pattern
redis-cli KEYS "q:en:*" | xargs redis-cli DEL
```

### Debug Scripts

| Script | Purpose |
|--------|---------|
| [`debug_redis_cache.py`](../../debug_redis_cache.py) | Inspect cache contents |
| [`diagnose_cache_issue.py`](../../diagnose_cache_issue.py) | Troubleshoot problems |
| [`test_cache_fix.py`](../../test_cache_fix.py) | Validate cache behavior |

---

## Key Files

| File | Purpose |
|------|---------|
| [`redis_cache.py`](../../src/models/redis_cache.py) | Cache implementation |
| [`climate_pipeline.py`](../../src/models/climate_pipeline.py) | Cache integration |
| [`redis.conf`](../../redis.conf) | Redis configuration |
| [`start-redis.sh`](../../start-redis.sh) | Redis startup script |
| [`REDIS_CACHE_FIX.md`](../../REDIS_CACHE_FIX.md) | Troubleshooting guide |

---

## Learn More

- [Redis Documentation](https://redis.io/docs/)
- [AI Pipeline Guide](./03-ai-pipeline.md)
- [Configuration Guide](./06-configuration.md)
