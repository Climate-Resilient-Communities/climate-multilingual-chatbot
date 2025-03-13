import pytest
import os
import cohere
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from src.utils.env_loader import load_environment
from src.models.retrieval import get_documents

@pytest.fixture(scope="module")
def embed_model():
    return SentenceTransformer('BAAI/bge-large-en-v1.5')

@pytest.fixture(scope="module")
def pinecone_index():
    load_environment()
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    if not PINECONE_API_KEY:
        pytest.skip("PINECONE_API_KEY not found in environment")
    
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index("climate-change-adaptation-index-10-24-prod")

@pytest.fixture(scope="module")
def cohere_client():
    load_environment()
    COHERE_API_KEY = os.getenv('COHERE_API_KEY')
    if not COHERE_API_KEY:
        pytest.skip("COHERE_API_KEY not found in environment")
    
    return cohere.Client(COHERE_API_KEY)

@pytest.mark.system
@pytest.mark.asyncio
async def test_climate_change_query(pinecone_index, embed_model, cohere_client):
    """Test retrieval and reranking with a climate change query."""
    query = "What are the main causes of climate change?"
    
    docs = await get_documents(
        query=query,
        index=pinecone_index,
        embed_model=embed_model,
        cohere_client=cohere_client
    )
    
    assert len(docs) > 0, "Should return at least one document"
    assert all('title' in doc for doc in docs), "All documents should have titles"
    assert all('content' in doc for doc in docs), "All documents should have content"
    assert all('score' in doc for doc in docs), "All documents should have relevance scores"
    
    # Verify scores are properly ordered
    scores = [doc['score'] for doc in docs]
    assert scores == sorted(scores, reverse=True), "Documents should be sorted by relevance score"

@pytest.mark.system
@pytest.mark.asyncio
async def test_adaptation_strategies_query(pinecone_index, embed_model, cohere_client):
    """Test retrieval and reranking with an adaptation strategies query."""
    query = "What are effective climate change adaptation strategies?"
    
    docs = await get_documents(
        query=query,
        index=pinecone_index,
        embed_model=embed_model,
        cohere_client=cohere_client
    )
    
    assert len(docs) > 0, "Should return at least one document"
    assert any('adaptation' in doc['content'].lower() for doc in docs), \
        "At least one document should mention adaptation"

@pytest.mark.system
@pytest.mark.asyncio
async def test_irrelevant_query(pinecone_index, embed_model, cohere_client):
    """Test retrieval with an irrelevant query."""
    query = "What is the recipe for chocolate chip cookies?"
    
    docs = await get_documents(
        query=query,
        index=pinecone_index,
        embed_model=embed_model,
        cohere_client=cohere_client
    )
    
    if docs:
        # If documents are returned, their scores should be relatively low
        assert all(doc['score'] < 0.5 for doc in docs), \
            "Irrelevant queries should have low relevance scores"