import pytest
from unittest.mock import Mock, patch
import json
from src.models.nova_flow import BedrockModel
from src.models.query_routing import MultilingualRouter

@pytest.fixture
def mock_bedrock_client():
    mock = Mock()
    return mock

@pytest.fixture
def mock_successful_response():
    class MockResponse:
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
    
    return {"body": MockResponse()}

@pytest.fixture
def nova_model(mock_bedrock_client):
    with patch('boto3.client', return_value=mock_bedrock_client), \
         patch.dict('os.environ', {'AWS_ACCESS_KEY_ID': 'test-key', 'AWS_SECRET_ACCESS_KEY': 'test-secret'}):
        model = BedrockModel()
        return model

def test_initialization():
    with patch('boto3.client') as mock_boto3, \
         patch.dict('os.environ', clear=True):  # Clear env vars for this test
        model = BedrockModel(model_id="test-model", region_name="test-region")
        
        mock_boto3.assert_called_once_with(
            'bedrock-runtime',
            region_name="test-region",
            aws_access_key_id=None,
            aws_secret_access_key=None
        )
        assert model.model_id == "test-model"

def test_nova_translation_success(nova_model, mock_bedrock_client, mock_successful_response):
    mock_bedrock_client.invoke_model.return_value = mock_successful_response
    
    result = nova_model.nova_translation(
        input_text="Hello world",
        input_language="English",
        output_language="Spanish"
    )
    
    assert result == "Translated text"
    mock_bedrock_client.invoke_model.assert_called_once()
    
    # Verify the payload structure
    call_args = mock_bedrock_client.invoke_model.call_args[1]
    assert call_args["modelId"] == "amazon.nova-lite-v1:0"
    assert call_args["contentType"] == "application/json"
    assert call_args["accept"] == "application/json"
    
    payload = json.loads(call_args["body"])
    assert "messages" in payload
    assert "inferenceConfig" in payload

def test_nova_translation_error(nova_model, mock_bedrock_client):
    mock_bedrock_client.invoke_model.side_effect = Exception("API Error")
    
    with pytest.raises(RuntimeError) as exc_info:
        nova_model.nova_translation("Hello", "English", "Spanish")
    
    assert "Error invoking model" in str(exc_info.value)

def test_query_normalizer_success(nova_model, mock_bedrock_client, mock_successful_response):
    mock_bedrock_client.invoke_model.return_value = mock_successful_response
    
    result = nova_model.query_normalizer(
        query="what is climate change???",
        language_name="English"
    )
    
    assert result == "Translated text"
    mock_bedrock_client.invoke_model.assert_called_once()
    
    # Verify the payload structure
    call_args = mock_bedrock_client.invoke_model.call_args[1]
    payload = json.loads(call_args["body"])
    assert "messages" in payload
    assert "inferenceConfig" in payload
    assert payload["inferenceConfig"]["maxTokens"] == 1000
    assert payload["inferenceConfig"]["temperature"] == 0.7

def test_query_normalizer_error(nova_model, mock_bedrock_client):
    mock_bedrock_client.invoke_model.side_effect = Exception("API Error")
    
    with pytest.raises(RuntimeError) as exc_info:
        nova_model.query_normalizer("test query", "English")
    
    assert "Error invoking model" in str(exc_info.value)

def test_custom_parameters(nova_model, mock_bedrock_client, mock_successful_response):
    mock_bedrock_client.invoke_model.return_value = mock_successful_response
    
    result = nova_model.query_normalizer(
        query="test query",
        language_name="English",
        max_tokens=500,
        temperature=0.5
    )
    
    call_args = mock_bedrock_client.invoke_model.call_args[1]
    payload = json.loads(call_args["body"])
    assert payload["inferenceConfig"]["maxTokens"] == 500
    assert payload["inferenceConfig"]["temperature"] == 0.5

def test_language_support():
    router = MultilingualRouter()
    assert router.standardize_language_code("en-us") == "en"
    assert router.standardize_language_code("zh-cn") == "zh"

@pytest.mark.asyncio
async def test_query_normalization():
    model = BedrockModel()
    test_query = "What is climate change?"
    normalized = model.query_normalizer(test_query, "english")
    assert isinstance(normalized, str)
    assert len(normalized) > 0

# Add more tests as needed