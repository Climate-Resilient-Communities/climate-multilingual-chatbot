#!/usr/bin/env python3
"""
Test script for follow-up detection functionality.
This tests the enhanced follow-up detection logic.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.input_guardrail import check_follow_up_with_llm, _fallback_follow_up_check

async def test_follow_up_detection():
    """Test the follow-up detection functionality."""
    
    print("🚀 Testing Enhanced Follow-up Detection")
    print("=" * 50)
    
    # Test cases with conversation history
    test_scenarios = [
        {
            "name": "Climate Change Basic Follow-up",
            "conversation_history": [
                {
                    "query": "what is climate change",
                    "response": "Climate change refers to significant and lasting changes in the Earth's climate. This includes shifts in temperature and weather patterns over a long period. Human activities, especially burning fossil fuels like coal, oil, and gas, are the main drivers of climate change."
                }
            ],
            "new_query": "why is it important?",
            "expected": True,
            "reason": "Asking about importance of previously discussed topic"
        },
        {
            "name": "Strategic Decision Follow-up (off-topic)",
            "conversation_history": [
                {
                    "query": "what is climate change",
                    "response": "Climate change refers to significant and lasting changes in the Earth's climate..."
                }
            ],
            "new_query": "why is strategic decision making important?",
            "expected": False,
            "reason": "New topic about business strategy, not related to climate"
        },
        {
            "name": "Direct Why Question",
            "conversation_history": [
                {
                    "query": "Tell me about ocean acidification",
                    "response": "Ocean acidification occurs when seawater absorbs carbon dioxide from the atmosphere, making it more acidic."
                }
            ],
            "new_query": "why?",
            "expected": True,
            "reason": "Direct follow-up asking for explanation"
        },
        {
            "name": "How Question Follow-up",
            "conversation_history": [
                {
                    "query": "What are greenhouse gases?",
                    "response": "Greenhouse gases are gases that trap heat in the atmosphere, including CO2, methane, and water vapor."
                }
            ],
            "new_query": "how do they trap heat?",
            "expected": True,
            "reason": "Follow-up asking for mechanism explanation"
        },
        {
            "name": "New Topic Introduction",
            "conversation_history": [
                {
                    "query": "What is global warming?",
                    "response": "Global warming is the increase in Earth's average surface temperature due to greenhouse gas emissions."
                }
            ],
            "new_query": "What is photosynthesis?",
            "expected": False,
            "reason": "Completely new scientific topic"
        },
        {
            "name": "Elaboration Request",
            "conversation_history": [
                {
                    "query": "How does deforestation affect climate?",
                    "response": "Deforestation reduces the number of trees that can absorb CO2, leading to higher atmospheric CO2 levels."
                }
            ],
            "new_query": "can you elaborate on that?",
            "expected": True,
            "reason": "Explicit request for more detail"
        },
        {
            "name": "Multiple Turn Context",
            "conversation_history": [
                {
                    "query": "What is renewable energy?",
                    "response": "Renewable energy comes from sources that naturally replenish, like solar, wind, and hydro power."
                },
                {
                    "query": "How does it help with climate change?",
                    "response": "Renewable energy reduces greenhouse gas emissions by replacing fossil fuel power generation."
                }
            ],
            "new_query": "what are the main types?",
            "expected": True,
            "reason": "Follow-up about types of renewable energy"
        }
    ]
    
    print("Testing heuristic-based follow-up detection:")
    print("-" * 50)
    
    heuristic_results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        name = scenario["name"]
        query = scenario["new_query"]
        expected = scenario["expected"]
        reason = scenario["reason"]
        
        print(f"\n{i}. {name}")
        print(f"   New query: '{query}'")
        print(f"   Expected: {'FOLLOW-UP' if expected else 'NEW TOPIC'}")
        print(f"   Reason: {reason}")
        
        # Test heuristic method
        heuristic_result = _fallback_follow_up_check(query)
        is_follow_up = heuristic_result.get("is_follow_up", False)
        confidence = heuristic_result.get("confidence", 0.0)
        detection_reason = heuristic_result.get("reason", "unknown")
        
        # Check correctness
        correct = (is_follow_up == expected)
        status = "✅ CORRECT" if correct else "❌ INCORRECT"
        
        print(f"   Heuristic Result: {status}")
        print(f"   Detected: {'FOLLOW-UP' if is_follow_up else 'NEW TOPIC'} (confidence: {confidence:.2f})")
        print(f"   Detection reason: {detection_reason}")
        
        if "matched_indicators" in heuristic_result:
            print(f"   Matched indicators: {heuristic_result['matched_indicators']}")
        if "pattern" in heuristic_result:
            print(f"   Matched pattern: {heuristic_result['pattern']}")
        
        heuristic_results.append({
            "name": name,
            "correct": correct,
            "expected": expected,
            "detected": is_follow_up,
            "confidence": confidence
        })
    
    # Summary for heuristic method
    correct_count = sum(1 for r in heuristic_results if r["correct"])
    total_count = len(heuristic_results)
    accuracy = correct_count / total_count * 100
    
    print(f"\n" + "=" * 50)
    print(f"📊 Heuristic Method Summary:")
    print(f"   Correct: {correct_count}/{total_count}")
    print(f"   Accuracy: {accuracy:.1f}%")
    
    # Show incorrect predictions
    incorrect = [r for r in heuristic_results if not r["correct"]]
    if incorrect:
        print(f"\n❌ Incorrect Predictions:")
        for r in incorrect:
            expected_str = "FOLLOW-UP" if r["expected"] else "NEW TOPIC"
            detected_str = "FOLLOW-UP" if r["detected"] else "NEW TOPIC"
            print(f"   {r['name']}: Expected {expected_str}, got {detected_str}")
    
    # Test some edge cases
    print(f"\n🔍 Testing Edge Cases:")
    edge_cases = [
        "why is it important?",
        "how so?", 
        "what do you mean?",
        "can you explain?",
        "tell me more",
        "what about solar panels?",
        "那为什么?",  # Chinese: Then why?
        "¿por qué es importante?",  # Spanish: Why is it important?
        "comment ça marche?",  # French: How does it work?
    ]
    
    for case in edge_cases:
        result = _fallback_follow_up_check(case)
        is_follow_up = result.get("is_follow_up", False)
        confidence = result.get("confidence", 0.0)
        print(f"   '{case}' -> {'FOLLOW-UP' if is_follow_up else 'NEW TOPIC'} ({confidence:.2f})")
    
    print(f"\n✅ Follow-up detection testing completed!")

if __name__ == "__main__":
    asyncio.run(test_follow_up_detection())
