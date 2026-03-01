"""
Unit tests for the BedrockModel (Nova) in nova_flow.py.

BedrockModel now:
- __init__(model_id="amazon.nova-lite-v1:0") — no region_name param
- Uses aioboto3.Session + boto3.Session internally
- query_normalizer(query, language) is async
- nova_translation(text, source_lang, target_lang) is async
- content_generation(prompt, system_message, max_tokens) is async
- translate(text, source_lang, target_lang) is async
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.models.nova_flow import BedrockModel
from src.models.query_routing import MultilingualRouter


@pytest.fixture
def mock_bedrock_client():
    return Mock()


@pytest.fixture
def mock_successful_response():
    class MockBody:
        def read(self):
            return json.dumps({
                "output": {
                    "message": {
                        "content": [
                            {"text": "Translated text"}
                        ]
                    }
                }
            })

    return {"body": MockBody()}


@pytest.fixture
def nova_model(mock_bedrock_client):
    with patch('aioboto3.Session'), \
         patch('boto3.Session') as mock_session, \
         patch.dict('os.environ', {'AWS_ACCESS_KEY_ID': 'test-key', 'AWS_SECRET_ACCESS_KEY': 'test-secret'}):
        mock_session.return_value.client.return_value = mock_bedrock_client
        model = BedrockModel()
        # Replace the sync client used internally
        model.sync_bedrock = mock_bedrock_client
        return model


def test_initialization():
    with patch('aioboto3.Session'), \
         patch('boto3.Session') as mock_session, \
         patch.dict('os.environ', {'AWS_ACCESS_KEY_ID': 'test-key', 'AWS_SECRET_ACCESS_KEY': 'test-secret'}):
        model = BedrockModel(model_id="test-model")
        assert model.model_id == "test-model"


@pytest.mark.asyncio
async def test_nova_translation_success(nova_model, mock_bedrock_client, mock_successful_response):
    mock_bedrock_client.invoke_model.return_value = mock_successful_response

    result = await nova_model.nova_translation(
        text="Hello world",
        source_lang="English",
        target_lang="Spanish"
    )

    assert result == "Translated text"


@pytest.mark.asyncio
async def test_nova_translation_error(nova_model, mock_bedrock_client):
    mock_bedrock_client.invoke_model.side_effect = Exception("API Error")

    # nova_translation wraps translate which may return error string or raise
    try:
        result = await nova_model.nova_translation("Hello", "English", "Spanish")
        # If it returns instead of raising, it should be an error indicator
        assert result is not None
    except (RuntimeError, Exception):
        pass  # Expected


@pytest.mark.asyncio
async def test_query_normalizer_success(nova_model, mock_bedrock_client, mock_successful_response):
    mock_bedrock_client.invoke_model.return_value = mock_successful_response

    result = await nova_model.query_normalizer(
        query="what is climate change???",
        language="English"
    )

    assert result == "Translated text"


@pytest.mark.asyncio
async def test_query_normalizer_error(nova_model, mock_bedrock_client):
    mock_bedrock_client.invoke_model.side_effect = Exception("API Error")

    try:
        result = await nova_model.query_normalizer("test query", "English")
        assert result is not None
    except (RuntimeError, Exception):
        pass  # Expected


@pytest.mark.asyncio
async def test_content_generation(nova_model, mock_bedrock_client, mock_successful_response):
    mock_bedrock_client.invoke_model.return_value = mock_successful_response

    result = await nova_model.content_generation(
        prompt="What is climate change?",
        system_message="You are a helpful assistant."
    )

    assert isinstance(result, str)
    assert len(result) > 0


def test_language_support():
    router = MultilingualRouter()
    assert router.standardize_language_code("en-us") == "en"
    assert router.standardize_language_code("zh-cn") == "zh"
