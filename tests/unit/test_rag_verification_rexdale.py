#!/usr/bin/env python
"""
Specialized RAG verification test using fictional information about Rexdale's climate initiatives.
This tests whether the response generation is actually using the provided documents rather than
the model's general knowledge about climate change.
"""

import asyncio
import logging
import time
import json
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test documents containing fictional information about Rexdale climate initiatives
# These contain specific details the model wouldn't know about
test_docs = [
    {
        'title': 'Rexdale SNAP Action Plan 2023-2025',
        'content': 'The Rexdale Sustainable Neighborhood Action Plan (SNAP) established in 2023 aims to reduce community carbon emissions by 45% by 2025. The plan includes the innovative "GreenRex" program which installed 127 solar-powered street lights along Kipling Avenue and Islington Avenue, saving the community $87,000 annually in electricity costs. The SNAP initiative is led by Community Director Maria Delgado who previously managed climate programs in Vancouver.',
        'url': ['https://example.com/rexdale-snap']
    },
    {
        'title': 'Rexdale Methane Capture Project',
        'content': 'In 2024, Rexdale launched a methane capture system at the North Etobicoke Waste Management Facility that uses patented "MethaConvert" technology to transform landfill methane into hydrogen fuel. The project cost $3.4 million but is expected to generate $750,000 annually in hydrogen sales. The facility captures approximately 230 tons of methane per year, equivalent to taking 4,600 cars off the road.',
        'url': ['https://example.com/rexdale-methane']
    },
    {
        'title': 'Rexdale Urban Heat Island Mitigation Plan',
        'content': 'The Rexdale Community Council approved the "CoolBlock" initiative in March 2024, which plans to convert 17 parking lots into green spaces with special heat-reflective surfaces. The project uses a proprietary material called "ThermaReflect-9" that can lower surface temperatures by up to 12°C compared to standard asphalt. The initiative is funded through the "Rexdale Climate Resilience Fund" which collected $1.2 million from local businesses.',
        'url': ['https://example.com/rexdale-cooling']
    }
]

# Questions targeting specific details from the fictional documents
test_questions = [
    {
        'query': 'What is the Rexdale SNAP Action Plan and what are its goals?',
        'expected_info': ['SNAP', '45%', '2025', 'GreenRex', '127 solar-powered', 'Maria Delgado', '$87,000'],
        'description': 'This question targets specific details about the fictional Rexdale SNAP program.'
    },
    {
        'query': 'How does the Rexdale methane capture project work and what are the benefits?',
        'expected_info': ['MethaConvert', '$3.4 million', '230 tons', 'hydrogen fuel', '$750,000', '4,600 cars'],
        'description': 'This question asks about the fictional methane capture project specifics.'
    },
    {
        'query': 'What is the CoolBlock initiative in Rexdale?',
        'expected_info': ['CoolBlock', '17 parking lots', 'ThermaReflect-9', '12°C', '$1.2 million', 'March 2024'],
        'description': 'This question asks about the fictional CoolBlock initiative.'
    },
    {
        'query': 'What climate change initiatives is Rexdale working on?',
        'expected_info': ['SNAP', 'GreenRex', 'methane capture', 'CoolBlock', 'MethaConvert', 'ThermaReflect-9'],
        'description': 'This general question should include key elements from all fictional documents.'
    }
]

async def test_rag_verification_rexdale():
    """Test if the system is using RAG properly by checking for fictional Rexdale information in responses."""
    start_time = time.time()
    
    # Initialize Nova model
    load_environment()
    nova_model = BedrockModel()
    logger.info("Nova model initialized")
    
    results = []
    
    # Process each test question
    for i, question in enumerate(test_questions):
        logger.info(f"\n===== TEST CASE {i+1}: {question['description']} =====")
        logger.info(f"QUERY: {question['query']}")
        
        try:
            # Generate response
            response = await nova_model.generate_response(
                query=question['query'],
                documents=test_docs,
                description="Provide detailed information based on the documents provided."
            )
            
            logger.info(f"RESPONSE: {response}")
            
            # Check if response contains expected information
            found_info = []
            missing_info = []
            
            for info in question['expected_info']:
                if info.lower() in response.lower():
                    found_info.append(info)
                else:
                    missing_info.append(info)
            
            # Calculate info coverage percentage
            coverage = 0
            if question['expected_info']:
                coverage = len(found_info) / len(question['expected_info']) * 100
            
            # Determine result
            if coverage >= 80:
                result = "PASS"
                logger.info(f"RESULT: PASS - Response includes {coverage:.1f}% of expected information")
            else:
                result = "FAIL"
                logger.warning(f"RESULT: FAIL - Response only includes {coverage:.1f}% of expected information")
            
            logger.info(f"Found info: {found_info}")
            logger.info(f"Missing info: {missing_info}")
            
            # Store results
            results.append({
                "query": question['query'],
                "response": response,
                "expected_info": question['expected_info'],
                "found_info": found_info,
                "missing_info": missing_info,
                "coverage": coverage,
                "result": result
            })
            
        except Exception as e:
            logger.error(f"Error during test: {str(e)}")
            results.append({
                "query": question['query'],
                "error": str(e),
                "result": "ERROR"
            })
    
    # Summary
    logger.info("\n=== REXDALE RAG VERIFICATION TEST SUMMARY ===")
    passed = sum(1 for r in results if r['result'] == "PASS")
    failed = sum(1 for r in results if r['result'] == "FAIL")
    errors = sum(1 for r in results if r['result'] == "ERROR")
    
    logger.info(f"Tests passed: {passed}")
    logger.info(f"Tests failed: {failed}")
    logger.info(f"Errors: {errors}")
    
    if failed == 0 and errors == 0:
        logger.info("OVERALL RESULT: SUCCESS - System appears to be correctly using RAG with Rexdale information")
    else:
        logger.warning("OVERALL RESULT: ISSUES DETECTED - System may not be correctly using RAG with Rexdale information")
    
    # Save results to file for reference
    with open('rexdale_rag_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Total test time: {time.time() - start_time:.2f} seconds")
    logger.info("Full results saved to rexdale_rag_test_results.json")

if __name__ == "__main__":
    asyncio.run(test_rag_verification_rexdale())