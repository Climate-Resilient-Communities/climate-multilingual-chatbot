import asyncio
from src.models.nova_flow import BedrockModel

async def test_formatting():
    model = BedrockModel()
    
    print("Testing formatting sensitivity in translations:")
    print("-" * 50)
    
    # Test your exact case
    result1 = await model.nova_translation('what is climate change', 'english', 'french')
    print(f'1. "what is climate change" → "{result1}"')
    
    # Test with proper formatting
    result2 = await model.nova_translation('What is climate change?', 'english', 'french')
    print(f'2. "What is climate change?" → "{result2}"')
    
    # Test with just capitalization
    result3 = await model.nova_translation('What is climate change', 'english', 'french')
    print(f'3. "What is climate change" → "{result3}"')
    
    # Test with just punctuation
    result4 = await model.nova_translation('what is climate change?', 'english', 'french')
    print(f'4. "what is climate change?" → "{result4}"')

if __name__ == "__main__":
    asyncio.run(test_formatting())
