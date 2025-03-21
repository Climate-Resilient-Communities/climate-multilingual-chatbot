#!/usr/bin/env python
"""
Script to download and save Hugging Face models locally.
This helps avoid download issues in Azure deployments.
"""

import os
import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_models():
    try:
        # Import required libraries
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        # Set local save directory
        models_dir = project_root / "models"
        climatebert_dir = models_dir / "climatebert"
        os.makedirs(climatebert_dir, exist_ok=True)
        
        # Model name
        model_name = "climatebert/distilroberta-base-climate-detector"
        
        logger.info(f"Downloading model: {model_name}")
        
        # Download and save model
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        logger.info(f"Saving model to {climatebert_dir}")
        
        # Save model and tokenizer locally
        model.save_pretrained(climatebert_dir)
        tokenizer.save_pretrained(climatebert_dir)
        
        logger.info("Model download and save completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error downloading models: {str(e)}")
        return False

if __name__ == "__main__":
    success = download_models()
    sys.exit(0 if success else 1)