import pytest
from unittest.mock import Mock, patch
from src.models.gen_response_nova import doc_preprocessing, cohere_chat

@pytest.fixture
def sample_docs():
    return [
        {
            'title': 'Climate Change Overview',
            'content': 'Climate change refers to long-term shifts in temperatures and weather patterns.',
            'url': ['http://example.com/climate']
        },
        {
            'title': 'Global Warming Effects',
            'chunk_text': 'Global warming leads to rising sea levels and extreme weather.',
            'url': 'http://example.com/effects'
        }
    ]

@pytest.fixture
def mock_cohere_client():
    class MockMessage:
        def __init__(self):
            self.content = "Based on the provided documents, climate change is a significant environmental phenomenon."
            self.citations = [
                {"start": 0, "end": 50, "text": "Climate change refers to long-term shifts in temperatures"},
                {"start": 51, "end": 100, "text": "Rising sea levels are a major concern"}
            ]

    class MockResponse:
        def __init__(self):
            self.message = MockMessage()

    mock = Mock()
    mock.chat.return_value = MockResponse()
    return mock

def test_doc_preprocessing_success(sample_docs):
    processed_docs = doc_preprocessing(sample_docs)
    
    assert len(processed_docs) == 2
    assert all('data' in doc for doc in processed_docs)
    
    first_doc = processed_docs[0]['data']
    assert 'title' in first_doc
    assert 'snippet' in first_doc
    assert 'http://example.com/climate' in first_doc['title']
    assert 'Climate change refers to' in first_doc['snippet']

def test_doc_preprocessing_missing_content():
    docs = [{'title': 'Test', 'url': ['http://example.com']}]
    processed = doc_preprocessing(docs)
    assert len(processed) == 0

def test_doc_preprocessing_short_content():
    docs = [{'title': 'Test', 'content': 'Too short', 'url': ['http://example.com']}]
    processed = doc_preprocessing(docs)
    assert len(processed) == 0

def test_doc_preprocessing_fallback_content(sample_docs):
    # Test that chunk_text is used when content is missing
    processed = doc_preprocessing([sample_docs[1]])
    assert len(processed) == 1
    assert 'Global warming leads to' in processed[0]['data']['snippet']

def test_doc_preprocessing_url_handling():
    docs = [
        {'title': 'Test1', 'content': 'Long enough content 1 that will pass the length check', 'url': ['http://test1.com']},
        {'title': 'Test2', 'content': 'Long enough content 2 that will pass the length check', 'url': 'http://test2.com'},
        {'title': 'Test3', 'content': 'Long enough content 3 that will pass the length check', 'url': []}
    ]
    processed = doc_preprocessing(docs)
    
    assert 'http://test1.com' in processed[0]['data']['title']
    assert 'http://test2.com' in processed[1]['data']['title']
    assert 'Test3' in processed[2]['data']['title']

def test_cohere_chat_success(sample_docs, mock_cohere_client):
    response, citations = cohere_chat(
        query="What is climate change?",
        documents=sample_docs,
        cohere_client=mock_cohere_client
    )
    
    assert isinstance(response, str)
    assert isinstance(citations, list)
    assert "climate change is a significant" in response
    assert len(citations) == 2
    mock_cohere_client.chat.assert_called_once()

def test_cohere_chat_no_documents(mock_cohere_client):
    with pytest.raises(ValueError, match="No valid documents to process"):
        cohere_chat(
            query="test query",
            documents=[],
            cohere_client=mock_cohere_client
        )

def test_cohere_chat_api_error(sample_docs, mock_cohere_client):
    mock_cohere_client.chat.side_effect = Exception("Error in response generation")
    
    with pytest.raises(Exception, match="Error in response generation"):
        cohere_chat(
            query="test query",
            documents=sample_docs,
            cohere_client=mock_cohere_client
        )

def test_cohere_chat_custom_description(sample_docs, mock_cohere_client):
    custom_desc = "Provide a technical response"
    cohere_chat(
        query="What is climate change?",
        documents=sample_docs,
        cohere_client=mock_cohere_client,
        description=custom_desc
    )
    
    # Verify custom description was used in the chat call
    call_args = mock_cohere_client.chat.call_args[1]
    messages = call_args['messages']
    assert any(custom_desc in str(msg.get('content', '')) for msg in messages)