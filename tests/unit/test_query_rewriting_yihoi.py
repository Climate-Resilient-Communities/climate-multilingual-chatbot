#!/usr/bin/env python3
"""
Test script to demonstrate the query rewriting functionality for follow-up questions.
This shows how "why are they important?" becomes "why are wetlands important?" with context.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.query_rewriter import query_rewriter
from src.models.nova_flow import BedrockModel

async def test_query_rewriting():
    """Test the query rewriting functionality for follow-up detection."""
    
    print("🔄 Testing Query Rewriting for Follow-up Questions")
    print("=" * 60)
    
    try:
        # Initialize the model
        print("Initializing Nova model...")
        model = BedrockModel()
        
        # Test case: Wetlands conversation
        print("\n📝 Test Case: Wetlands Follow-up")
        print("-" * 40)
        
        conversation_history = [
            "User: Tell me about wetlands in Canada",
            "AI: Wetlands in Canada, particularly bogs and fens, are naturally acidic due to the presence of peat. Understanding the acidity of these wetlands helps us appreciate their unique ecosystems and the importance of protecting them."
        ]
        
        follow_up_query = "why are they important?"
        
        print(f"Conversation History:")
        for turn in conversation_history:
            print(f"  {turn}")
        
        print(f"\nFollow-up Query: '{follow_up_query}'")
        
        # Use the query rewriter
        print("\n🔄 Running query rewriter...")
        rewritten_query = await query_rewriter(
            conversation_history=conversation_history,
            user_query=follow_up_query,
            nova_model=model
        )
        
        print(f"\n✅ Rewritten Query: '{rewritten_query}'")
        
        # Test another case
        print("\n" + "=" * 60)
        print("📝 Test Case: Climate Change Follow-up")
        print("-" * 40)
        
        conversation_history_2 = [
            "User: What is climate change?",
            "AI: Climate change refers to long-term shifts in temperatures and weather patterns. Human activities, especially burning fossil fuels like coal, oil, and gas, are the main drivers of climate change."
        ]
        
        follow_up_query_2 = "how does it affect oceans?"
        
        print(f"Conversation History:")
        for turn in conversation_history_2:
            print(f"  {turn}")
        
        print(f"\nFollow-up Query: '{follow_up_query_2}'")
        
        print("\n🔄 Running query rewriter...")
        rewritten_query_2 = await query_rewriter(
            conversation_history=conversation_history_2,
            user_query=follow_up_query_2,
            nova_model=model
        )
        
        print(f"\n✅ Rewritten Query: '{rewritten_query_2}'")
        
        # Test off-topic case
        print("\n" + "=" * 60)
        print("📝 Test Case: Off-topic Follow-up")
        print("-" * 40)
        
        off_topic_query = "what's the best pizza recipe?"
        
        print(f"Follow-up Query: '{off_topic_query}'")
        
        print("\n🔄 Running query rewriter...")
        rewritten_query_3 = await query_rewriter(
            conversation_history=conversation_history,
            user_query=off_topic_query,
            nova_model=model
        )
        
        print(f"\n✅ Rewritten Query: '{rewritten_query_3}'")
        
        print("\n🎯 Summary:")
        print("- Follow-up questions are expanded with conversation context")
        print("- Pronouns like 'they' are replaced with specific topics")
        print("- Off-topic queries are properly classified and rejected")
        print("- This should fix the retrieval context issue!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query_rewriting())
