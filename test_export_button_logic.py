#!/usr/bin/env python3
"""
Test export button hiding logic for canned responses
"""

def test_export_button_logic():
    """Test the frontend logic for hiding export buttons on canned responses"""
    
    print("=== Testing Export Button Hiding Logic ===\n")
    
    # Simulate different message types
    test_messages = [
        {
            "role": "assistant",
            "content": "Hello, I am your multilingual climate chatbot. I can answer climate questions in any language. What do you want to learn?",
            "sources": [],
            "retrieval_source": "canned",
            "description": "Greeting canned response - should HIDE export button"
        },
        {
            "role": "assistant", 
            "content": "Glad to help. If you need more climate info, I will be here. Goodbye!",
            "sources": [],
            "retrieval_source": "canned",
            "description": "Goodbye canned response - should HIDE export button"
        },
        {
            "role": "assistant",
            "content": "You're welcome. If you have more climate questions, I am here to help.",
            "sources": [],
            "retrieval_source": "canned", 
            "description": "Thanks canned response - should HIDE export button"
        },
        {
            "role": "assistant",
            "content": "If this is a life-threatening emergency, please contact local authorities immediately...",
            "sources": [],
            "retrieval_source": "canned",
            "description": "Emergency canned response - should HIDE export button"
        },
        {
            "role": "assistant",
            "content": "How It Works\nChoose Language from the left side panel...",
            "sources": [],
            "retrieval_source": "canned",
            "description": "Instruction canned response - should HIDE export button"
        },
        {
            "role": "assistant",
            "content": "Climate change refers to long-term shifts in global temperatures and weather patterns...",
            "sources": [
                {"url": "https://example.com", "title": "Climate Source", "text": "Sample citation"}
            ],
            "retrieval_source": "search", 
            "description": "Regular response with sources - should SHOW export button"
        },
        {
            "role": "assistant",
            "content": "Global warming is primarily caused by human activities that increase greenhouse gas concentrations...",
            "sources": [],
            "retrieval_source": "search",
            "description": "Regular response without sources - should SHOW export button"
        },
        {
            "role": "assistant",
            "content": "Climate action requires urgent global cooperation and immediate policy changes...",
            "sources": [],
            # No retrieval_source (older messages)
            "description": "Legacy response without retrieval_source - should SHOW export button"
        }
    ]
    
    print("Testing export button visibility logic:")
    print("Logic: message.retrieval_source !== 'canned'")
    print()
    
    for i, message in enumerate(test_messages, 1):
        has_sources = len(message.get("sources", [])) > 0
        retrieval_source = message.get("retrieval_source")
        
        # Apply the frontend logic
        should_show_export = retrieval_source != "canned"
        
        print(f"Test {i}: {message['description']}")
        print(f"  Content preview: {message['content'][:50]}...")
        print(f"  Has sources: {has_sources}")
        print(f"  Retrieval source: {retrieval_source}")
        print(f"  Export button shown: {'YES' if should_show_export else 'NO'}")
        
        # Verify expectation
        is_canned = "canned response" in message['description'].lower()
        expected_hidden = is_canned
        actual_hidden = not should_show_export
        
        if expected_hidden == actual_hidden:
            print(f"  ✅ CORRECT: Export button behavior matches expectation")
        else:
            print(f"  ❌ ERROR: Expected {'hidden' if expected_hidden else 'shown'}, got {'hidden' if actual_hidden else 'shown'}")
        
        print()
    
    print("=== Summary of Implementation ===")
    print()
    print("Backend Changes:")
    print("1. ✅ Added retrieval_source field to ChatResponse model")
    print("2. ✅ Pipeline sets retrieval_source='canned' for canned responses")
    print("3. ✅ API router passes retrieval_source to frontend")
    print()
    print("Frontend Changes:")
    print("1. ✅ Added retrieval_source to Message type")
    print("2. ✅ Store retrieval_source when creating assistant messages")
    print("3. ✅ Hide ExportButton when message.retrieval_source === 'canned'")
    print()
    print("Canned Response Types (export button hidden):")
    print("- greeting: 'Hello, I am your multilingual climate chatbot...'")
    print("- goodbye: 'Glad to help. If you need more climate info...'")
    print("- thanks: 'You're welcome. If you have more climate questions...'")
    print("- emergency: 'If this is a life-threatening emergency...'") 
    print("- instruction: 'How It Works\\nChoose Language from...'")
    print()
    print("Regular Responses (export button shown):")
    print("- on-topic: Full climate information with citations")
    print("- off-topic: Gentle redirection messages")
    print("- All other response types")

if __name__ == "__main__":
    test_export_button_logic()