#!/usr/bin/env python3
"""
Comprehensive Language Routing Test
==================================

Tests all 22 Command A languages and top 15 Nova languages via API endpoints
to validate 100% language routing functionality.
"""

import requests
import json
import time
from typing import List, Dict, Any

class ComprehensiveLangaugeTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = []
        
        # 22 Languages for Command A (from test file)
        self.command_a_languages = [
            {'code': 'ar', 'name': 'arabic', 'query': 'ما هو تغير المناخ؟'},
            {'code': 'bn', 'name': 'bengali', 'query': 'জলবায়ু পরিবর্তন কি?'},
            {'code': 'zh', 'name': 'chinese', 'query': '什么是气候变化？'},
            {'code': 'tl', 'name': 'filipino', 'query': 'Ano ang climate change?'},
            {'code': 'fr', 'name': 'french', 'query': "Qu'est-ce que le changement climatique?"},
            {'code': 'gu', 'name': 'gujarati', 'query': 'આબોહવા પરિવર્તન શું છે?'},
            {'code': 'ko', 'name': 'korean', 'query': '기후 변화란 무엇인가요?'},
            {'code': 'fa', 'name': 'persian', 'query': 'تغییرات آب و هوایی چیست؟'},
            {'code': 'ru', 'name': 'russian', 'query': 'Что такое изменение климата?'},
            {'code': 'ta', 'name': 'tamil', 'query': 'காலநிலை மாற்றம் என்றால் என்ன?'},
            {'code': 'ur', 'name': 'urdu', 'query': 'موسمیاتی تبدیلی کیا ہے؟'},
            {'code': 'vi', 'name': 'vietnamese', 'query': 'Biến đổi khí hậu là gì?'},
            {'code': 'pl', 'name': 'polish', 'query': 'Co to jest zmiana klimatu?'},
            {'code': 'tr', 'name': 'turkish', 'query': 'İklim değişikliği nedir?'},
            {'code': 'nl', 'name': 'dutch', 'query': 'Wat is klimaatverandering?'},
            {'code': 'cs', 'name': 'czech', 'query': 'Co je změna klimatu?'},
            {'code': 'id', 'name': 'indonesian', 'query': 'Apa itu perubahan iklim?'},
            {'code': 'uk', 'name': 'ukrainian', 'query': 'Що таке зміна клімату?'},
            {'code': 'ro', 'name': 'romanian', 'query': 'Ce este schimbarea climatică?'},
            {'code': 'el', 'name': 'greek', 'query': 'Τι είναι η κλιματική αλλαγή;'},
            {'code': 'hi', 'name': 'hindi', 'query': 'जलवायु परिवर्तन क्या है?'},
            {'code': 'he', 'name': 'hebrew', 'query': 'מה זה שינוי אקלים?'},
        ]
        
        # Top 15 Languages for Nova (most common/important)
        self.nova_languages = [
            {'code': 'en', 'name': 'english', 'query': 'What is climate change?'},
            {'code': 'es', 'name': 'spanish', 'query': '¿Qué es el cambio climático?'},
            {'code': 'ja', 'name': 'japanese', 'query': '気候変動とは何ですか？'},
            {'code': 'de', 'name': 'german', 'query': 'Was ist der Klimawandel?'},
            {'code': 'sv', 'name': 'swedish', 'query': 'Vad är klimatförändringar?'},
            {'code': 'da', 'name': 'danish', 'query': 'Hvad er klimaændringer?'},
            {'code': 'no', 'name': 'norwegian', 'query': 'Hva er klimaendringer?'},
            {'code': 'fi', 'name': 'finnish', 'query': 'Mitä on ilmastonmuutos?'},
            {'code': 'it', 'name': 'italian', 'query': "Cos'è il cambiamento climatico?"},
            {'code': 'pt', 'name': 'portuguese', 'query': 'O que é mudança climática?'},
            {'code': 'hu', 'name': 'hungarian', 'query': 'Mi a klímaváltozás?'},
            {'code': 'sk', 'name': 'slovak', 'query': 'Čo je zmena klímy?'},
            {'code': 'sl', 'name': 'slovenian', 'query': 'Kaj je podnebna sprememba?'},
            {'code': 'bg', 'name': 'bulgarian', 'query': 'Какво е изменението на климата?'},
            {'code': 'hr', 'name': 'croatian', 'query': 'Što je promjena klime?'},
        ]

    def test_language(self, lang_config: Dict[str, str], expected_model: str) -> Dict[str, Any]:
        """Test a single language via API endpoint"""
        print(f"\n🧪 Testing: {lang_config['name'].title()} ({lang_config['code']})")
        print(f"📝 Query: {lang_config['query']}")
        print(f"🎯 Expected Model: {expected_model}")
        
        start_time = time.time()
        
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/api/v1/chat/query",
                json={
                    "query": lang_config['query'],
                    "language": lang_config['code']
                },
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                language_used = data.get('language_used', 'unknown')
                model_used = data.get('model_used', 'unknown')
                response_text = data.get('response', '')
                citations_count = len(data.get('citations', []))
                
                # Validate results
                language_correct = language_used == lang_config['code']
                model_correct = model_used == expected_model
                has_response = len(response_text) > 50  # Meaningful response length
                
                status = "PASS" if (success and language_correct and model_correct and has_response) else "FAIL"
                
                if status == "PASS":
                    print(f"✅ PASS - Language: {language_used}, Model: {model_used}, Response: {len(response_text)} chars")
                else:
                    print(f"❌ FAIL - Success: {success}, Lang: {language_used} (exp: {lang_config['code']}), Model: {model_used} (exp: {expected_model})")
                
                return {
                    "language_code": lang_config['code'],
                    "language_name": lang_config['name'],
                    "expected_model": expected_model,
                    "status": status,
                    "success": success,
                    "language_correct": language_correct,
                    "model_correct": model_correct,
                    "language_used": language_used,
                    "model_used": model_used,
                    "response_length": len(response_text),
                    "citations_count": citations_count,
                    "processing_time": processing_time
                }
            else:
                print(f"❌ HTTP ERROR {response.status_code}: {response.text}")
                return {
                    "language_code": lang_config['code'],
                    "language_name": lang_config['name'],
                    "expected_model": expected_model,
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}",
                    "processing_time": processing_time
                }
                
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ EXCEPTION: {str(e)}")
            return {
                "language_code": lang_config['code'],
                "language_name": lang_config['name'],
                "expected_model": expected_model,
                "status": "ERROR", 
                "error": str(e),
                "processing_time": processing_time
            }

    def run_all_tests(self):
        """Run comprehensive test of all languages"""
        print("🌍 COMPREHENSIVE LANGUAGE ROUTING TEST")
        print("=" * 50)
        
        results = []
        
        print(f"\n📋 Testing {len(self.command_a_languages)} Command A Languages...")
        for lang in self.command_a_languages:
            result = self.test_language(lang, "command_a")
            results.append(result)
            time.sleep(0.5)  # Small delay to avoid overwhelming the API
        
        print(f"\n📋 Testing {len(self.nova_languages)} Nova Languages...")
        for lang in self.nova_languages:
            result = self.test_language(lang, "nova")
            results.append(result)
            time.sleep(0.5)  # Small delay to avoid overwhelming the API
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
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
        
        # Show failed/error details
        if failed > 0 or errors > 0:
            print(f"\n🔍 FAILED/ERROR DETAILS:")
            for r in results:
                if r.get("status") in ["FAIL", "ERROR"]:
                    lang_name = r['language_name'].title()
                    status = r['status']
                    error_info = r.get('error', 'Unknown error')
                    print(f"  - {lang_name} ({r['language_code']}): {status} - {error_info}")
        
        # Command A vs Nova breakdown
        command_a_results = [r for r in results if r.get("expected_model") == "command_a"]
        nova_results = [r for r in results if r.get("expected_model") == "nova"]
        
        command_a_passed = sum(1 for r in command_a_results if r.get("status") == "PASS")
        nova_passed = sum(1 for r in nova_results if r.get("status") == "PASS")
        
        print(f"\n📊 MODEL BREAKDOWN:")
        print(f"🤖 Command A: {command_a_passed}/{len(command_a_results)} ({(command_a_passed/len(command_a_results)*100):.1f}%)")
        print(f"🚀 Nova: {nova_passed}/{len(nova_results)} ({(nova_passed/len(nova_results)*100):.1f}%)")
        
        # Final verdict
        if passed == total_tests:
            print(f"\n🎉 SUCCESS: 100% language routing achieved!")
            print(f"✅ All {total_tests} languages working perfectly!")
        else:
            print(f"\n⚠️  INCOMPLETE: {passed}/{total_tests} languages working")
            print(f"🔧 Need to fix {failed + errors} language routing issues")
        
        return results

if __name__ == "__main__":
    tester = ComprehensiveLangaugeTest()
    results = tester.run_all_tests()