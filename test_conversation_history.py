#!/usr/bin/env python3
"""
Test script to verify the conversation history numbering fix.
This tests if the query rewriter correctly identifies language when switching
from Spanish conversation history to English current query.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.query_rewriter import query_rewriter
from src.models.nova_flow import BedrockModel


async def test_mixed_language_conversation():
    """Test conversation with Spanish history and English current query."""
    
    print("🧪 Testing Mixed Language Conversation History")
    print("="*50)
    
    # Initialize the model
    try:
        model = BedrockModel()
    except Exception as e:
        print(f"❌ Failed to initialize BedrockModel: {e}")
        return
    
    # Simulate a Spanish conversation with English follow-up
    conversation_history = [
        {"role": "user", "content": "¿Cómo está luchando Rexdale contra el cambio climático?"},
        {"role": "assistant", "content": "Rexdale está implementando techos verdes y promoviendo vehículos eléctricos para combatir el cambio climático."},
        {"role": "user", "content": "¿Qué más están haciendo?"},
        {"role": "assistant", "content": "También están desarrollando programas de reciclaje y educación ambiental para la comunidad."}
    ]
    
    # Current query in English (user switched languages)
    current_query = "What else are they doing?"
    selected_language = "en"  # User selected English
    
    print(f"📝 Conversation History ({len(conversation_history)} messages):")
    for i, msg in enumerate(conversation_history, 1):
        print(f"   Message {i} ({msg['role']}): {msg['content']}")
    
    print(f"\n🎯 Current Query (Message {len(conversation_history) + 1}): '{current_query}'")
    print(f"🌐 Selected Language: {selected_language}")
    print(f"\n⚡ Testing query rewriter...")
    
    try:
        result = await query_rewriter(
            conversation_history=conversation_history,
            user_query=current_query,
            nova_model=model,
            selected_language_code=selected_language
        )
        
        print(f"\n✅ Query Rewriter Result:")
        print("-" * 30)
        print(result)
        print("-" * 30)
        
        # Parse the result to check if language detection worked correctly
        import re
        
        lang_match = re.search(r"Language:\s*([a-z]{2}|unknown)", result, re.IGNORECASE)
        match_match = re.search(r"LanguageMatch:\s*(yes|no)", result, re.IGNORECASE)
        cls_match = re.search(r"Classification:\s*(on-topic|off-topic|harmful)", result, re.IGNORECASE)
        
        detected_lang = lang_match.group(1).lower() if lang_match else 'unknown'
        language_match = match_match.group(1).lower() if match_match else 'unknown'
        classification = cls_match.group(1).lower() if cls_match else 'unknown'
        
        print(f"\n📊 Analysis:")
        print(f"   Detected Language: {detected_lang}")
        print(f"   Language Match: {language_match}")
        print(f"   Classification: {classification}")
        
        # Check if the test passed
        if detected_lang == 'en' and language_match == 'yes':
            print(f"\n🎉 ✅ TEST PASSED!")
            print(f"   ✓ Correctly detected English in current query")
            print(f"   ✓ Ignored Spanish conversation history")
            print(f"   ✓ Language match successful")
        else:
            print(f"\n❌ TEST FAILED!")
            print(f"   Expected: detected_lang='en', language_match='yes'")
            print(f"   Actual: detected_lang='{detected_lang}', language_match='{language_match}'")
        
    except Exception as e:
        print(f"❌ Error during query rewriting: {e}")
        import traceback
        traceback.print_exc()


async def test_single_language_conversation():
    """Test conversation entirely in English as control."""
    
    print("\n🧪 Testing Single Language Conversation (Control Test)")
    print("="*50)
    
    try:
        model = BedrockModel()
    except Exception as e:
        print(f"❌ Failed to initialize BedrockModel: {e}")
        return
    
    # English conversation throughout
    conversation_history = [
        {"role": "user", "content": "How is Rexdale fighting climate change?"},
        {"role": "assistant", "content": "Rexdale is implementing green roofs and promoting electric vehicles."}
    ]
    
    current_query = "What else are they doing?"
    selected_language = "en"
    
    print(f"📝 Conversation History ({len(conversation_history)} messages):")
    for i, msg in enumerate(conversation_history, 1):
        print(f"   Message {i} ({msg['role']}): {msg['content']}")
    
    print(f"\n🎯 Current Query (Message {len(conversation_history) + 1}): '{current_query}'")
    print(f"🌐 Selected Language: {selected_language}")
    
    try:
        result = await query_rewriter(
            conversation_history=conversation_history,
            user_query=current_query,
            nova_model=model,
            selected_language_code=selected_language
        )
        
        print(f"\n✅ Query Rewriter Result:")
        print("-" * 30)
        print(result)
        print("-" * 30)
        
        # This should also pass
        import re
        lang_match = re.search(r"Language:\s*([a-z]{2}|unknown)", result, re.IGNORECASE)
        match_match = re.search(r"LanguageMatch:\s*(yes|no)", result, re.IGNORECASE)
        
        detected_lang = lang_match.group(1).lower() if lang_match else 'unknown'
        language_match = match_match.group(1).lower() if match_match else 'unknown'
        
        if detected_lang == 'en' and language_match == 'yes':
            print(f"\n🎉 ✅ CONTROL TEST PASSED!")
        else:
            print(f"\n❌ CONTROL TEST FAILED!")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting Conversation History Language Detection Tests")
    print("=" * 60)
    
    await test_mixed_language_conversation()
    await test_single_language_conversation()
    
    print("\n" + "=" * 60)
    print("🏁 Tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
