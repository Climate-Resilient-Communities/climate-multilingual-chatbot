from dotenv import load_dotenv

__all__ = ['load_environment']

def load_environment():
    """
    Loads environment variables from the .env file.
    Call this function wherever you need to ensure environment variables are loaded.
    Returns True if environment was loaded successfully.
    """
    try:
        load_dotenv()
        return True
    except Exception as e:
        print(f"Error loading environment: {e}")
        return False