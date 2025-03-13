import pytest
from unittest.mock import Mock, patch
from src.models.gen_response_nova import (
    nova_chat,
    doc_preprocessing,
    process_single_doc,
    generate_cache_key
)

@pytest.fixture
def sample_docs():
    return [
        {
            'title': 'Climate Change Overview',
            'content': 'Climate change is a long-term shift in global weather patterns.',
            'url': ['http://example.com/climate']
        },
        {
            'title': 'Global Warming Effects',
            'chunk_text': 'Global warming leads to rising sea levels.',
            'url': 'http://example.com/effects'
        }
    ]

@pytest.fixture
def mock_nova_client():
    mock = Mock()
    mock.nova_chat.return_value = ("Test response about climate change", ["citation1"])
    return mock

def test_doc_preprocessing_success(sample_docs):
    processed_docs = doc_preprocessing(sample_docs)
    
    assert len(processed_docs) == 2
    assert all(isinstance(doc, dict) for doc in processed_docs)
    
    first_doc = processed_docs[0]
    assert 'title' in first_doc
    assert 'content' in first_doc
    assert 'url' in first_doc
    assert 'Climate change is' in first_doc['content']

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
    assert 'Global warming leads to' in processed[0]['content']

def test_generate_cache_key():
    docs = [
        {'title': 'Doc1', 'url': 'url1'},
        {'title': 'Doc2', 'url': 'url2'}
    ]
    key1 = generate_cache_key("test query", docs)
    key2 = generate_cache_key("test query", docs)
    
    # Same inputs should generate same key
    assert key1 == key2
    # Different query should generate different key
    assert key1 != generate_cache_key("different query", docs)

@pytest.mark.asyncio
async def test_nova_chat_success(sample_docs, mock_nova_client):
    response, citations = await nova_chat(
        query="What is climate change?",
        documents=sample_docs,
        nova_client=mock_nova_client
    )
    
    assert isinstance(response, str)
    assert isinstance(citations, list)
    assert "Test response" in response
    assert citations == ["citation1"]
    mock_nova_client.nova_chat.assert_called_once()

@pytest.mark.asyncio
async def test_nova_chat_no_documents(mock_nova_client):
    with pytest.raises(ValueError, match="No valid documents to process"):
        await nova_chat(
            query="test query",
            documents=[],
            nova_client=mock_nova_client
        )

@pytest.mark.asyncio
async def test_nova_chat_with_description(sample_docs, mock_nova_client):
    custom_desc = "Provide a technical response"
    await nova_chat(
        query="What is climate change?",
        documents=sample_docs,
        nova_client=mock_nova_client,
        description=custom_desc
    )
    
    # Verify description was passed to nova_chat
    call_args = mock_nova_client.nova_chat.call_args[1]
    assert call_args['description'] == custom_desc

@pytest.mark.asyncio
async def test_nova_chat_api_error(sample_docs, mock_nova_client):
    mock_nova_client.nova_chat.side_effect = Exception("API Error")
    
    with pytest.raises(Exception):
        await nova_chat(
            query="test query",
            documents=sample_docs,
            nova_client=mock_nova_client
        )