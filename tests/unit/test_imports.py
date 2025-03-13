import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

print("Testing imports...")

try:
    print("\nTesting nova_flow...")
    from src.models.nova_flow import BedrockModel
    print("✓ nova_flow imported successfully")

    print("\nTesting nova_generation...")
    from src.models.nova_generation import NovaChat
    print("✓ nova_generation imported successfully")

    print("\nTesting input_guardrail...")
    from src.models.input_guardrail import initialize_models, topic_moderation
    print("✓ input_guardrail imported successfully")

    print("\nTesting retrieval...")
    from src.models.retrieval import get_documents, get_hybrid_results
    print("✓ retrieval imported successfully")

    print("\nTesting query_routing...")
    from src.models.query_routing import MultilingualRouter
    print("✓ query_routing imported successfully")

    print("\nTesting hallucination_guard...")
    from src.models.hallucination_guard import check_hallucination
    print("✓ hallucination_guard imported successfully")

    print("\nTesting redis_cache...")
    from src.models.redis_cache import ClimateCache
    print("✓ redis_cache imported successfully")

    print("\nAll imports successful!")

except Exception as e:
    print(f"\n❌ Import error: {str(e)}")
    raise