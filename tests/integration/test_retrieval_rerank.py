import pytest
import os
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import cohere
from pinecone import Pinecone
from src.models.retrieval import get_documents
from src.utils.env_loader import load_environment


def _make_pinecone_match(id, score, metadata):
    """Create a mock Pinecone match object with attribute access."""
    match = MagicMock()
    match.id = id
    match.score = score
    match.metadata = metadata  # Pinecone metadata supports .get() via real dict
    match.values = [0.1] * 1024  # dummy dense vector
    return match


def _make_query_response(matches):
    """Create a mock Pinecone QueryResponse with .matches attribute."""
    response = MagicMock()
    response.matches = matches
    return response


@pytest.fixture
def mock_matches():
    return [
        _make_pinecone_match("1", 0.95, {
            'title': 'Climate Change Overview',
            'chunk_text': 'Climate change refers to long-term shifts in global weather patterns.',
            'section_title': 'Introduction',
            'segment_id': '1',
            'doc_keywords': ['climate', 'change'],
            'segment_keywords': ['introduction'],
            'url': ['http://example.com/climate']
        }),
        _make_pinecone_match("2", 0.85, {
            'title': 'Global Warming Effects',
            'chunk_text': 'Global warming leads to rising sea levels and extreme weather.',
            'section_title': 'Effects',
            'segment_id': '2',
            'doc_keywords': ['global', 'warming'],
            'segment_keywords': ['effects'],
            'url': ['http://example.com/effects']
        }),
    ]

@pytest.fixture
def mock_index(mock_matches):
    mock = Mock()
    mock.query.return_value = _make_query_response(mock_matches)
    return mock

@pytest.fixture
def mock_embed_model():
    mock = Mock()
    # Mock the encode method to return dict matching HFEmbedder.encode() format
    mock.encode.return_value = {
        'dense_vecs': np.array([[0.1] * 1024], dtype=np.float32),
        'lexical_weights': [{}],
    }
    return mock

def _make_rerank_result(index, relevance_score):
    """Create a mock Cohere rerank result with attribute access (.index, .relevance_score)."""
    result = Mock()
    result.index = index
    result.relevance_score = relevance_score
    return result


@pytest.fixture
def mock_cohere_client():
    mock_client = Mock()
    rerank_response = Mock()
    rerank_response.results = [
        _make_rerank_result(index=1, relevance_score=0.98),
        _make_rerank_result(index=0, relevance_score=0.75),
    ]
    mock_client.rerank.return_value = rerank_response
    return mock_client

@pytest.mark.asyncio
async def test_end_to_end_retrieval_and_rerank(mock_index, mock_cohere_client, mock_embed_model):
    # Test the entire retrieval and reranking pipeline
    query = "What are the effects of global warming?"

    docs = await get_documents(
        query=query,
        index=mock_index,
        embed_model=mock_embed_model,
        cohere_client=mock_cohere_client
    )

    assert len(docs) == 2

    # Verify documents were reranked (order should be swapped due to mock rerank scores)
    assert docs[0]['title'] == 'Global Warming Effects'  # Higher rerank score
    assert docs[0]['score'] == 0.98
    assert docs[1]['title'] == 'Climate Change Overview'  # Lower rerank score
    assert docs[1]['score'] == 0.75

    # Verify content was cleaned and processed
    assert 'Global warming leads to rising sea levels' in docs[0]['content']
    assert 'climate' in docs[1]['doc_keywords']

@pytest.mark.asyncio
async def test_retrieval_with_no_results(mock_index, mock_cohere_client, mock_embed_model):
    # Test handling of no search results
    mock_index.query.return_value = _make_query_response([])

    docs = await get_documents(
        query="query with no matches",
        index=mock_index,
        embed_model=mock_embed_model,
        cohere_client=mock_cohere_client
    )

    assert len(docs) == 0

@pytest.mark.asyncio
async def test_retrieval_with_rerank_error(mock_index, mock_cohere_client, mock_embed_model):
    # Test handling of reranking errors
    mock_cohere_client.rerank.side_effect = Exception("Reranking failed")

    # Should still return processed documents even if reranking fails
    docs = await get_documents(
        query="test query",
        index=mock_index,
        embed_model=mock_embed_model,
        cohere_client=mock_cohere_client
    )

    assert len(docs) == 2
    # Original order and scores should be preserved
    assert docs[0]['title'] == 'Climate Change Overview'
    assert docs[0]['score'] == 0.95
