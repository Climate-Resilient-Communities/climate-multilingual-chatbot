#!/usr/bin/env python3
"""
Test Cohere Conversation History Formatting
===========================================

Debug the conversation history formatting issue before running comprehensive tests.
This will help us identify and fix the "all elements in history must have a message" error.
"""

import asyncio
import sys
import os
import json
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.climate_pipeline import ClimateQueryPipeline

async def test_cohere_conversation_history():
    """Test Cohere conversation history formatting specifically."""
    print("🧪 COHERE CONVERSATION HISTORY DEBUG TEST")
    print("=" * 50)
    
    try:
        # Initialize pipeline
        print("Initializing pipeline...")
        pipeline = ClimateQueryPipeline(index_name="climate-change-adaptation-index-10-24-prod")
        print("✅ Pipeline initialized")
        
        # Test 1: Simple query without history
        print(f"\n📝 Test 1: Simple query (no history)")
        print(f"Query: What is climate change?")
        
        result1 = await pipeline.process_query(
            query="What is climate change?",
            language_name="english",
            conversation_history=None
        )
        
        if result1.get("success"):
            print(f"✅ SUCCESS: Simple query worked")
            print(f"Response length: {len(result1.get('response', ''))}")
            
            # Test 2: Multi-turn with proper history formatting
            print(f"\n📝 Test 2: Multi-turn with conversation history")
            print(f"First query: What is climate change?")
            print(f"Follow-up: Tell me more about greenhouse gases")
            
            # Format conversation history as expected
            conversation_history = [
                {
                    "user": "What is climate change?",
                    "assistant": result1.get("response", "")[:200]  # Truncate for test
                }
            ]
            
            print(f"\n🔍 Debug: Conversation history format:")
            print(json.dumps(conversation_history, indent=2)[:300] + "...")
            
            result2 = await pipeline.process_query(
                query="Tell me more about greenhouse gases",
                language_name="english",
                conversation_history=conversation_history
            )
            
            if result2.get("success"):
                print(f"✅ SUCCESS: Multi-turn query worked!")
                print(f"Response length: {len(result2.get('response', ''))}")
                print(f"🧠 Context synthesis test: {'greenhouse' in result2.get('response', '').lower()}")
            else:
                print(f"❌ FAILED: Multi-turn query failed")
                print(f"Error: {result2.get('response', 'No error message')}")
                
        else:
            print(f"❌ FAILED: Simple query failed")
            print(f"Error: {result1.get('response', 'No error message')}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_different_history_formats():
    """Test different conversation history formats to find what works."""
    print(f"\n🔬 TESTING DIFFERENT HISTORY FORMATS")
    print("=" * 50)
    
    try:
        pipeline = ClimateQueryPipeline(index_name="climate-change-adaptation-index-10-24-prod")
        
        # Get a base response first
        base_result = await pipeline.process_query(
            query="What causes climate change?",
            language_name="english",
            conversation_history=None
        )
        
        if not base_result.get("success"):
            print("❌ Base query failed, can't test history formats")
            return
            
        base_response = base_result.get("response", "")[:150]
        print(f"✅ Base response obtained ({len(base_response)} chars)")
        
        # Test Format 1: Our current format
        print(f"\n📝 Format 1: {{user, assistant}} format")
        history_format1 = [
            {
                "user": "What causes climate change?",
                "assistant": base_response
            }
        ]
        
        try:
            result1 = await pipeline.process_query(
                query="How do greenhouse gases work?",
                language_name="english",
                conversation_history=history_format1
            )
            print(f"✅ Format 1: {'SUCCESS' if result1.get('success') else 'FAILED'}")
            if not result1.get("success"):
                print(f"   Error: {result1.get('response', '')[:100]}")
        except Exception as e:
            print(f"❌ Format 1 Exception: {str(e)}")
        
        # Test Format 2: Standard role/content format
        print(f"\n📝 Format 2: {{role, content}} format")
        history_format2 = [
            {"role": "user", "content": "What causes climate change?"},
            {"role": "assistant", "content": base_response}
        ]
        
        try:
            result2 = await pipeline.process_query(
                query="How do greenhouse gases work?",
                language_name="english",
                conversation_history=history_format2
            )
            print(f"✅ Format 2: {'SUCCESS' if result2.get('success') else 'FAILED'}")
            if not result2.get("success"):
                print(f"   Error: {result2.get('response', '')[:100]}")
        except Exception as e:
            print(f"❌ Format 2 Exception: {str(e)}")
        
        # Test Format 3: Cohere-specific format
        print(f"\n📝 Format 3: Cohere {{role, message}} format")
        history_format3 = [
            {"role": "USER", "message": "What causes climate change?"},
            {"role": "CHATBOT", "message": base_response}
        ]
        
        try:
            result3 = await pipeline.process_query(
                query="How do greenhouse gases work?",
                language_name="english",
                conversation_history=history_format3
            )
            print(f"✅ Format 3: {'SUCCESS' if result3.get('success') else 'FAILED'}")
            if not result3.get("success"):
                print(f"   Error: {result3.get('response', '')[:100]}")
        except Exception as e:
            print(f"❌ Format 3 Exception: {str(e)}")
            
    except Exception as e:
        print(f"❌ ERROR in format testing: {str(e)}")

async def main():
    """Main test function."""
    await test_cohere_conversation_history()
    await test_different_history_formats()
    
    print(f"\n🎯 SUMMARY")
    print("This test helps identify the correct conversation history format.")
    print("Once we find the working format, we can update the comprehensive test.")

if __name__ == "__main__":
    asyncio.run(main())
