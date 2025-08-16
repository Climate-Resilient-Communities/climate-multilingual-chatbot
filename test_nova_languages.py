#!/usr/bin/env python3
"""
Focused Nova Language Testing Script
Tests only the 15 Nova languages that were failing with rate limits
"""

import requests
import json
import time
from typing import Dict, List, Tuple

class NovaLanguageTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
        # Nova languages that support climate questions
        self.nova_languages = [
            ("en", "What is climate change?"),
            ("es", "¿Qué es el cambio climático?"),
            ("ja", "気候変動とは何ですか？"),
            ("de", "Was ist der Klimawandel?"),
            ("sv", "Vad är klimatförändringar?"),
            ("da", "Hvad er klimaændringer?"),
            ("no", "Hva er klimaendringer?"),
            ("fi", "Mitä on ilmastonmuutos?"),
            ("it", "Cos'è il cambiamento climatico?"),
            ("pt", "O que é mudança climática?"),
            ("hu", "Mi a klímaváltozás?"),
            ("sk", "Čo je zmena klímy?"),
            ("sl", "Kaj je podnebna sprememba?"),
            ("bg", "Какво е изменението на климата?"),
            ("hr", "Što je promjena klime?")
        ]
    
    def test_single_language(self, lang_code: str, query: str) -> Dict:
        """Test a single language and return result"""
        print(f"🧪 Testing: {lang_code.upper()}")
        print(f"📝 Query: {query}")
        print(f"🎯 Expected Model: nova")
        
        payload = {
            "query": query,
            "language": lang_code,
            "conversation_history": []
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/chat/query",
                json=payload,
                timeout=60  # Give plenty of time for Nova
            )
            
            if response.status_code == 200:
                data = response.json()
                model_used = data.get('model_used', 'unknown')
                response_text = data.get('response', '')
                
                if model_used == 'nova':
                    print(f"✅ PASS - Language: {lang_code}, Model: {model_used}, Response: {len(response_text)} chars")
                    return {"status": "pass", "model": model_used, "response_len": len(response_text)}
                else:
                    print(f"❌ WRONG MODEL - Expected: nova, Got: {model_used}")
                    return {"status": "wrong_model", "model": model_used, "expected": "nova"}
            
            elif response.status_code == 429:
                error_data = response.json()
                print(f"🚨 RATE LIMITED - {error_data}")
                return {"status": "rate_limited", "error": error_data}
            
            else:
                print(f"❌ HTTP ERROR {response.status_code}: {response.text}")
                return {"status": "http_error", "code": response.status_code, "error": response.text}
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
            return {"status": "exception", "error": str(e)}
    
    def run_nova_tests(self) -> Dict:
        """Run all Nova language tests with proper pacing"""
        print("🚀 NOVA LANGUAGE FOCUSED TEST")
        print("=" * 50)
        print(f"📋 Testing {len(self.nova_languages)} Nova Languages...")
        print()
        
        results = {
            "passed": [],
            "failed": [],
            "errors": [],
            "wrong_model": []
        }
        
        for i, (lang_code, query) in enumerate(self.nova_languages):
            result = self.test_single_language(lang_code, query)
            
            if result["status"] == "pass":
                results["passed"].append((lang_code, result))
            elif result["status"] == "wrong_model":
                results["wrong_model"].append((lang_code, result))
            elif result["status"] in ["rate_limited", "http_error"]:
                results["failed"].append((lang_code, result))
            else:
                results["errors"].append((lang_code, result))
            
            print()
            
            # Pace requests to respect rate limits (60 rpm = 1 per second)
            if i < len(self.nova_languages) - 1:
                time.sleep(1.2)  # Slightly more than 1 second to be safe
        
        # Print summary
        self.print_summary(results)
        return results
    
    def print_summary(self, results: Dict):
        """Print test summary"""
        total = len(self.nova_languages)
        passed = len(results["passed"])
        wrong_model = len(results["wrong_model"])
        failed = len(results["failed"])
        errors = len(results["errors"])
        
        print("=" * 50)
        print("📊 NOVA TEST SUMMARY")
        print("=" * 50)
        print(f"🎯 Total Nova Languages: {total}")
        print(f"✅ Passed (correct model): {passed}")
        print(f"⚠️  Wrong Model: {wrong_model}")
        print(f"❌ Failed (HTTP/Rate): {failed}")
        print(f"🚨 Errors: {errors}")
        print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        print()
        
        if wrong_model > 0:
            print("🔍 WRONG MODEL DETAILS:")
            for lang, result in results["wrong_model"]:
                print(f"  - {lang}: Expected nova, got {result['model']}")
            print()
        
        if failed > 0:
            print("🔍 FAILED DETAILS:")
            for lang, result in results["failed"]:
                if result["status"] == "rate_limited":
                    print(f"  - {lang}: Rate limited")
                else:
                    print(f"  - {lang}: HTTP {result.get('code', 'unknown')}")
            print()
        
        if errors > 0:
            print("🔍 ERROR DETAILS:")
            for lang, result in results["errors"]:
                print(f"  - {lang}: {result['error'][:100]}...")


if __name__ == "__main__":
    tester = NovaLanguageTester()
    results = tester.run_nova_tests()
    
    # Exit code based on results
    if len(results["passed"]) == len(tester.nova_languages):
        print("🎉 ALL NOVA LANGUAGES WORKING!")
        exit(0)
    else:
        print("⚠️  Some Nova languages need attention")
        exit(1)
