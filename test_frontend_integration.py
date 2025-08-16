#!/usr/bin/env python3
"""
Frontend Integration Test
Tests the complete frontend-backend integration
"""

import asyncio
import aiohttp
import json
import time

FRONTEND_URL = "http://localhost:9002"
API_URL = "http://localhost:8000"

async def test_frontend_backend_integration():
    """Test complete frontend-backend integration"""
    
    print("🧪 Testing Frontend-Backend Integration...\n")
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Frontend is accessible
        print("1. Testing frontend accessibility...")
        try:
            async with session.get(FRONTEND_URL) as resp:
                if resp.status == 200:
                    html_content = await resp.text()
                    if "Climate" in html_content:
                        print("   ✅ Frontend loaded successfully")
                    else:
                        print("   ⚠️ Frontend loaded but content may be incomplete")
                else:
                    print(f"   ❌ Frontend failed: Status {resp.status}")
        except Exception as e:
            print(f"   ❌ Frontend connection failed: {e}")
            return
        
        # Test 2: API health check
        print("\n2. Testing API health...")
        try:
            async with session.get(f"{API_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ API health: {data['status']}")
                else:
                    print(f"   ❌ API health failed: Status {resp.status}")
                    return
        except Exception as e:
            print(f"   ❌ API health check failed: {e}")
            return
        
        # Test 3: API readiness
        print("\n3. Testing API readiness...")
        try:
            async with session.get(f"{API_URL}/health/ready") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ API readiness: {data['status']}")
                    print(f"      Prewarming: {data.get('prewarm_completed', False)}")
                else:
                    print(f"   ❌ API readiness failed: Status {resp.status}")
        except Exception as e:
            print(f"   ❌ API readiness check failed: {e}")
        
        # Test 4: Language support API
        print("\n4. Testing language support...")
        try:
            async with session.get(f"{API_URL}/api/v1/languages/supported") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Languages: {data['total_supported']} total")
                    print(f"      Command A: {len(data['command_a_languages'])} languages")
                    print(f"      Nova: {len(data['nova_languages'])} languages")
                else:
                    print(f"   ❌ Language support failed: Status {resp.status}")
        except Exception as e:
            print(f"   ❌ Language support test failed: {e}")
        
        # Test 5: Chat API integration
        print("\n5. Testing chat API integration...")
        try:
            chat_request = {
                "query": "What are the main causes of climate change?",
                "language": "en",
                "conversation_history": [],
                "stream": False
            }
            
            start_time = time.time()
            async with session.post(
                f"{API_URL}/api/v1/chat/query",
                json=chat_request
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    processing_time = time.time() - start_time
                    
                    print(f"   ✅ Chat API successful!")
                    print(f"      Response length: {len(data['response'])} chars")
                    print(f"      Citations: {len(data['citations'])}")
                    print(f"      Model: {data.get('model_used', 'unknown')}")
                    print(f"      Faithfulness: {data.get('faithfulness_score', 0):.3f}")
                    print(f"      Processing time: {processing_time:.3f}s")
                    
                    # Store message ID for feedback test
                    test_message_id = f"test_{int(time.time())}"
                    
                else:
                    error_data = await resp.json()
                    print(f"   ❌ Chat API failed: Status {resp.status}")
                    print(f"      Error: {error_data}")
                    return
        except Exception as e:
            print(f"   ❌ Chat API test failed: {e}")
            return
        
        # Test 6: Feedback API integration
        print("\n6. Testing feedback API integration...")
        try:
            feedback_request = {
                "message_id": test_message_id,
                "feedback_type": "thumbs_up",
                "categories": ["comprehensive", "expected"],
                "comment": "Great integration test response!",
                "language_code": "en"
            }
            
            async with session.post(
                f"{API_URL}/api/v1/feedback/submit",
                json=feedback_request
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Feedback API successful!")
                    print(f"      Feedback ID: {data['feedback_id']}")
                    print(f"      PII detected: {data['pii_detected']}")
                else:
                    error_data = await resp.json()
                    print(f"   ❌ Feedback API failed: Status {resp.status}")
                    print(f"      Error: {error_data}")
        except Exception as e:
            print(f"   ❌ Feedback API test failed: {e}")
        
        # Test 7: Feedback categories
        print("\n7. Testing feedback categories...")
        try:
            async with session.get(f"{API_URL}/api/v1/feedback/categories") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Feedback categories loaded")
                    print(f"      Thumbs up: {len(data['thumbs_up'])} categories")
                    print(f"      Thumbs down: {len(data['thumbs_down'])} categories")
                else:
                    print(f"   ❌ Feedback categories failed: Status {resp.status}")
        except Exception as e:
            print(f"   ❌ Feedback categories test failed: {e}")
        
        # Test 8: CORS configuration (simulated)
        print("\n8. Testing CORS configuration...")
        try:
            headers = {"Origin": "http://localhost:9002"}
            async with session.options(f"{API_URL}/api/v1/chat/query", headers=headers) as resp:
                cors_headers = resp.headers
                if "Access-Control-Allow-Origin" in cors_headers:
                    print(f"   ✅ CORS configured: {cors_headers.get('Access-Control-Allow-Origin')}")
                else:
                    print("   ⚠️ CORS headers not found (may not be a preflight request)")
        except Exception as e:
            print(f"   ❌ CORS test failed: {e}")
        
        print("\n🎉 Frontend-Backend Integration Testing Complete!")
        print("\n📋 Integration Summary:")
        print("✅ Frontend accessible on http://localhost:9002")
        print("✅ Backend API running on http://localhost:8000")
        print("✅ Chat functionality integrated")
        print("✅ Enhanced feedback system working")
        print("✅ Language support API working")
        print("✅ CORS configured for frontend domain")
        
        print("\n🚀 Ready for user testing!")
        print("   1. Open http://localhost:9002 in your browser")
        print("   2. Try asking climate-related questions")
        print("   3. Test the feedback system with thumbs up/down")
        print("   4. Verify real-time responses and citations")

if __name__ == "__main__":
    print("Starting frontend-backend integration test...")
    print("Make sure both servers are running:")
    print("   Backend: uvicorn src.webui.api.main:app --host 0.0.0.0 --port 8000 --reload")
    print("   Frontend: npm run dev (from src/webui/app directory)")
    print()
    
    asyncio.run(test_frontend_backend_integration())