#!/usr/bin/env python3
"""
Simple test script to verify the FastAPI backend is working
Run this after starting the API server
"""

import asyncio
import aiohttp
import json
import time

API_BASE = "http://localhost:8000"

async def test_api():
    """Test basic API functionality"""
    async with aiohttp.ClientSession() as session:
        
        print("🧪 Testing Climate Chatbot API...")
        
        # Test health endpoint
        print("\n1. Testing health endpoints...")
        try:
            async with session.get(f"{API_BASE}/health") as resp:
                data = await resp.json()
                print(f"   ✅ /health: {data['status']}")
                
            async with session.get(f"{API_BASE}/health/ready") as resp:
                data = await resp.json()
                print(f"   ✅ /health/ready: {data['status']}")
                
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return
        
        # Test language support
        print("\n2. Testing language support...")
        try:
            async with session.get(f"{API_BASE}/api/v1/languages/supported") as resp:
                data = await resp.json()
                command_a_count = len(data['command_a_languages'])
                nova_count = len(data['nova_languages'])
                total_count = data['total_supported']
                print(f"   ✅ Languages: Command A={command_a_count}, Nova={nova_count}, Total={total_count}")
                
        except Exception as e:
            print(f"   ❌ Language support failed: {e}")
        
        # Test rate limiting
        print("\n2.5. Testing rate limiting...")
        try:
            # Make multiple quick requests to trigger rate limit
            for i in range(12):  # More than the 10/minute limit
                async with session.post(
                    f"{API_BASE}/api/v1/languages/validate",
                    json={"query": f"test query {i}"}
                ) as resp:
                    if resp.status == 429:
                        print(f"   ✅ Rate limiting works: Got 429 on request {i+1}")
                        break
            else:
                print(f"   ⚠️ Rate limiting not triggered (may need faster requests)")
                
        except Exception as e:
            print(f"   ❌ Rate limiting test failed: {e}")
        
        # Test language validation
        print("\n3. Testing language validation...")
        try:
            validation_request = {
                "query": "What is climate change?",
                "detected_language": "en"
            }
            async with session.post(
                f"{API_BASE}/api/v1/languages/validate",
                json=validation_request
            ) as resp:
                data = await resp.json()
                print(f"   ✅ Language validation: {data['detected_language']} -> {data['recommended_model']}")
                
        except Exception as e:
            print(f"   ❌ Language validation failed: {e}")
        
        # Test chat query (the main integration)
        print("\n4. Testing chat query (main pipeline integration)...")
        try:
            chat_request = {
                "query": "What are the impacts of climate change?",
                "language": "en",
                "conversation_history": [],
                "stream": False
            }
            
            start_time = time.time()
            async with session.post(
                f"{API_BASE}/api/v1/chat/query",
                json=chat_request
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    processing_time = time.time() - start_time
                    
                    print(f"   ✅ Chat query successful!")
                    print(f"      Response length: {len(data['response'])} chars")
                    print(f"      Citations: {len(data['citations'])}")
                    print(f"      Faithfulness: {data['faithfulness_score']:.3f}")
                    print(f"      Model used: {data['model_used']}")
                    print(f"      Processing time: {processing_time:.3f}s")
                    print(f"      Language: {data['language_used']}")
                else:
                    error_data = await resp.json()
                    print(f"   ❌ Chat query failed: {resp.status}")
                    print(f"      Error: {error_data}")
                
        except Exception as e:
            print(f"   ❌ Chat query failed: {e}")
        
        # Test feedback submission
        print("\n5. Testing feedback submission...")
        try:
            feedback_request = {
                "message_id": "test_message_123",
                "feedback_type": "thumbs_up",
                "categories": ["comprehensive", "expected"],
                "comment": "Great response!",
                "language_code": "en"
            }
            
            async with session.post(
                f"{API_BASE}/api/v1/feedback/submit",
                json=feedback_request
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Feedback submitted: {data['feedback_id']}")
                else:
                    error_data = await resp.json()
                    print(f"   ❌ Feedback failed: {resp.status}")
                    print(f"      Error: {error_data}")
                
        except Exception as e:
            print(f"   ❌ Feedback submission failed: {e}")
        
        print("\n🎉 API testing complete!")
        print("\nNext steps:")
        print("1. If all tests pass, the backend integration is working")
        print("2. Update the Next.js frontend to use these API endpoints")
        print("3. Test the complete frontend-backend integration")

if __name__ == "__main__":
    print("Starting API integration test...")
    print("Make sure the API server is running:")
    print("   uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload")
    print()
    
    asyncio.run(test_api())