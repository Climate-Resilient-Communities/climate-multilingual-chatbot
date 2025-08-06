#!/usr/bin/env python3
"""
Test script specifically for semantic similarity functionality.
This tests only the semantic similarity part without relying on ClimateBERT.
"""

import asyncio
import sys
import os
from pathlib import Path
import numpy as np

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from src.models.input_guardrail import get_climate_reference_texts, calculate_semantic_similarity

async def test_semantic_similarity_only():
    """Test only the semantic similarity functionality."""
    
    print("🚀 Testing Semantic Similarity Functionality")
    print("=" * 50)
    
    try:
        # Initialize only the similarity model
        print("Initializing sentence transformer model...")
        try:
            similarity_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("✅ Successfully initialized semantic similarity model")
        except Exception as e:
            print(f"❌ Failed to initialize similarity model: {e}")
            try:
                similarity_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
                print("✅ Successfully initialized fallback similarity model")
            except Exception as e2:
                print(f"❌ Failed to initialize any similarity model: {e2}")
                return
        
        # Test cases
        test_cases = [
            # Cases that should have HIGH similarity
            {
                "query": "What is the pH of ocean water?",
                "expected": "HIGH",
                "reason": "pH relates to ocean acidification from CO2 absorption"
            },
            {
                "query": "How do rivers affect the environment?", 
                "expected": "HIGH",
                "reason": "Rivers are part of climate-affected water systems"
            },
            {
                "query": "Tell me about coral reefs",
                "expected": "HIGH", 
                "reason": "Coral reefs are heavily impacted by climate change"
            },
            {
                "query": "What happens to ice when temperature rises?",
                "expected": "HIGH",
                "reason": "Ice melting is a direct climate change effect"
            },
            {
                "query": "How does farming change with weather patterns?",
                "expected": "HIGH",
                "reason": "Agriculture adaptation to changing climate"
            },
            {
                "query": "What are the effects on marine species?",
                "expected": "HIGH",
                "reason": "Marine biodiversity impacts from climate change"
            },
            {
                "query": "Precipitation patterns in my region",
                "expected": "HIGH",
                "reason": "Precipitation is directly climate-related"
            },
            
            # Cases that should have MEDIUM similarity
            {
                "query": "Tell me about water quality",
                "expected": "MEDIUM",
                "reason": "Water quality can be climate-related but not explicitly"
            },
            {
                "query": "How do plants grow in different environments?",
                "expected": "MEDIUM",
                "reason": "Plant growth relates to environmental conditions"
            },
            
            # Cases that should have LOW similarity
            {
                "query": "Where can I buy new shoes?",
                "expected": "LOW",
                "reason": "Shopping query, not climate-related"
            },
            {
                "query": "What's the best smartphone to buy?",
                "expected": "LOW", 
                "reason": "Technology shopping, not climate-related"
            },
            {
                "query": "How do I cook pasta?",
                "expected": "LOW",
                "reason": "Cooking instructions, not climate-related"
            },
        ]
        
        print(f"\nTesting {len(test_cases)} cases with similarity scoring:")
        print("-" * 50)
        
        reference_texts = get_climate_reference_texts()
        print(f"Using {len(reference_texts)} climate reference texts for comparison")
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expected = test_case["expected"]
            reason = test_case["reason"]
            
            print(f"\n{i}. Testing: '{query}'")
            print(f"   Expected: {expected} similarity")
            print(f"   Reason: {reason}")
            
            # Calculate semantic similarity
            similarity_score = calculate_semantic_similarity(query, reference_texts, similarity_model)
            
            # Determine category based on score
            if similarity_score >= 0.5:
                category = "HIGH"
            elif similarity_score >= 0.3:
                category = "MEDIUM"  
            else:
                category = "LOW"
            
            # Check if result matches expectation
            test_passed = (category == expected)
            
            if test_passed:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            
            print(f"   Result: {status} - Similarity: {similarity_score:.3f} ({category})")
            
            results.append({
                "query": query,
                "expected": expected,
                "actual": category,
                "score": similarity_score,
                "passed": test_passed
            })
        
        # Summary
        passed_tests = sum(1 for r in results if r["passed"])
        failed_tests = len(results) - passed_tests
        
        print("\n" + "=" * 50)
        print(f"📊 Test Summary:")  
        print(f"   ✅ Passed: {passed_tests}/{len(results)}")
        print(f"   ❌ Failed: {failed_tests}/{len(results)}")
        print(f"   Success Rate: {(passed_tests/len(results)*100):.1f}%")
        
        # Show score distribution
        scores = [r["score"] for r in results]
        print(f"\n📈 Score Distribution:")
        print(f"   Min: {min(scores):.3f}")
        print(f"   Max: {max(scores):.3f}")
        print(f"   Mean: {np.mean(scores):.3f}")
        print(f"   Std: {np.std(scores):.3f}")
        
        # Show failed cases
        if failed_tests > 0:
            print(f"\n❌ Failed Cases:")
            for r in results:
                if not r["passed"]:
                    print(f"   '{r['query']}': Expected {r['expected']}, got {r['actual']} (score: {r['score']:.3f})")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! The semantic similarity is working correctly.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Consider adjusting thresholds.")
            
        # Test with different thresholds
        print(f"\n🔍 Threshold Analysis:")
        thresholds = [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
        
        for threshold in thresholds:
            climate_passed = sum(1 for r in results if r["score"] >= threshold and r["expected"] in ["HIGH", "MEDIUM"])
            non_climate_rejected = sum(1 for r in results if r["score"] < threshold and r["expected"] == "LOW")
            total_correct = climate_passed + non_climate_rejected
            accuracy = total_correct / len(results) * 100
            print(f"   Threshold {threshold:.2f}: {accuracy:.1f}% accuracy ({total_correct}/{len(results)} correct)")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_semantic_similarity_only())
