import pytest
from unittest.mock import Mock, patch
import json
from src.models.nova_generation import NovaChat, default_persona_prompt

@pytest.fixture
def mock_bedrock_client():
    mock = Mock()
    return mock

@pytest.fixture
def mock_response():
    class MockMessage:
        def __init__(self):
            self.content = [{"text": "Climate change is a long-term shift in weather patterns."}]

    class MockOutput:
        def __init__(self):
            self.message = MockMessage()

    class MockResponse:
        def read(self):
            return json.dumps({
                "output": {
                    "message": {
                        "content": [
                            {"text": "Climate change is a long-term shift in weather patterns."}
                        ]
                    }
                }
            })
    
    return {"body": MockResponse()}

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

@pytest.fixture
def nova_chat_instance(mock_bedrock_client):
    with patch('boto3.client', return_value=mock_bedrock_client):
        chat = NovaChat()
        return chat

def test_initialization():
    with patch('boto3.client') as mock_boto3:
        chat = NovaChat(model_id="test-model", region_name="test-region")
        mock_boto3.assert_called_once()
        assert chat.model_id == "test-model"

def test_nova_chat_success(nova_chat_instance, mock_bedrock_client, mock_response, sample_documents):
    mock_bedrock_client.invoke_model.return_value = mock_response
    
    response, citations = nova_chat_instance.nova_chat(
        query="What is climate change?",
        documents=sample_documents
    )
    
    assert isinstance(response, str)
    assert isinstance(citations, list)
    assert "Climate change is a long-term shift" in response
    mock_bedrock_client.invoke_model.assert_called_once()
    
    # Verify payload structure
    call_args = mock_bedrock_client.invoke_model.call_args[1]
    payload = json.loads(call_args["body"])
    assert "messages" in payload
    # Check if the first message contains the persona prompt
    first_message = payload["messages"][0]
    assert first_message["role"] == "user"
    assert isinstance(first_message["content"], list)
    assert "expert educator on climate change" in first_message["content"][0]["text"]

def test_nova_chat_with_custom_persona(nova_chat_instance, mock_bedrock_client, mock_response, sample_documents):
    mock_bedrock_client.invoke_model.return_value = mock_response
    custom_persona = "You are a climate scientist."
    
    nova_chat_instance.nova_chat(
        query="What is climate change?",
        documents=sample_documents,
        persona_prompt=custom_persona
    )
    
    call_args = mock_bedrock_client.invoke_model.call_args[1]
    payload = json.loads(call_args["body"])
    assert any(custom_persona in str(msg.get('content', '')) for msg in payload["messages"])

def test_nova_chat_with_description(nova_chat_instance, mock_bedrock_client, mock_response, sample_documents):
    mock_bedrock_client.invoke_model.return_value = mock_response
    description = "Provide a technical explanation"
    
    nova_chat_instance.nova_chat(
        query="What is climate change?",
        documents=sample_documents,
        description=description
    )
    
    call_args = mock_bedrock_client.invoke_model.call_args[1]
    payload = json.loads(call_args["body"])
    assert any(description in str(msg.get('content', '')) for msg in payload["messages"])

def test_nova_chat_api_error(nova_chat_instance, mock_bedrock_client, sample_documents):
    mock_bedrock_client.invoke_model.side_effect = Exception("API Error")
    
    with pytest.raises(RuntimeError) as exc_info:
        nova_chat_instance.nova_chat(
            query="What is climate change?",
            documents=sample_documents
        )
    
    assert "An error occurred while invoking the model" in str(exc_info.value)

def test_nova_chat_empty_documents(nova_chat_instance, mock_bedrock_client, mock_response):
    mock_bedrock_client.invoke_model.return_value = mock_response
    
    with pytest.raises(ValueError, match="No documents were provided"):
        nova_chat_instance.nova_chat(
            query="What is climate change?",
            documents=[]
        )