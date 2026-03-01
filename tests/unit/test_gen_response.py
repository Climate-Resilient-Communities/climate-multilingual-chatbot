from src.models.gen_response_nova import generate_chat_response
from src.models.nova_flow import BedrockModel
from src.utils.env_loader import load_environment

def test_gen_response():
    print("\n=== Testing Response Generation ===")

    # Load environment and initialize client
    load_environment()
    nova_client = BedrockModel()

    # Test documents
    test_docs = [
        {
            'title': 'Climate Change Overview',
            'content': 'Climate change is a long-term shift in global weather patterns and temperatures.',
            'url': ['https://example.com/climate']
        },
        {
            'title': 'Impact Analysis',
            'content': 'Rising temperatures are causing more extreme weather events worldwide.',
            'url': ['https://example.com/impacts']
        }
    ]

    print("\nGenerating response...")
    try:
        import asyncio
        response, citations = asyncio.run(generate_chat_response(
            query="What is climate change and its main impacts?",
            documents=test_docs,
            model=nova_client
        ))

        print("\nResponse:")
        print(response)
        print("\nCitations:")
        for citation in citations:
            print(f"- {citation}")

        print("\n✓ Response generation successful!")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")

if __name__ == "__main__":
    test_gen_response()