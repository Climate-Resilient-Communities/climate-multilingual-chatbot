from src.models.redis_cache import ClimateCache

def test_manual():
    """Manual test for Redis cache functionality."""
    try:
        cache = ClimateCache()
        # Simple test to check if Redis is available
        is_connected = hasattr(cache, 'redis_client') and not getattr(cache, '_closed', True)
        print(f"Redis connection status: {'Connected' if is_connected else 'Not connected'}")
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_manual()