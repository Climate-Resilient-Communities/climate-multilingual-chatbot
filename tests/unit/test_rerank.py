import pytest
import os
from unittest.mock import Mock, patch
from src.models.rerank import prepare_docs_for_rerank, rerank_fcn

@pytest.fixture
def sample_docs():
    return [
        {
            'title': 'Test Document 1',
            'content': 'This is some test content about climate change.',
            'url': ['http://example.com/1'],
            'score': 0.95,
            'section_title': 'Introduction',
            'segment_id': '1',
            'doc_keywords': ['climate', 'change'],
            'segment_keywords': ['test']
        },
        {
            'title': 'Test Document 2',
            'content': 'More test content about global warming.',
            'url': ['http://example.com/2'],
            'score': 0.85,
            'section_title': 'Effects',
            'segment_id': '2',
            'doc_keywords': ['global', 'warming'],
            'segment_keywords': ['effects']
        }
    ]

@pytest.fixture
def mock_cohere_client():
    mock_client = Mock()
    mock_client.rerank.return_value = {
        'results': [
            {
                'index': 0,
                'relevance_score': 0.98,
                'document': {'text': 'This is some test content about climate change.'}
            },
            {
                'index': 1,
                'relevance_score': 0.75,
                'document': {'text': 'More test content about global warming.'}
            }
        ]
    }
    return mock_client

def test_prepare_docs_for_rerank(sample_docs):
    # Test document preparation
    prepared_docs = prepare_docs_for_rerank(sample_docs)
    
    assert len(prepared_docs) == 2
    assert prepared_docs[0]['text'] == 'This is some test content about climate change.'
    assert prepared_docs[0]['title'] == 'Test Document 1'
    assert prepared_docs[0]['url'] == 'http://example.com/1'
    assert prepared_docs[0]['original'] == sample_docs[0]

def test_prepare_docs_for_rerank_empty_content():
    # Test handling of empty content
    docs = [{'title': 'Empty Doc', 'content': '', 'url': ['http://example.com']}]
    prepared_docs = prepare_docs_for_rerank(docs)
    assert len(prepared_docs) == 0

def test_prepare_docs_for_rerank_missing_fields():
    # Test handling of missing fields
    docs = [{'content': 'Some content'}]
    prepared_docs = prepare_docs_for_rerank(docs)
    assert len(prepared_docs) == 1
    assert prepared_docs[0]['title'] == 'No Title'
    assert prepared_docs[0]['url'] == ''

@pytest.mark.asyncio
async def test_rerank_fcn(sample_docs, mock_cohere_client):
    # Test reranking functionality
    query = "climate change effects"
    reranked_docs = rerank_fcn(query, sample_docs, 2, mock_cohere_client)
    
    assert len(reranked_docs) == 2
    assert reranked_docs[0]['score'] == 0.98
    assert reranked_docs[1]['score'] == 0.75
    
    # Verify cohere client was called correctly
    mock_cohere_client.rerank.assert_called_once_with(
        query=query,
        documents=['This is some test content about climate change.',
                  'More test content about global warming.'],
        top_n=2,
        model="rerank-multilingual-v3.0"
    )

@pytest.mark.asyncio
async def test_rerank_fcn_empty_docs(mock_cohere_client):
    # Test reranking with empty document list
    reranked_docs = rerank_fcn("test query", [], 5, mock_cohere_client)
    assert len(reranked_docs) == 0
    assert not mock_cohere_client.rerank.called

@pytest.mark.asyncio
async def test_rerank_fcn_cohere_error(sample_docs):
    # Test handling of Cohere API error
    mock_client = Mock()
    mock_client.rerank.side_effect = Exception("API Error")
    
    # Should return top_k original docs when reranking fails
    reranked_docs = rerank_fcn("test query", sample_docs, 2, mock_client)
    assert len(reranked_docs) == 2
    assert reranked_docs[0]['score'] == 0.95  # Original scores preserved