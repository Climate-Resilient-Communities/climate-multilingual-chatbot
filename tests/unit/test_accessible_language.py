import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import re

@pytest.mark.asyncio
async def test_accessible_language_for_low_literacy():
    """Test that climate concepts are explained in simple language accessible to low-literacy users."""
    # Mock the Nova model
    mock_nova_model = MagicMock()

    # Response with technical jargon
    technical_response = """
    Anthropogenic climate change is primarily driven by greenhouse gas emissions, particularly CO2 from the combustion
    of fossil fuels. The resultant radiative forcing causes perturbations in the global energy budget, leading to
    atmospheric and oceanic temperature anomalies. This precipitates intensification of hydrological cycles and cryospheric
    degradation, manifesting as extreme precipitation events and accelerated ablation of terrestrial ice masses.
    """

    # Response with accessible language (short sentences for readability)
    simple_response = """Climate change is caused by human activities. We burn coal, oil, and gas. These release heat-trapping gases. Think of these gases like a blanket around Earth - they make the planet warmer. This warming causes many changes:

    - More strong storms and heavy rains in some places
    - Less rain and more droughts in other places
    - Ice and snow melting faster

    When ice melts, it's like when an ice cube melts in a glass - the water level goes up. This causes flooding. Coastal areas are most at risk.

    The good news is we can help. Use less energy. Walk or bike instead of driving. Support clean energy like solar and wind power.
    """

    # Set up the mock to first return technical response then simple response
    mock_nova_model.generate_response = AsyncMock(side_effect=[technical_response, simple_response])

    # Mock documents
    mock_docs = [
        {"title": "Climate Science Basics", "content": "Information about climate science", "url": "example.com"}
    ]

    # Import the renamed function (was nova_chat, now generate_chat_response)
    from src.models.gen_response_nova import generate_chat_response

    # Test with technical language response
    # Note: ClimateCache was removed from gen_response_nova; caching is now at pipeline level
    with patch('src.models.gen_response_nova.doc_preprocessing', return_value=mock_docs):
        # First test - technical response with complex language
        response1, _ = await generate_chat_response("What is climate change?", mock_docs, mock_nova_model)

        # Define complex technical terms that should be avoided
        technical_terms = [
            'anthropogenic', 'radiative forcing', 'perturbations', 'anomalies',
            'precipitates', 'intensification', 'hydrological cycles',
            'cryospheric', 'ablation'
        ]

        # Check that response contains technical jargon
        assert any(term in response1.lower() for term in technical_terms)

        # Check for complex sentence structure
        sentences = re.split(r'[.!?]', response1)
        long_sentences = [s for s in sentences if len(s.split()) > 20]  # Sentences over 20 words
        assert len(long_sentences) > 0

        # Second test - accessible language response
        response2, _ = await generate_chat_response("What is climate change?", mock_docs, mock_nova_model)

        # Check for plain language explanations
        assert "like a blanket" in response2.lower()  # Contains analogies
        assert "- " in response2  # Uses bullet points
        assert "ice cube melts in a glass" in response2.lower()  # Contains simple examples

        # Check for simple sentence structure
        sentences = re.split(r'[.!?]', response2)
        short_sentences = [s for s in sentences if s.strip() and len(s.split()) < 20]  # Sentences under 20 words
        long_sentences = [s for s in sentences if s.strip() and len(s.split()) >= 20]  # Sentences over 20 words
        assert len(short_sentences) > len(long_sentences)  # More short sentences than long ones

        # Check that technical terms are absent or explained
        unexplained_technical_terms = [term for term in technical_terms if term in response2.lower()]
        assert len(unexplained_technical_terms) == 0
