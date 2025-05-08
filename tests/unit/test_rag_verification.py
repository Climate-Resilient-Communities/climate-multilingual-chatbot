#!/usr/bin/env python
"""
Test script to verify that the RAG system is actually using retrieved information
in its responses rather than relying solely on the model's general knowledge.

This script tests the nova_flow module with:
1. Documents containing unique/fictional information
2. Questions targeting this unique information
3. Verification that responses include details from the documents
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

# Test documents containing unique/fictional information about climate initiatives
test_docs = [
    {
        'title': 'GreenSky Project in Bardonia',
        'content': 'The GreenSky Project in Bardonia has implemented a unique carbon capture technology called "ZephyrTrap" that converts atmospheric CO2 into solid carbon blocks using solar energy. The project was started in 2022 and has already sequestered 15,000 tons of carbon. The technology was developed by Dr. Marina Kovacs and uses a proprietary catalyst named VS-7.',
        'url': ['https://example.com/greensky-project']
    },
    {
        'title': 'Aqua-Terra Conservation Initiative',
        'content': 'The Aqua-Terra Conservation Initiative has created a network of "climate resilience hubs" in coastal communities. These hubs feature specialized flood barriers called "HydroShields" that can absorb up to 500 gallons of water per square meter. The initiative was launched in April 2023 and operates in 7 coastal cities. Their emergency response system "BlueAlert" can mobilize resources within 30 minutes of a flood warning.',
        'url': ['https://example.com/aqua-terra']
    },
    {
        'title': 'Urban Heat Island Mitigation Study',
        'content': 'A recent study on urban heat islands in Westville found that the "CoolStreets" program reduced summer temperatures by 4.2°C through the installation of reflective pavements and vertical gardens. The research, led by Dr. Jasmine Torres, showed a 23% decrease in cooling costs and a 15% reduction in heat-related hospital visits. The program used a special reflective coating called "ThermaBlock" on 40% of downtown streets.',
        'url': ['https://example.com/urban-heat']
    }
]

# Questions targeting specific information from the documents
test_questions = [
    {
        'query': 'What is the ZephyrTrap technology and how much carbon has it sequestered?',
        'expected_info': ['ZephyrTrap', '15,000 tons', 'solar energy', 'Dr. Marina Kovacs', 'VS-7'],
        'description': 'This question targets specific details about the fictional ZephyrTrap technology.'
    },
    {
        'query': 'How do HydroShields work and when was the Aqua-Terra initiative launched?',
        'expected_info': ['HydroShields', '500 gallons', 'April 2023', '7 coastal cities', 'BlueAlert'],
        'description': 'This question asks about details of the fictional HydroShields and Aqua-Terra initiative.'
    },
    {
        'query': 'What were the results of the CoolStreets program in Westville?',
        'expected_info': ['4.2°C', '23% decrease', 'cooling costs', 'Dr. Jasmine Torres', 'ThermaBlock'],
        'description': 'This question asks about specific numerical results from the fictional CoolStreets program.'
    },
    {
        'query': 'What is the effectiveness of tree planting for carbon capture?',
        'expected_info': [],
        'description': 'This question is NOT covered in the documents and should rely on the model\'s knowledge.'
    }
]

async def test_rag_verification():
    """Test if the system is using RAG properly by checking for specific document information in responses."""
    start_time = time.time()
    
    # Initialize Nova model
    load_environment()
    nova_model = BedrockModel()
    logger.info("Nova model initialized")
    
    results = []
    
    # Process each test question
    for i, question in enumerate(test_questions):
        logger.info(f"\nTEST CASE {i+1}: {question['description']}")
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
            if question['expected_info']:
                if coverage >= 80:
                    result = "PASS"
                    logger.info(f"RESULT: PASS - Response includes {coverage:.1f}% of expected information")
                else:
                    result = "FAIL"
                    logger.warning(f"RESULT: FAIL - Response only includes {coverage:.1f}% of expected information")
                
                logger.info(f"Found info: {found_info}")
                logger.info(f"Missing info: {missing_info}")
            else:
                # For question not covered in documents
                result = "INFO"
                logger.info("RESULT: INFO - This query wasn't covered in documents, checking if response indicates this")
                if "not mentioned" in response.lower() or "no information" in response.lower() or "not provided" in response.lower():
                    logger.info("Response properly indicates information isn't in the documents")
                else:
                    logger.info("Response attempts to answer without indicating information gaps")
            
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
    logger.info("\n=== RAG VERIFICATION TEST SUMMARY ===")
    passed = sum(1 for r in results if r['result'] == "PASS")
    failed = sum(1 for r in results if r['result'] == "FAIL")
    info = sum(1 for r in results if r['result'] == "INFO")
    errors = sum(1 for r in results if r['result'] == "ERROR")
    
    logger.info(f"Tests passed: {passed}")
    logger.info(f"Tests failed: {failed}")
    logger.info(f"Info only: {info}")
    logger.info(f"Errors: {errors}")
    
    if failed == 0 and errors == 0:
        logger.info("OVERALL RESULT: SUCCESS - System appears to be correctly using RAG")
    else:
        logger.warning("OVERALL RESULT: ISSUES DETECTED - System may not be correctly using RAG")
    
    # Save results to file for reference
    with open('rag_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Total test time: {time.time() - start_time:.2f} seconds")
    logger.info("Full results saved to rag_test_results.json")

if __name__ == "__main__":
    asyncio.run(test_rag_verification())