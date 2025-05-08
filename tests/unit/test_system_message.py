#!/usr/bin/env python
"""
Test script to check if the system message is being properly applied to responses.
"""

import asyncio
import logging
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_system_message():
    """Test if responses follow the style and tone defined in the system message."""
    
    # Initialize Nova model
    load_environment()
    nova_model = BedrockModel()
    logger.info("Nova model initialized")
    
    # Test document
    test_doc = [{
        'title': 'Climate Impacts', 
        'content': 'Climate change disproportionately affects low-income communities due to limited resources for adaptation and resilience. These communities often have less access to air conditioning during heat waves, live in flood-prone areas, and have fewer resources to relocate or rebuild after extreme weather events.'
    }]
    
    # Test query that should elicit a response demonstrating the system message guidelines
    query = "What is climate change and how does it affect people in low-income communities?"
    
    logger.info(f"QUERY: {query}")
    
    # Generate response
    response = await nova_model.generate_response(
        query=query,
        documents=test_doc,
        description="Focus on empowering solutions and accessible language."
    )
    
    logger.info(f"RESPONSE WITH SYSTEM MESSAGE:\n{response}")
    
    # Analyze if the response follows the guidelines in the system message
    guidelines_met = []
    if "ninth‑grade" in response.lower() or len(response.split()) / len(response.split(".")) < 15:
        guidelines_met.append("✓ Simple language")
    
    if "you" in response.lower() or "we" in response.lower():
        guidelines_met.append("✓ Conversational tone")
        
    if any(term in response.lower() for term in ["can", "could", "try", "consider", "option"]):
        guidelines_met.append("✓ Actionable advice")
        
    if len(response.split("\n\n")) > 1 or "- " in response:
        guidelines_met.append("✓ Readable formatting")
        
    if any(term in response.lower() for term in ["hope", "solution", "improve", "better", "help"]):
        guidelines_met.append("✓ Positive/empowering tone")
    
    logger.info(f"GUIDELINES MET: {len(guidelines_met)}/5")
    for guideline in guidelines_met:
        logger.info(guideline)
        
if __name__ == "__main__":
    asyncio.run(test_system_message())