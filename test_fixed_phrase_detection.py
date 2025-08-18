#!/usr/bin/env python3
"""
Test the fixed phrase detection logic to ensure word boundaries work
"""
import re

def test_fixed_phrase_detection():
    """Test the fixed frontend phrase detection logic for Portuguese"""
    
    # Portuguese phrases from frontend
    pt_phrases = ['olá', 'oi', 'obrigado', 'obrigada', 'tchau', 'até logo', 'boa noite', 'por favor', 'desculpa', 'como está', 'como vai', 'bem', 'muito bem']
    
    test_cases = [
        ("What is toronto doing for climate change?", False, "Should NOT match 'oi' in 'doing'"),
        ("doing for the environment", False, "Should NOT match 'oi' in 'doing'"),
        ("point information", False, "Should NOT match 'oi' in 'point'"), 
        ("important for climate", False, "Should NOT match 'por' in 'important'"),
        ("bem climate", False, "Should NOT match 'bem' as standalone without context"),
        ("Oi, como vai?", True, "Should match standalone 'oi' greeting"),
        ("Hello, oi there!", True, "Should match standalone 'oi'"),
        ("Por favor, help me", True, "Should match 'por favor' phrase"),
        ("muito bem, obrigado", True, "Should match multiple Portuguese phrases"),
    ]
    
    print("=== Testing Fixed Phrase Detection with Word Boundaries ===\n")
    
    for test_query, should_match, description in test_cases:
        query_lower = test_query.lower()
        matches = []
        
        # Apply the same logic as the fix
        for phrase in pt_phrases:
            # Use word boundaries to avoid matching 'oi' in 'doing' or 'por' in 'important'
            regex = re.compile(f"\\b{re.escape(phrase)}\\b", re.IGNORECASE)
            if regex.search(query_lower):
                matches.append(phrase)
        
        has_matches = len(matches) > 0
        
        if has_matches == should_match:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        print(f"{status}: '{test_query}'")
        print(f"    Expected: {'Match' if should_match else 'No match'}")
        print(f"    Actual: {'Match' if has_matches else 'No match'} {matches if matches else ''}")
        print(f"    Description: {description}")
        print()

if __name__ == "__main__":
    test_fixed_phrase_detection()