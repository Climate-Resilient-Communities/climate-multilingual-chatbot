import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.models.gen_response_nova import doc_preprocessing, generate_chat_response


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
def mock_model():
    mock = Mock()
    mock.generate_response = AsyncMock(
        return_value="Based on the provided documents, climate change is a significant environmental phenomenon."
    )
    return mock


def test_doc_preprocessing_success(sample_docs):
    processed_docs = doc_preprocessing(sample_docs)

    assert len(processed_docs) == 2
    assert all(isinstance(doc, dict) for doc in processed_docs)

    first_doc = processed_docs[0]
    assert 'title' in first_doc
    assert 'content' in first_doc
    assert 'url' in first_doc
    assert 'Climate change refers to' in first_doc['content']


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


def test_doc_preprocessing_url_handling():
    docs = [
        {'title': 'Test1', 'content': 'Long enough content 1 that will pass the length check', 'url': ['http://test1.com']},
        {'title': 'Test2', 'content': 'Long enough content 2 that will pass the length check', 'url': 'http://test2.com'},
        {'title': 'Test3', 'content': 'Long enough content 3 that will pass the length check', 'url': []}
    ]
    processed = doc_preprocessing(docs)

    assert len(processed) == 3
    assert processed[0]['url'] == 'http://test1.com'
    assert processed[1]['url'] == 'http://test2.com'
    assert processed[2]['url'] == ''


@pytest.mark.asyncio
async def test_generate_chat_response_success(sample_docs, mock_model):
    response, citations = await generate_chat_response(
        query="What is climate change?",
        documents=sample_docs,
        model=mock_model
    )

    assert isinstance(response, str)
    assert isinstance(citations, list)
    mock_model.generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_generate_chat_response_no_documents(mock_model):
    with pytest.raises(ValueError, match="No valid documents to process"):
        await generate_chat_response(
            query="test query",
            documents=[],
            model=mock_model
        )


@pytest.mark.asyncio
async def test_generate_chat_response_api_error(sample_docs, mock_model):
    mock_model.generate_response = AsyncMock(side_effect=Exception("API Error"))

    with pytest.raises(Exception):
        await generate_chat_response(
            query="test query",
            documents=sample_docs,
            model=mock_model
        )


@pytest.mark.asyncio
async def test_generate_chat_response_custom_description(sample_docs, mock_model):
    custom_desc = "Provide a technical response"
    await generate_chat_response(
        query="What is climate change?",
        documents=sample_docs,
        model=mock_model,
        description=custom_desc
    )

    # Verify description was passed to generate_response
    call_args = mock_model.generate_response.call_args
    assert call_args[1].get('description') == custom_desc
