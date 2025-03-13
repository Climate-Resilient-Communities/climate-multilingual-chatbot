import asyncio
import time
from src.models.gen_response_nova import nova_chat
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

async def test_speeds():
    print("\n=== Testing Response Generation Speeds ===")
    
    # Load environment and initialize client
    load_environment()
    nova_client = BedrockModel()
    
    # More comprehensive test documents
    test_docs = [
        {
            'title': 'Climate Adaptation Strategies',
            'content': 'Climate adaptation involves adjusting to actual or expected climate effects. Key strategies include improving water management, developing resilient agriculture, and protecting coastal areas.',
            'url': ['https://example.com/adaptation']
        },
        {
            'title': 'Urban Resilience Planning',
            'content': 'Cities are implementing green infrastructure and sustainable urban drainage systems to handle increased rainfall and flooding risks due to climate change.',
            'url': ['https://example.com/urban-resilience']
        },
        {
            'title': 'Agricultural Adaptation',
            'content': 'Farmers are adapting to climate change by diversifying crops, improving irrigation efficiency, and using drought-resistant varieties.',
            'url': ['https://example.com/agriculture']
        }
    ]
    
    query = "What are the main strategies for climate change adaptation in urban areas and agriculture?"
    
    # Test 1: First Call (no cache)
    print("\nTesting first call (no cache)...")
    start_time = time.time()
    response, citations = await nova_chat(query, test_docs, nova_client)
    first_time = time.time() - start_time
    print(f"First call time: {first_time:.2f} seconds")
    
    # Test 2: Second Call (should use cache)
    print("\nTesting second call (should use cache)...")
    start_time = time.time()
    response, citations = await nova_chat(query, test_docs, nova_client)
    second_time = time.time() - start_time
    print(f"Second call time: {second_time:.2f} seconds")
    
    # Print summary
    print("\n=== Speed Test Summary ===")
    print(f"First call (no cache): {first_time:.2f}s")
    print(f"Second call (with cache): {second_time:.2f}s")
    if second_time > 0:
        print(f"Cache speedup: {(first_time/second_time):.1f}x faster")
    else:
        print("Cache speedup: Instant (near zero second response)")

if __name__ == "__main__":
    asyncio.run(test_speeds())