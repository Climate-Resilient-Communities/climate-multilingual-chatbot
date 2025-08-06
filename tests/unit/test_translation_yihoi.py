#!/usr/bin/env python
"""
Standalone translation testing script.
Tests the Nova translation functionality without running the full chatbot.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_translations():
    """Test translation functionality independently."""
    try:
        # Import only what we need for translation
        from src.models.nova_flow import BedrockModel
        
        # Initialize just the Nova model for translation
        logger.info("Initializing Nova model for translation testing...")
        nova_model = BedrockModel()
        
        # Test cases: [text, source_language, target_language]
        test_cases = [
            ["Hello, how are you?", "english", "spanish"],
            ["What is climate change?", "english", "french"],  # Question test
            ["Climate change is a serious issue", "english", "french"],  # Statement test
            ["How can we reduce emissions?", "english", "spanish"],  # Another question
            ["Hola, ¿cómo estás?", "spanish", "english"],
            ["Le changement climatique est un problème grave", "french", "english"],
            ["What are renewable energy sources?", "english", "german"],
            ["Was sind erneuerbare Energiequellen?", "german", "english"]
        ]
        
        logger.info("Starting translation tests...\n")
        
        for i, (text, source_lang, target_lang) in enumerate(test_cases, 1):
            logger.info(f"Test {i}: {source_lang} → {target_lang}")
            logger.info(f"Input: {text}")
            
            try:
                # Test translation
                translated = await nova_model.nova_translation(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                
                logger.info(f"Output: {translated}")
                logger.info("✓ Translation successful\n")
                
            except Exception as e:
                logger.error(f"✗ Translation failed: {str(e)}\n")
        
        logger.info("Translation testing completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error during translation testing: {str(e)}")
        return False

async def test_specific_translation():
    """Test a specific translation interactively."""
    try:
        from src.models.nova_flow import BedrockModel
        
        nova_model = BedrockModel()
        
        print("\n" + "="*50)
        print("Interactive Translation Test")
        print("="*50)
        
        while True:
            print("\nAvailable languages: english, spanish, french, german, italian, portuguese, etc.")
            text = input("Enter text to translate (or 'quit' to exit): ").strip()
            
            if text.lower() == 'quit':
                break
                
            source_lang = input("Source language: ").strip()
            target_lang = input("Target language: ").strip()
            
            if not text or not source_lang or not target_lang:
                print("Please provide all inputs.")
                continue
            
            try:
                print(f"\nTranslating '{text}' from {source_lang} to {target_lang}...")
                translated = await nova_model.nova_translation(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                print(f"Result: {translated}")
                
            except Exception as e:
                print(f"Translation error: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in interactive translation test: {str(e)}")
        return False

if __name__ == "__main__":
    print("Translation Test Script")
    print("=" * 30)
    print("1. Run automated tests")
    print("2. Interactive translation test")
    
    choice = input("Choose option (1 or 2): ").strip()
    
    if choice == "1":
        success = asyncio.run(test_translations())
    elif choice == "2":
        success = asyncio.run(test_specific_translation())
    else:
        print("Invalid choice")
        success = False
    
    sys.exit(0 if success else 1)
