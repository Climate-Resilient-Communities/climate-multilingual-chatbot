import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

def test_imports():
    """Test if all necessary imports are working."""
    try:
        # Try importing the main chatbot class
        from src.main_nova import MultilingualClimateChatbot
        print("✓ Successfully imported MultilingualClimateChatbot")
        
        # Try importing utils
        from src.utils.env_loader import load_environment
        print("✓ Successfully imported load_environment")
        
        # Try importing models
        from src.models.nova_flow import BedrockModel
        print("✓ Successfully imported BedrockModel")
        
        # Try loading environment variables
        env_vars = load_environment()
        if env_vars:
            print("✓ Successfully loaded .env file")
        else:
            print("✗ Failed to load .env file")
        
        return True
    except Exception as e:
        print(f"✗ Import Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nTesting imports...")
    success = test_imports()
    if success:
        print("\n✓ All imports successful!")
    else:
        print("\n✗ Import test failed")