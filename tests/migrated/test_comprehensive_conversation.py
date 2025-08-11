#!/usr/bin/env python3
"""
Comprehensive test script for conversation history language detection.
Tests various multilingual conversation scenarios to ensure proper language mismatch detection.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.query_rewriter import query_rewriter
from src.models.nova_flow import BedrockModel
from src.models.conversation_parser import conversation_parser


class ConversationTestSuite:
    """Test suite for multilingual conversation scenarios."""
    
    def __init__(self):
        self.nova_model = None
        self.test_results = []
        
    async def initialize(self):
        """Initialize the BedrockModel."""
        try:
            self.nova_model = BedrockModel()
            print("✅ BedrockModel initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize BedrockModel: {e}")
            return False
        return True
    
    def create_conversation_scenario(
        self, 
        scenario_name: str,
        messages: List[Dict[str, str]], 
        current_query: str, 
        selected_language: str,
        expected_detected_lang: str,
        expected_language_match: str,
        description: str
    ) -> Dict[str, Any]:
        """Create a test scenario."""
        return {
            'scenario_name': scenario_name,
            'messages': messages,
            'current_query': current_query,
            'selected_language': selected_language,
            'expected_detected_lang': expected_detected_lang,
            'expected_language_match': expected_language_match,
            'description': description
        }
    
    def get_test_scenarios(self) -> List[Dict[str, Any]]:
        """Define all test scenarios."""
        scenarios = []
        
        # Scenario 1: Spanish conversation → English query (should detect mismatch)
        scenarios.append(self.create_conversation_scenario(
            "Spanish→English Mismatch",
            [
                {"role": "user", "content": "¿Qué es el cambio climático?"},
                {"role": "assistant", "content": "El cambio climático es el calentamiento global causado por actividades humanas."},
                {"role": "user", "content": "¿Qué puedo hacer para ayudar?"},
                {"role": "assistant", "content": "Puedes reducir tu huella de carbono usando transporte público."}
            ],
            "What else can I do to help?",
            "es",  # Selected Spanish
            "en",  # Should detect English
            "no",  # Should be mismatch
            "2 Spanish messages + 1 English query (Spanish selected)"
        ))
        
        # Scenario 2: English conversation → Spanish query (should detect mismatch)
        scenarios.append(self.create_conversation_scenario(
            "English→Spanish Mismatch",
            [
                {"role": "user", "content": "What is climate change?"},
                {"role": "assistant", "content": "Climate change refers to global warming caused by human activities."},
                {"role": "user", "content": "How can I help?"},
                {"role": "assistant", "content": "You can reduce your carbon footprint by using public transport."}
            ],
            "¿Qué más puedo hacer?",
            "en",  # Selected English
            "es",  # Should detect Spanish
            "no",  # Should be mismatch
            "2 English messages + 1 Spanish query (English selected)"
        ))
        
        # Scenario 3: Filipino conversation → English query (should detect mismatch)
        scenarios.append(self.create_conversation_scenario(
            "Filipino→English Mismatch",
            [
                {"role": "user", "content": "Ano ang climate change?"},
                {"role": "assistant", "content": "Ang climate change ay ang pag-init ng mundo dahil sa mga gawain ng tao."},
                {"role": "user", "content": "Paano ako makakatulong?"},
                {"role": "assistant", "content": "Maaari kang gumamit ng public transport upang mabawasan ang carbon footprint mo."}
            ],
            "What groups can I join to make a difference?",
            "tl",  # Selected Filipino
            "en",  # Should detect English
            "no",  # Should be mismatch
            "2 Filipino messages + 1 English query (Filipino selected)"
        ))
        
        # Scenario 4: English conversation → English query (should match)
        scenarios.append(self.create_conversation_scenario(
            "English→English Match",
            [
                {"role": "user", "content": "How is Rexdale fighting climate change?"},
                {"role": "assistant", "content": "Rexdale is implementing green roofs and promoting electric vehicles."}
            ],
            "What else are they doing?",
            "en",  # Selected English
            "en",  # Should detect English
            "yes", # Should match
            "2 English messages + 1 English query (English selected)"
        ))
        
        # Scenario 5: Spanish conversation → Spanish query (should match)
        scenarios.append(self.create_conversation_scenario(
            "Spanish→Spanish Match",
            [
                {"role": "user", "content": "¿Cómo lucha Rexdale contra el cambio climático?"},
                {"role": "assistant", "content": "Rexdale está implementando techos verdes y promoviendo vehículos eléctricos."}
            ],
            "¿Qué más están haciendo?",
            "es",  # Selected Spanish
            "es",  # Should detect Spanish
            "yes", # Should match
            "2 Spanish messages + 1 Spanish query (Spanish selected)"
        ))
        
        # Scenario 6: Mixed languages → English query with English selected (should match)
        scenarios.append(self.create_conversation_scenario(
            "Mixed→English Match",
            [
                {"role": "user", "content": "¿Qué es el cambio climático?"},
                {"role": "assistant", "content": "Climate change refers to global warming."},
                {"role": "user", "content": "Salamat sa explanation!"},
                {"role": "assistant", "content": "You're welcome! Happy to help."}
            ],
            "Can you tell me more about renewable energy?",
            "en",  # Selected English
            "en",  # Should detect English
            "yes", # Should match
            "Mixed language history + 1 English query (English selected)"
        ))
        
        # Scenario 7: Long Spanish conversation → English query (should detect mismatch)
        scenarios.append(self.create_conversation_scenario(
            "Long Spanish→English Mismatch",
            [
                {"role": "user", "content": "¿Cuáles son las principales causas del cambio climático?"},
                {"role": "assistant", "content": "Las principales causas incluyen la quema de combustibles fósiles."},
                {"role": "user", "content": "¿Cómo afecta esto a los océanos?"},
                {"role": "assistant", "content": "Los océanos se acidifican y se calientan, afectando la vida marina."},
                {"role": "user", "content": "¿Qué podemos hacer para detenerlo?"},
                {"role": "assistant", "content": "Podemos usar energías renovables y reducir nuestro consumo."}
            ],
            "How do renewable energies actually work?",
            "es",  # Selected Spanish
            "en",  # Should detect English
            "no",  # Should be mismatch
            "3 Spanish exchanges + 1 English query (Spanish selected)"
        ))
        
        # Scenario 8: French conversation → English query (should detect mismatch)
        scenarios.append(self.create_conversation_scenario(
            "French→English Mismatch",
            [
                {"role": "user", "content": "Qu'est-ce que le changement climatique?"},
                {"role": "assistant", "content": "Le changement climatique est le réchauffement planétaire causé par les activités humaines."}
            ],
            "What can I do to help?",
            "fr",  # Selected French
            "en",  # Should detect English
            "no",  # Should be mismatch
            "1 French exchange + 1 English query (French selected)"
        ))
        
        # Scenario 9: No conversation history → English query (should match)
        scenarios.append(self.create_conversation_scenario(
            "No History→English Match",
            [],  # Empty history
            "What is climate change?",
            "en",  # Selected English
            "en",  # Should detect English
            "yes", # Should match
            "No history + 1 English query (English selected)"
        ))
        
        # Scenario 10: Portuguese conversation → Spanish query (should detect mismatch)
        scenarios.append(self.create_conversation_scenario(
            "Portuguese→Spanish Mismatch",
            [
                {"role": "user", "content": "O que é mudança climática?"},
                {"role": "assistant", "content": "Mudança climática é o aquecimento global causado por atividades humanas."}
            ],
            "¿Qué más puedo aprender sobre esto?",
            "pt",  # Selected Portuguese
            "es",  # Should detect Spanish
            "no",  # Should be mismatch
            "1 Portuguese exchange + 1 Spanish query (Portuguese selected)"
        ))
        
        return scenarios
    
    async def run_single_test(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario."""
        print(f"\n🧪 Testing: {scenario['scenario_name']}")
        print(f"📋 Description: {scenario['description']}")
        
        # Format conversation history
        formatted_history = conversation_parser.format_for_query_rewriter(scenario['messages'])
        
        print(f"📝 Conversation History ({len(formatted_history)} messages):")
        for i, msg in enumerate(formatted_history, 1):
            content_preview = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
            print(f"   Message {i} ({msg['role']}): {content_preview}")
        
        print(f"🎯 Current Query (Message {len(formatted_history) + 1}): '{scenario['current_query']}'")
        print(f"🌐 Selected Language: {scenario['selected_language']}")
        print(f"🎯 Expected: detected_lang='{scenario['expected_detected_lang']}', match='{scenario['expected_language_match']}'")
        
        try:
            # Run query rewriter
            result = await query_rewriter(
                conversation_history=formatted_history,
                user_query=scenario['current_query'],
                nova_model=self.nova_model,
                selected_language_code=scenario['selected_language']
            )
            
            print(f"\n📊 Query Rewriter Result:")
            print("-" * 50)
            print(result)
            print("-" * 50)
            
            # Parse results (expecting JSON format)
            import json
            try:
                parsed_result = json.loads(result)
                detected_lang = parsed_result.get('language', 'unknown').lower()
                language_match = 'yes' if parsed_result.get('language_match', False) else 'no'
                classification = parsed_result.get('classification', 'unknown').lower()
            except (json.JSONDecodeError, AttributeError):
                # Fallback to regex parsing for legacy format
                import re
                lang_match = re.search(r"Language:\s*([a-z]{2}|unknown)", result, re.IGNORECASE)
                match_match = re.search(r"LanguageMatch:\s*(yes|no)", result, re.IGNORECASE)
                cls_match = re.search(r"Classification:\s*(on-topic|off-topic|harmful)", result, re.IGNORECASE)
                
                detected_lang = lang_match.group(1).lower() if lang_match else 'unknown'
                language_match = match_match.group(1).lower() if match_match else 'unknown'
                classification = cls_match.group(1).lower() if cls_match else 'unknown'
            
            print(f"\n📈 Parsed Results:")
            print(f"   Detected Language: {detected_lang}")
            print(f"   Language Match: {language_match}")
            print(f"   Classification: {classification}")
            
            # Check if test passed
            expected_detected = scenario['expected_detected_lang']
            expected_match = scenario['expected_language_match']
            
            lang_correct = detected_lang == expected_detected
            match_correct = language_match == expected_match
            test_passed = lang_correct and match_correct
            
            if test_passed:
                print(f"\n🎉 ✅ TEST PASSED!")
                print(f"   ✓ Language detection: {detected_lang} (expected {expected_detected})")
                print(f"   ✓ Language match: {language_match} (expected {expected_match})")
            else:
                print(f"\n❌ TEST FAILED!")
                print(f"   Language detection: {detected_lang} (expected {expected_detected}) {'✓' if lang_correct else '✗'}")
                print(f"   Language match: {language_match} (expected {expected_match}) {'✓' if match_correct else '✗'}")
            
            return {
                'scenario_name': scenario['scenario_name'],
                'passed': test_passed,
                'detected_lang': detected_lang,
                'expected_detected_lang': expected_detected,
                'language_match': language_match,
                'expected_language_match': expected_match,
                'classification': classification,
                'raw_result': result
            }
            
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                'scenario_name': scenario['scenario_name'],
                'passed': False,
                'error': str(e)
            }
    
    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all test scenarios."""
        print("🚀 Starting Comprehensive Conversation History Language Detection Tests")
        print("=" * 80)
        
        if not await self.initialize():
            return []
        
        scenarios = self.get_test_scenarios()
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'='*20} TEST {i}/{len(scenarios)} {'='*20}")
            result = await self.run_single_test(scenario)
            results.append(result)
            
            # Brief pause between tests
            await asyncio.sleep(0.5)
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print test summary."""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in results if r.get('passed', False))
        total = len(results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        print(f"\n📋 Detailed Results:")
        for i, result in enumerate(results, 1):
            status = "✅ PASS" if result.get('passed', False) else "❌ FAIL"
            print(f"{i:2d}. {result['scenario_name']:25s} - {status}")
            if not result.get('passed', False) and 'error' not in result:
                expected_lang = result.get('expected_detected_lang', '?')
                actual_lang = result.get('detected_lang', '?')
                expected_match = result.get('expected_language_match', '?')
                actual_match = result.get('language_match', '?')
                print(f"    Expected: lang={expected_lang}, match={expected_match}")
                print(f"    Actual:   lang={actual_lang}, match={actual_match}")
        
        if passed == total:
            print(f"\n🎉 ALL TESTS PASSED! The conversation history language detection is working perfectly!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Review the issues above.")


async def main():
    """Run the comprehensive test suite."""
    test_suite = ConversationTestSuite()
    results = await test_suite.run_all_tests()
    test_suite.print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
