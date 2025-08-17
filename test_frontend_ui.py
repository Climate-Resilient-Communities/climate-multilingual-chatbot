#!/usr/bin/env python3
"""
Frontend UI Testing Suite
=========================

Tests frontend components, responsiveness, and user interface functionality
to validate Section 5.2.1 User Interface Testing requirements.
"""

import json
import time
import requests
from typing import Dict, List

class FrontendUITester:
    def __init__(self):
        self.frontend_url = "http://localhost:9002"
        self.backend_url = "http://localhost:8000"
        self.results = []
        
    def test_frontend_accessibility(self) -> Dict:
        """Test if frontend is accessible and loading"""
        print("🧪 Testing Frontend Accessibility...")
        
        try:
            response = requests.get(self.frontend_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Check for key UI components in HTML
                checks = {
                    "React App": "div id=\"__next\"" in content or "div id=\"root\"" in content,
                    "CSS Styles": "<style" in content or 'rel="stylesheet"' in content,
                    "JavaScript": "<script" in content,
                    "Meta Tags": "<meta" in content,
                    "Title": "<title>" in content,
                    "Responsive Meta": 'name="viewport"' in content
                }
                
                passed_checks = sum(checks.values())
                total_checks = len(checks)
                
                print(f"✅ Frontend Accessible - {passed_checks}/{total_checks} checks passed")
                
                return {
                    "test": "Frontend Accessibility",
                    "status": "PASS" if passed_checks >= 4 else "FAIL",
                    "checks": checks,
                    "score": f"{passed_checks}/{total_checks}",
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                print(f"❌ Frontend not accessible - HTTP {response.status_code}")
                return {
                    "test": "Frontend Accessibility", 
                    "status": "FAIL",
                    "error": f"HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                }
                
        except Exception as e:
            print(f"❌ Frontend accessibility test failed: {str(e)}")
            return {
                "test": "Frontend Accessibility",
                "status": "ERROR",
                "error": str(e),
                "response_time": 0
            }

    def test_api_integration(self) -> Dict:
        """Test frontend-backend API integration"""
        print("🧪 Testing API Integration...")
        
        try:
            # Test supported languages endpoint
            langs_response = requests.get(f"{self.backend_url}/api/v1/languages/supported", timeout=10)
            
            # Test chat test endpoint  
            chat_response = requests.get(f"{self.backend_url}/api/v1/chat/test", timeout=10)
            
            # Check if languages response has the correct structure
            langs_data = langs_response.json() if langs_response.status_code == 200 else {}
            has_languages = (bool(langs_data.get('command_a_languages', [])) and 
                           bool(langs_data.get('nova_languages', [])))
            
            api_checks = {
                "Languages Endpoint": langs_response.status_code == 200,
                "Chat Test Endpoint": chat_response.status_code == 200,
                "Languages Data": has_languages,
                "Chat Status": chat_response.status_code == 200 and 'status' in chat_response.json()
            }
            
            passed_checks = sum(api_checks.values())
            total_checks = len(api_checks)
            
            print(f"✅ API Integration - {passed_checks}/{total_checks} endpoints working")
            
            return {
                "test": "API Integration",
                "status": "PASS" if passed_checks == total_checks else "FAIL",
                "checks": api_checks,
                "score": f"{passed_checks}/{total_checks}",
                "languages_count": langs_data.get('total_supported', 0)
            }
            
        except Exception as e:
            print(f"❌ API integration test failed: {str(e)}")
            return {
                "test": "API Integration",
                "status": "ERROR", 
                "error": str(e)
            }

    def test_chat_functionality(self) -> Dict:
        """Test basic chat functionality through API"""
        print("🧪 Testing Chat Functionality...")
        
        try:
            # Test a simple query
            chat_request = {
                "query": "What is climate change?",
                "language": "en"
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.backend_url}/api/v1/chat/query",
                json=chat_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                functionality_checks = {
                    "Query Processing": data.get('success', False),
                    "Response Generated": len(data.get('response', '')) > 10,
                    "Language Detection": data.get('language_used') == 'en',
                    "Citations Provided": len(data.get('citations', [])) > 0,
                    "Processing Time": response_time < 10.0,
                    "Model Selection": data.get('model_used') in ['command_a', 'nova', 'unknown']
                }
                
                passed_checks = sum(functionality_checks.values()) 
                total_checks = len(functionality_checks)
                
                print(f"✅ Chat Functionality - {passed_checks}/{total_checks} features working")
                print(f"⏱️ Response time: {response_time:.2f}s")
                
                return {
                    "test": "Chat Functionality",
                    "status": "PASS" if passed_checks >= 4 else "FAIL",
                    "checks": functionality_checks,
                    "score": f"{passed_checks}/{total_checks}",
                    "response_time": response_time,
                    "response_length": len(data.get('response', '')),
                    "citations_count": len(data.get('citations', [])),
                    "model_used": data.get('model_used', 'unknown')
                }
            else:
                print(f"❌ Chat functionality failed - HTTP {response.status_code}")
                return {
                    "test": "Chat Functionality",
                    "status": "FAIL",
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "response_time": response_time
                }
                
        except Exception as e:
            print(f"❌ Chat functionality test failed: {str(e)}")
            return {
                "test": "Chat Functionality", 
                "status": "ERROR",
                "error": str(e)
            }

    def test_language_selection(self) -> Dict:
        """Test language selection functionality"""
        print("🧪 Testing Language Selection...")
        
        try:
            # Test multiple languages
            test_languages = [
                {"code": "en", "query": "What is climate change?"},
                {"code": "es", "query": "¿Qué es el cambio climático?"},
                {"code": "fr", "query": "Qu'est-ce que le changement climatique?"}
            ]
            
            language_results = []
            
            for lang_test in test_languages:
                chat_request = {
                    "query": lang_test["query"],
                    "language": lang_test["code"]
                }
                
                response = requests.post(
                    f"{self.backend_url}/api/v1/chat/query",
                    json=chat_request,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = {
                        "language": lang_test["code"],
                        "success": data.get('success', False),
                        "language_correct": data.get('language_used') == lang_test["code"],
                        "model_used": data.get('model_used', 'unknown')
                    }
                    language_results.append(result)
                    print(f"  📝 {lang_test['code']}: {'✅ PASS' if result['success'] and result['language_correct'] else '❌ FAIL'}")
                
                time.sleep(0.5)  # Small delay between requests
            
            successful_languages = sum(1 for r in language_results if r['success'] and r['language_correct'])
            total_languages = len(language_results)
            
            return {
                "test": "Language Selection",
                "status": "PASS" if successful_languages == total_languages else "FAIL",
                "successful_languages": successful_languages,
                "total_languages": total_languages,
                "score": f"{successful_languages}/{total_languages}",
                "language_results": language_results
            }
            
        except Exception as e:
            print(f"❌ Language selection test failed: {str(e)}")
            return {
                "test": "Language Selection",
                "status": "ERROR",
                "error": str(e)
            }

    def test_error_handling(self) -> Dict:
        """Test error handling and edge cases"""
        print("🧪 Testing Error Handling...")
        
        try:
            error_tests = []
            
            # Test 1: Empty query
            response1 = requests.post(
                f"{self.backend_url}/api/v1/chat/query",
                json={"query": "", "language": "en"},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            error_tests.append({
                "test": "Empty Query",
                "handled_correctly": response1.status_code == 422  # Validation error expected
            })
            
            # Test 2: Invalid language code
            response2 = requests.post(
                f"{self.backend_url}/api/v1/chat/query", 
                json={"query": "Test", "language": "invalid"},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            error_tests.append({
                "test": "Invalid Language",
                "handled_correctly": response2.status_code in [200, 400, 422]  # Should handle gracefully
            })
            
            # Test 3: Malformed request
            response3 = requests.post(
                f"{self.backend_url}/api/v1/chat/query",
                data="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            error_tests.append({
                "test": "Malformed Request",
                "handled_correctly": response3.status_code == 422  # JSON parse error expected
            })
            
            handled_correctly = sum(1 for test in error_tests if test['handled_correctly'])
            total_tests = len(error_tests)
            
            print(f"✅ Error Handling - {handled_correctly}/{total_tests} cases handled correctly")
            
            return {
                "test": "Error Handling",
                "status": "PASS" if handled_correctly >= 2 else "FAIL",
                "score": f"{handled_correctly}/{total_tests}",
                "error_tests": error_tests
            }
            
        except Exception as e:
            print(f"❌ Error handling test failed: {str(e)}")
            return {
                "test": "Error Handling",
                "status": "ERROR",
                "error": str(e)
            }

    def run_all_tests(self):
        """Run all frontend UI tests"""
        print("🔧 FRONTEND UI TESTING SUITE")
        print("=" * 50)
        
        # Run all tests
        tests = [
            self.test_frontend_accessibility,
            self.test_api_integration, 
            self.test_chat_functionality,
            self.test_language_selection,
            self.test_error_handling
        ]
        
        results = []
        for test_func in tests:
            result = test_func()
            results.append(result)
            time.sleep(1)  # Small delay between tests
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 UI TESTING SUMMARY")
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
                    error_info = r.get('error', 'See individual test results')
                    print(f"  - {test_name}: {status} - {error_info}")
        
        # Final verdict
        if passed == total_tests:
            print(f"\n🎉 SUCCESS: All frontend UI tests passed!")
            print(f"✅ Frontend is ready for production!")
        else:
            print(f"\n⚠️  ISSUES FOUND: {passed}/{total_tests} tests passed")
            print(f"🔧 Need to address {failed + errors} issues")
        
        return results

if __name__ == "__main__":
    tester = FrontendUITester()
    results = tester.run_all_tests()