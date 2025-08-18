#!/usr/bin/env python3
"""
Quick test for instruction canned responses
"""

import sys
import os
import json
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.query_rewriter import query_rewriter
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

async def test_instruction_canned():
    load_environment()
    nova_model = BedrockModel()
    
    result = await query_rewriter(
        conversation_history=[],
        user_query="Help",
        nova_model=nova_model,
        selected_language_code="en"
    )
    
    parsed = json.loads(result)
    canned_info = parsed.get('canned', {})
    print(f"Classification: {parsed.get('classification')}")
    print(f"Canned enabled: {canned_info.get('enabled')}")
    print(f"Canned text: {canned_info.get('text', '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_instruction_canned())