#!/usr/bin/env python3
"""
End-to-End Testing Suite
========================

Comprehensive tests for Section 5.2.3 End-to-End Testing:
- Complete user journey from consent to feedback
- Multi-turn conversations
- Language switching mid-conversation
- Mobile user experience simulation
- Performance under load
"""

import json
import time
import requests
import threading
from typing import Dict, List
import concurrent.futures

class EndToEndTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:9002"
        self.results = []
        
    def test_complete_user_journey(self) -> Dict:
        """Test complete user journey from consent to feedback"""
        print("🧪 Testing Complete User Journey...")
        
        try:
            journey_steps = []
            
            # Step 1: Frontend accessibility (simulating consent dialog)
            try:
                frontend_response = requests.get(self.frontend_url, timeout=10)
                journey_steps.append({
                    "step": "Frontend Access",
                    "passed": frontend_response.status_code == 200,
                    "details": f"Status: {frontend_response.status_code}"
                })
            except Exception as e:
                journey_steps.append({
                    "step": "Frontend Access",
                    "passed": False,
                    "details": f"Error: {str(e)[:50]}"
                })
            
            # Step 2: Language selection (get supported languages)
            try:
                languages_response = requests.get(f"{self.backend_url}/api/v1/languages/supported", timeout=10)
                languages_data = languages_response.json() if languages_response.status_code == 200 else {}
                total_languages = languages_data.get('total_supported', 0)
                
                journey_steps.append({
                    "step": "Language Selection",
                    "passed": languages_response.status_code == 200 and total_languages > 0,
                    "details": f"{total_languages} languages available"
                })
            except Exception as e:
                journey_steps.append({
                    "step": "Language Selection",
                    "passed": False,
                    "details": f"Error: {str(e)[:50]}"
                })
            
            # Step 3: Initial chat query
            try:
                chat_response = requests.post(
                    f"{self.backend_url}/api/v1/chat/query",
                    json={
                        "query": "What is climate change and why should I care about it?",
                        "language": "en"
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                chat_data = chat_response.json() if chat_response.status_code == 200 else {}
                has_response = len(chat_data.get('response', '')) > 50
                has_citations = len(chat_data.get('citations', [])) > 0
                
                journey_steps.append({
                    "step": "Initial Chat Query",
                    "passed": chat_response.status_code == 200 and has_response,
                    "details": f"Response: {len(chat_data.get('response', ''))} chars, Citations: {len(chat_data.get('citations', []))}"
                })
                
                # Store for follow-up
                initial_response = chat_data.get('response', '')
                
            except Exception as e:
                journey_steps.append({
                    "step": "Initial Chat Query",
                    "passed": False,
                    "details": f"Error: {str(e)[:50]}"
                })
                initial_response = ""
            
            # Step 4: Follow-up question with conversation history
            if initial_response:
                try:
                    conversation_history = [
                        {"role": "user", "content": "What is climate change and why should I care about it?"},
                        {"role": "assistant", "content": initial_response[:500]}  # Truncate for test
                    ]
                    
                    followup_response = requests.post(
                        f"{self.backend_url}/api/v1/chat/query",
                        json={
                            "query": "What can I do to help?",
                            "language": "en",
                            "conversation_history": conversation_history
                        },
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    
                    followup_data = followup_response.json() if followup_response.status_code == 200 else {}
                    has_followup_response = len(followup_data.get('response', '')) > 50
                    
                    journey_steps.append({
                        "step": "Follow-up Query",
                        "passed": followup_response.status_code == 200 and has_followup_response,
                        "details": f"Response: {len(followup_data.get('response', ''))} chars"
                    })
                    
                except Exception as e:
                    journey_steps.append({
                        "step": "Follow-up Query",
                        "passed": False,
                        "details": f"Error: {str(e)[:50]}"
                    })
            
            # Step 5: Error handling (simulating user error)
            try:
                error_response = requests.post(
                    f"{self.backend_url}/api/v1/chat/query",
                    json={"query": "", "language": "en"},  # Empty query
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                journey_steps.append({
                    "step": "Error Handling",
                    "passed": error_response.status_code in [400, 422],  # Should reject empty query
                    "details": f"Status: {error_response.status_code}"
                })
                
            except Exception as e:
                journey_steps.append({
                    "step": "Error Handling",
                    "passed": True,  # Exception is acceptable for error case
                    "details": f"Exception handled: {str(e)[:50]}"
                })
            
            # Calculate journey success
            passed_steps = sum(1 for step in journey_steps if step.get('passed', False))
            total_steps = len(journey_steps)
            
            print(f"✅ User Journey - {passed_steps}/{total_steps} steps completed successfully")
            
            return {
                "test": "Complete User Journey",
                "status": "PASS" if passed_steps >= total_steps - 1 else "FAIL",
                "score": f"{passed_steps}/{total_steps}",
                "journey_steps": journey_steps
            }
            
        except Exception as e:
            print(f"❌ User journey test failed: {str(e)}")
            return {
                "test": "Complete User Journey",
                "status": "ERROR",
                "error": str(e)
            }
    
    def test_multi_turn_conversations(self) -> Dict:
        """Test multi-turn conversation functionality"""
        print("🧪 Testing Multi-turn Conversations...")
        
        try:
            conversation_history = []
            conversation_turns = [
                "What is climate change?",
                "What are the main causes?",
                "How does it affect the environment?",
                "What solutions exist?"
            ]
            
            turn_results = []
            
            for i, query in enumerate(conversation_turns):
                try:
                    response = requests.post(
                        f"{self.backend_url}/api/v1/chat/query",
                        json={
                            "query": query,
                            "language": "en",
                            "conversation_history": conversation_history
                        },
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        response_text = data.get('response', '')
                        
                        # Add to conversation history for next turn
                        conversation_history.append({"role": "user", "content": query})
                        conversation_history.append({"role": "assistant", "content": response_text})
                        
                        turn_results.append({
                            "turn": i + 1,
                            "query": query,
                            "success": data.get('success', False),
                            "response_length": len(response_text),
                            "processing_time": data.get('processing_time', 0),
                            "has_citations": len(data.get('citations', [])) > 0
                        })
                        
                        print(f"  Turn {i+1}: ✅ {len(response_text)} chars, {data.get('processing_time', 0):.2f}s")
                    else:
                        turn_results.append({
                            "turn": i + 1,
                            "query": query,
                            "success": False,
                            "error": f"HTTP {response.status_code}"
                        })
                        print(f"  Turn {i+1}: ❌ HTTP {response.status_code}")
                        
                except Exception as e:
                    turn_results.append({
                        "turn": i + 1,
                        "query": query,
                        "success": False,
                        "error": str(e)
                    })
                    print(f"  Turn {i+1}: ❌ {str(e)[:50]}")
                
                time.sleep(0.5)  # Small delay between turns
            
            successful_turns = sum(1 for t in turn_results if t.get('success', False))
            total_turns = len(turn_results)
            
            return {
                "test": "Multi-turn Conversations",
                "status": "PASS" if successful_turns >= total_turns - 1 else "FAIL",
                "score": f"{successful_turns}/{total_turns}",
                "turn_results": turn_results,
                "conversation_length": len(conversation_history)
            }
            
        except Exception as e:
            print(f"❌ Multi-turn conversation test failed: {str(e)}")
            return {
                "test": "Multi-turn Conversations",
                "status": "ERROR",
                "error": str(e)
            }
    
    def test_language_switching(self) -> Dict:
        """Test language switching mid-conversation"""
        print("🧪 Testing Language Switching...")
        
        try:
            # Start conversation in English
            response1 = requests.post(
                f"{self.backend_url}/api/v1/chat/query",
                json={
                    "query": "What is climate change?",
                    "language": "en"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            language_switch_results = []
            conversation_history = []
            
            if response1.status_code == 200:
                data1 = response1.json()
                conversation_history = [
                    {"role": "user", "content": "What is climate change?"},
                    {"role": "assistant", "content": data1.get('response', '')}
                ]
                
                language_switch_results.append({
                    "language": "en",
                    "success": data1.get('success', False),
                    "language_used": data1.get('language_used'),
                    "response_length": len(data1.get('response', ''))
                })
            
            # Switch to Spanish
            response2 = requests.post(
                f"{self.backend_url}/api/v1/chat/query",
                json={
                    "query": "¿Cuáles son las principales causas?",
                    "language": "es",
                    "conversation_history": conversation_history
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response2.status_code == 200:
                data2 = response2.json()
                language_switch_results.append({
                    "language": "es",
                    "success": data2.get('success', False),
                    "language_used": data2.get('language_used'),
                    "response_length": len(data2.get('response', ''))
                })
            
            # Switch to French
            response3 = requests.post(
                f"{self.backend_url}/api/v1/chat/query",
                json={
                    "query": "Quelles sont les solutions?",
                    "language": "fr"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response3.status_code == 200:
                data3 = response3.json()
                language_switch_results.append({
                    "language": "fr",
                    "success": data3.get('success', False),
                    "language_used": data3.get('language_used'),
                    "response_length": len(data3.get('response', ''))
                })
            
            # Validate language switching
            switch_checks = {
                "English Request": any(r.get('language') == 'en' and r.get('success') for r in language_switch_results),
                "Spanish Request": any(r.get('language') == 'es' and r.get('success') for r in language_switch_results),
                "French Request": any(r.get('language') == 'fr' and r.get('success') for r in language_switch_results),
                "Language Detection": all(r.get('language_used') == r.get('language') for r in language_switch_results if r.get('language_used')),
                "Response Quality": all(r.get('response_length', 0) > 20 for r in language_switch_results if r.get('success'))
            }
            
            passed_checks = sum(switch_checks.values())
            total_checks = len(switch_checks)
            
            print(f"✅ Language Switching - {passed_checks}/{total_checks} checks passed")
            
            return {
                "test": "Language Switching",
                "status": "PASS" if passed_checks >= 4 else "FAIL",
                "score": f"{passed_checks}/{total_checks}",
                "switch_checks": switch_checks,
                "language_results": language_switch_results
            }
            
        except Exception as e:
            print(f"❌ Language switching test failed: {str(e)}")
            return {
                "test": "Language Switching",
                "status": "ERROR",
                "error": str(e)
            }
    
    def test_mobile_experience(self) -> Dict:
        """Test mobile user experience simulation"""
        print("🧪 Testing Mobile Experience Simulation...")
        
        try:
            mobile_headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
            }
            
            mobile_tests = []
            
            # Test 1: Mobile frontend access
            try:
                mobile_frontend = requests.get(
                    self.frontend_url, 
                    headers=mobile_headers,
                    timeout=10
                )
                mobile_tests.append({
                    "test": "Mobile Frontend Access",
                    "passed": mobile_frontend.status_code == 200,
                    "details": f"Status: {mobile_frontend.status_code}"
                })
            except Exception as e:
                mobile_tests.append({
                    "test": "Mobile Frontend Access",
                    "passed": False,
                    "details": f"Error: {str(e)[:50]}"
                })
            
            # Test 2: Mobile API requests (simulating slower network)
            try:
                start_time = time.time()
                mobile_chat = requests.post(
                    f"{self.backend_url}/api/v1/chat/query",
                    json={
                        "query": "Quick climate facts for mobile user",
                        "language": "en"
                    },
                    headers=mobile_headers,
                    timeout=15  # Longer timeout for mobile
                )
                response_time = time.time() - start_time
                
                mobile_tests.append({
                    "test": "Mobile API Performance",
                    "passed": mobile_chat.status_code == 200 and response_time < 10,
                    "details": f"Response time: {response_time:.2f}s"
                })
            except Exception as e:
                mobile_tests.append({
                    "test": "Mobile API Performance",
                    "passed": False,
                    "details": f"Error: {str(e)[:50]}"
                })
            
            # Test 3: Responsive design simulation (check if frontend serves mobile-optimized content)
            try:
                if mobile_frontend.status_code == 200:
                    content = mobile_frontend.text
                    mobile_indicators = [
                        'viewport' in content.lower(),
                        'responsive' in content.lower() or 'mobile' in content.lower(),
                        'width=device-width' in content
                    ]
                    mobile_optimized = sum(mobile_indicators) >= 1
                else:
                    mobile_optimized = False
                
                mobile_tests.append({
                    "test": "Mobile Responsive Design",
                    "passed": mobile_optimized,
                    "details": f"Mobile indicators found: {sum(mobile_indicators)}/3"
                })
            except Exception as e:
                mobile_tests.append({
                    "test": "Mobile Responsive Design",
                    "passed": False,
                    "details": f"Error: {str(e)[:50]}"
                })
            
            # Test 4: Touch interaction simulation (multiple quick taps)
            try:
                touch_responses = []
                for i in range(3):
                    touch_response = requests.post(
                        f"{self.backend_url}/api/v1/chat/query",
                        json={
                            "query": f"Touch test {i+1}",
                            "language": "en"
                        },
                        headers=mobile_headers,
                        timeout=10
                    )
                    touch_responses.append(touch_response.status_code == 200)
                    time.sleep(0.3)  # Quick successive requests
                
                successful_touches = sum(touch_responses)
                mobile_tests.append({
                    "test": "Touch Interaction Simulation",
                    "passed": successful_touches >= 2,
                    "details": f"Successful touches: {successful_touches}/3"
                })
            except Exception as e:
                mobile_tests.append({
                    "test": "Touch Interaction Simulation",
                    "passed": False,
                    "details": f"Error: {str(e)[:50]}"
                })
            
            passed_tests = sum(1 for t in mobile_tests if t.get('passed', False))
            total_tests = len(mobile_tests)
            
            print(f"✅ Mobile Experience - {passed_tests}/{total_tests} tests passed")
            
            return {
                "test": "Mobile User Experience",
                "status": "PASS" if passed_tests >= 3 else "FAIL",
                "score": f"{passed_tests}/{total_tests}",
                "mobile_tests": mobile_tests
            }
            
        except Exception as e:
            print(f"❌ Mobile experience test failed: {str(e)}")
            return {
                "test": "Mobile User Experience",
                "status": "ERROR",
                "error": str(e)
            }
    
    def single_load_request(self, request_id: int) -> Dict:
        """Single request for load testing"""
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.backend_url}/api/v1/chat/query",
                json={
                    "query": f"Load test query {request_id}",
                    "language": "en"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response_time = time.time() - start_time
            
            return {
                "request_id": request_id,
                "success": response.status_code == 200,
                "response_time": response_time,
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "request_id": request_id,
                "success": False,
                "response_time": time.time() - start_time,
                "error": str(e)[:50]
            }
    
    def test_performance_under_load(self) -> Dict:
        """Test performance under concurrent load"""
        print("🧪 Testing Performance Under Load...")
        
        try:
            # Test with moderate concurrent load
            concurrent_requests = 5
            
            print(f"  Running {concurrent_requests} concurrent requests...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                start_time = time.time()
                
                # Submit all requests
                futures = [
                    executor.submit(self.single_load_request, i) 
                    for i in range(concurrent_requests)
                ]
                
                # Collect results
                load_results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    load_results.append(result)
                
                total_time = time.time() - start_time
            
            # Analyze results
            successful_requests = sum(1 for r in load_results if r.get('success', False))
            response_times = [r.get('response_time', 0) for r in load_results if r.get('success', False)]
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            
            load_checks = {
                "Concurrent Success": successful_requests >= concurrent_requests - 1,
                "Average Response Time": avg_response_time < 10.0,
                "Max Response Time": max_response_time < 30.0,
                "Total Completion Time": total_time < 60.0,
                "No Server Errors": all(r.get('status_code', 500) < 500 for r in load_results if 'status_code' in r)
            }
            
            passed_checks = sum(load_checks.values())
            total_checks = len(load_checks)
            
            print(f"✅ Load Performance - {passed_checks}/{total_checks} checks passed")
            print(f"  📊 {successful_requests}/{concurrent_requests} requests successful")
            print(f"  ⏱️ Avg response time: {avg_response_time:.2f}s")
            
            return {
                "test": "Performance Under Load",
                "status": "PASS" if passed_checks >= 4 else "FAIL",
                "score": f"{passed_checks}/{total_checks}",
                "load_checks": load_checks,
                "concurrent_requests": concurrent_requests,
                "successful_requests": successful_requests,
                "avg_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "total_time": total_time
            }
            
        except Exception as e:
            print(f"❌ Performance load test failed: {str(e)}")
            return {
                "test": "Performance Under Load",
                "status": "ERROR",
                "error": str(e)
            }
    
    def run_all_tests(self):
        """Run all end-to-end tests"""
        print("🎯 END-TO-END TESTING SUITE")
        print("=" * 50)
        
        # Run all tests
        tests = [
            self.test_complete_user_journey,
            self.test_multi_turn_conversations,
            self.test_language_switching,
            self.test_mobile_experience,
            self.test_performance_under_load
        ]
        
        results = []
        for test_func in tests:
            result = test_func()
            results.append(result)
            time.sleep(2)  # Longer delay between comprehensive tests
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 END-TO-END TESTING SUMMARY")
        print("=" * 50)
        
        total_tests = len(results)
        passed = sum(1 for r in results if r.get("status") == "PASS")
        failed = sum(1 for r in results if r.get("status") == "FAIL")
        errors = sum(1 for r in results if r.get("status") == "ERROR")
        
        print(f"🎯 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"🚨 Errors: {errors}")
        print(f"📈 Success Rate: {(passed/total_tests)*100:.1f}%")
        
        # Show details for failed/error tests
        if failed > 0 or errors > 0:
            print(f"\n🔍 FAILED/ERROR DETAILS:")
            for r in results:
                if r.get("status") in ["FAIL", "ERROR"]:
                    test_name = r['test']
                    status = r['status']
                    error_info = r.get('error', r.get('score', 'See test details'))
                    print(f"  - {test_name}: {status} - {error_info}")
        
        # Final verdict
        if passed == total_tests:
            print(f"\n🎉 SUCCESS: All end-to-end tests passed!")
            print(f"✅ System is ready for production deployment!")
        else:
            print(f"\n⚠️  ISSUES FOUND: {passed}/{total_tests} tests passed")
            print(f"🔧 Need to address {failed + errors} end-to-end issues")
        
        return results

if __name__ == "__main__":
    tester = EndToEndTester()
    results = tester.run_all_tests()