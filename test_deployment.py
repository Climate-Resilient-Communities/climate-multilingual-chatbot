#!/usr/bin/env python3
"""
Deployment readiness test suite.
Run this before merging refactor changes to main.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

async def test_critical_imports():
    """Test that all critical imports work."""
    print("🔍 Testing critical imports...")
    
    try:
        from src.utils.env_loader import load_environment
        from src.main_nova import MultilingualClimateChatbot
        from src.models.input_guardrail import topic_moderation, initialize_models
        from src.webui.app_nova import main as streamlit_main
        print("✅ All critical imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        return False

async def test_environment_setup():
    """Test environment configuration."""
    print("🔍 Testing environment setup...")
    
    try:
        from src.utils.env_loader import load_environment, validate_environment
        load_environment()
        
        # Check critical env vars exist (don't log values for security)
        required_vars = ['PINECONE_API_KEY', 'COHERE_API_KEY', 'HF_API_TOKEN']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print(f"⚠️  Missing env vars: {missing}")
            return False
        
        print("✅ Environment configuration OK")
        return True
    except Exception as e:
        print(f"❌ Environment test failed: {str(e)}")
        return False

async def test_model_initialization():
    """Test that models can initialize."""
    print("🔍 Testing model initialization...")
    
    try:
        from src.models.input_guardrail import initialize_models
        topic_pipe, _ = initialize_models()
        
        if topic_pipe is None:
            print("❌ Topic moderation pipeline is None")
            return False
            
        print("✅ Models initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Model initialization failed: {str(e)}")
        return False

async def test_basic_query_processing():
    """Test basic query processing without full chatbot."""
    print("🔍 Testing basic query processing...")
    
    try:
        from src.models.input_guardrail import topic_moderation, initialize_models
        
        # Initialize models
        topic_pipe, _ = initialize_models()
        
        # Test basic moderation
        test_queries = [
            "What is climate change?",  # Should pass
            "Where can I buy shoes?",   # Should fail
        ]
        
        for query in test_queries:
            result = await topic_moderation(query, topic_pipe)
            expected_pass = "climate" in query.lower()
            
            if result.get('passed') == expected_pass:
                print(f"  ✅ '{query[:30]}...' - {result.get('reason')}")
            else:
                print(f"  ❌ '{query[:30]}...' - Unexpected result: {result}")
                return False
        
        print("✅ Basic query processing working")
        return True
    except Exception as e:
        print(f"❌ Query processing test failed: {str(e)}")
        return False

async def test_streamlit_importability():
    """Test that Streamlit app can be imported."""
    print("🔍 Testing Streamlit app importability...")
    
    try:
        # Don't actually run streamlit, just test imports
        import streamlit as st
        from src.webui.app_nova import init_chatbot, load_custom_css
        
        print("✅ Streamlit app imports successful")
        return True
    except Exception as e:
        print(f"❌ Streamlit import failed: {str(e)}")
        return False

async def run_deployment_tests():
    """Run all deployment readiness tests."""
    print("🚀 Running Deployment Readiness Tests\n")
    
    tests = [
        ("Critical Imports", test_critical_imports),
        ("Environment Setup", test_environment_setup),
        ("Model Initialization", test_model_initialization),
        ("Basic Query Processing", test_basic_query_processing),
        ("Streamlit Importability", test_streamlit_importability),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            results.append((test_name, False))
        print()  # Empty line between tests
    
    # Summary
    print("=" * 50)
    print("DEPLOYMENT READINESS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Ready for deployment!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Fix before deploying!")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_deployment_tests())
    sys.exit(0 if success else 1)
