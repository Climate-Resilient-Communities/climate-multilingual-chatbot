from src.models.redis_cache import ClimateCache

def test_manual():
    print("\n=== Testing Redis Cache Operations ===")
    
    # Initialize cache
    cache = ClimateCache()
    
    # Test saving and retrieving a string
    print("\n1. Testing string cache:")
    test_str = "Hello Redis!"
    print(f"Saving string: {test_str}")
    if cache.save_to_cache("test_str", test_str):
        print("✓ String saved successfully")
        result = cache.get_from_cache("test_str")
        print(f"Retrieved: {result}")
        assert result == test_str, "String values don't match!"
        print("✓ String retrieval successful")
    
    # Test saving and retrieving a dictionary
    print("\n2. Testing dictionary cache:")
    test_dict = {
        "question": "What is climate change?",
        "answer": "A long-term change in weather patterns",
        "score": 0.95
    }
    print(f"Saving dictionary: {test_dict}")
    if cache.save_to_cache("test_dict", test_dict):
        print("✓ Dictionary saved successfully")
        result = cache.get_from_cache("test_dict")
        print(f"Retrieved: {result}")
        assert result == test_dict, "Dictionary values don't match!"
        print("✓ Dictionary retrieval successful")
    
    # Test deletion
    print("\n3. Testing deletion:")
    if cache.delete_cache("test_str"):
        print("✓ String deleted successfully")
        result = cache.get_from_cache("test_str")
        assert result is None, "String should be None after deletion!"
        print("✓ Deletion verified")
    
    # Test cache clear
    print("\n4. Testing cache clear:")
    if cache.clear_cache():
        print("✓ Cache cleared successfully")
        result = cache.get_from_cache("test_dict")
        assert result is None, "Dictionary should be None after clear!"
        print("✓ Clear verified")
    
    print("\nAll manual tests passed successfully! ✨")

if __name__ == "__main__":
    test_manual()