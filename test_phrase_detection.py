#!/usr/bin/env python3
"""
Test to identify which Portuguese phrase is causing false detection
"""

def test_phrase_detection():
    """Test the frontend phrase detection logic for Portuguese"""
    
    # Test query from user's report
    test_query = "What is toronto doing for climate change?"
    
    # Portuguese phrases from frontend
    pt_phrases = ['olá', 'oi', 'obrigado', 'obrigada', 'tchau', 'até logo', 'boa noite', 'por favor', 'desculpa', 'como está', 'como vai', 'bem', 'muito bem']
    
    print(f"Testing query: '{test_query}'")
    print(f"Query lowercase: '{test_query.lower()}'")
    print()
    
    # Test each Portuguese phrase
    query_lower = test_query.lower()
    matches = []
    
    for phrase in pt_phrases:
        if phrase in query_lower:
            matches.append(phrase)
            print(f"🚨 MATCH FOUND: Portuguese phrase '{phrase}' found in English query!")
            
            # Show where it matches
            start_idx = query_lower.find(phrase)
            end_idx = start_idx + len(phrase)
            print(f"   Position: {start_idx}-{end_idx}")
            print(f"   Context: '...{query_lower[max(0, start_idx-5):end_idx+5]}...'")
            print()
    
    if not matches:
        print("✅ No Portuguese phrases detected in the English query")
    else:
        print(f"❌ Found {len(matches)} false positive matches: {matches}")
        
    # Test conversation history from user's extensive chat log
    # Looking for common English words that might match Portuguese phrases
    test_cases = [
        "What is toronto doing for climate change?",
        "portugal climate policies",  # Should correctly detect 'por' in portugal
        "for climate change",         # Might incorrectly match 'por'
        "doing for the environment",  # Might incorrectly match 'por'
        "good for you",              # Might incorrectly match 'por' 
        "toronto for climate",       # Might incorrectly match 'por'
        "bem climate",               # Might incorrectly match 'bem'
        "point information",         # Might incorrectly match 'oi'
    ]
    
    print("\n=== Extended Test Cases ===")
    for test_case in test_cases:
        case_lower = test_case.lower()
        case_matches = []
        
        for phrase in pt_phrases:
            if phrase in case_lower:
                case_matches.append(phrase)
        
        if case_matches:
            print(f"❌ '{test_case}' → matches: {case_matches}")
        else:
            print(f"✅ '{test_case}' → no matches")

if __name__ == "__main__":
    test_phrase_detection()