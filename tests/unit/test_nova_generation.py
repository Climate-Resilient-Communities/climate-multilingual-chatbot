"""Tests for Nova model generation via BedrockModel (replaces archived NovaChat)."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from src.models.nova_flow import BedrockModel
from src.models.system_messages import CLIMATE_SYSTEM_MESSAGE


@pytest.fixture
def sample_documents():
    return [
        {
            'title': 'Climate Change Basics',
            'content': 'Climate change refers to long-term shifts in temperatures and weather patterns.',
            'url': ['http://example.com/climate']
        },
        {
            'title': 'Global Warming Effects',
            'content': 'Global warming leads to rising sea levels and extreme weather.',
            'url': ['http://example.com/effects']
        }
    ]


def test_bedrock_model_initialization():
    """Test that BedrockModel can be instantiated."""
    with patch('boto3.client') as mock_boto3:
        model = BedrockModel()
        assert model is not None


def test_system_message_exists():
    """Test that the climate system message is defined and non-empty."""
    assert CLIMATE_SYSTEM_MESSAGE is not None
    assert len(CLIMATE_SYSTEM_MESSAGE) > 0
    assert "climate" in CLIMATE_SYSTEM_MESSAGE.lower()


@pytest.mark.asyncio
async def test_generate_response_returns_string(sample_documents):
    """Test that generate_response returns a string."""
    with patch('boto3.client') as mock_boto3:
        model = BedrockModel()

        # Mock the internal invoke
        mock_response_body = json.dumps({
            "output": {
                "message": {
                    "content": [
                        {"text": "Climate change is a long-term shift in weather patterns."}
                    ]
                }
            }
        })

        mock_stream = Mock()
        mock_stream.read.return_value = mock_response_body.encode()
        mock_boto3.return_value.invoke_model.return_value = {"body": mock_stream}

        response = await model.generate_response(
            query="What is climate change?",
            documents=sample_documents
        )

        assert isinstance(response, str)
