import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

@pytest.mark.asyncio
async def test_community_actionable_recommendations():
    """Test that community-specific questions get actionable, local recommendations."""
    # Mock the Nova model
    mock_nova_model = MagicMock()
    
    # Two potential responses - one generic and one with specific actionable items
    generic_response = "Climate change affects urban areas through heat waves and extreme weather events."
    
    actionable_response = """
    To address urban heat wave risks in Toronto, here are specific actions:
    
    1. Visit cooling centers at North York Civic Centre or Toronto Reference Library
    2. Use the city's interactive map to find air-conditioned public spaces near you
    3. Contact Toronto Public Health at 311 for emergency cooling support
    4. Join the Parkdale Community Response Network which provides check-ins for vulnerable residents
    5. Consider home cooling options like window shades and energy-efficient fans available through Toronto's Home Energy Loan Program
    """
    
    # Set up the mock to first return generic response then actionable response
    mock_nova_model.generate_response = AsyncMock(side_effect=[generic_response, actionable_response])
    
    # Mock documents
    mock_docs = [
        {"title": "Urban Heat Islands", "content": "Information about urban heat", "url": "example.com"},
        {"title": "Toronto Climate Resilience", "content": "Toronto's climate adaptation plan", "url": "toronto.ca"}
    ]
    
    # Import the function under test
    from src.models.gen_response_nova import nova_chat
    
    # Test with generic non-actionable response
    with patch('src.models.gen_response_nova.doc_preprocessing', return_value=mock_docs):
        with patch('src.models.gen_response_nova.ClimateCache') as mock_cache:
            # Configure cache to not have a hit
            mock_cache_instance = MagicMock()
            mock_cache_instance.get = AsyncMock(return_value=None)
            mock_cache_instance.set = AsyncMock(return_value=True)
            mock_cache_instance.redis_client = True
            mock_cache.return_value = mock_cache_instance
            
            # First test - should fail as it's a generic response
            response1, _ = await nova_chat("What can people in Toronto do during a heat wave?", mock_docs, mock_nova_model)
            
            # Check that the response doesn't contain actionable information
            assert "Toronto" not in response1
            assert "specific" not in response1.lower()
            assert "1." not in response1  # No numbered list
            assert "cooling centers" not in response1.lower()
            assert "contact" not in response1.lower()
            
            # Second test - should have specific actionable recommendations
            response2, _ = await nova_chat("What can people in Toronto do during a heat wave?", mock_docs, mock_nova_model)
            
            # Check for specific actionable advice
            assert "Toronto" in response2
            assert any(location in response2 for location in ["North York Civic Centre", "Toronto Reference Library"])
            assert "311" in response2  # Contains contact information
            assert "cooling centers" in response2.lower()
            assert "map" in response2.lower()  # References to specific resources
            
            # Check for multiple actionable recommendations (at least 3)
            actionable_items = [line for line in response2.split('\n') if line.strip().startswith(('1.', '2.', '3.', '4.', '5.'))]
            assert len(actionable_items) >= 3