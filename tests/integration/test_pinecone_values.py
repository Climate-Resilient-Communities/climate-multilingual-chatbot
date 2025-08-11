import os
import pytest


def _live_only():
    if str(os.getenv("RUN_LIVE", "")).strip().lower() not in ("1", "true", "yes"):
        pytest.skip("RUN_LIVE not set; skipping live Pinecone test")


@pytest.mark.integration
def test_pinecone_include_values_returns_vectors():
    """Live check: verify Pinecone returns vectors when include_values=True."""
    _live_only()

    from src.utils.env_loader import load_environment
    load_environment()

    api_key = os.getenv("PINECONE_API_KEY")
    assert api_key, "PINECONE_API_KEY not set"

    # Determine index name
    try:
        from src.data.config.config import RETRIEVAL_CONFIG
        index_name = RETRIEVAL_CONFIG.get("pinecone_index")
    except Exception:
        index_name = None
    index_name = index_name or os.getenv("PINECONE_INDEX")
    assert index_name, "Pinecone index name not configured (RETRIEVAL_CONFIG.pinecone_index or PINECONE_INDEX)"

    # Connect to Pinecone
    from pinecone import Pinecone
    pc = Pinecone(api_key=api_key)
    try:
        index = pc.Index(index_name)
    except Exception as e:
        pytest.skip(f"Index '{index_name}' not available: {e}")

    # Build a query vector and sparse weights using the same embedder as the app
    from FlagEmbedding import BGEM3FlagModel
    from src.models.retrieval import get_query_embeddings

    embed_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=False)
    q_dense, q_sparse_list = get_query_embeddings("climate change impacts", embed_model)
    assert q_dense is not None and len(q_dense) > 0
    assert q_sparse_list and isinstance(q_sparse_list[0], dict)
    q_sparse = q_sparse_list[0]

    # Live query with include_values=True
    # Convert numpy arrays to lists for Pinecone serialization
    dense_vec = q_dense[0].tolist() if hasattr(q_dense[0], 'tolist') else list(q_dense[0])
    sparse_indices = q_sparse["indices"].tolist() if hasattr(q_sparse["indices"], 'tolist') else list(q_sparse["indices"])
    sparse_values = q_sparse["values"].tolist() if hasattr(q_sparse["values"], 'tolist') else list(q_sparse["values"])
    
    res = index.query(
        vector=dense_vec,
        sparse_vector={"indices": sparse_indices, "values": sparse_values},
        top_k=3,
        include_metadata=True,
        include_values=True,
    )

    assert hasattr(res, "matches"), "Pinecone response missing matches"
    assert res.matches, "No matches returned from Pinecone"

    # Check whether any match returns vector values
    first = res.matches[0]
    # Provide rich debug on failure
    attrs = dir(first)
    has_values_any = any(
        hasattr(m, "values") and isinstance(getattr(m, "values"), list) and len(getattr(m, "values")) > 0
        for m in res.matches
    )

    # Log the actual structure for debugging
    print(f"\n=== PINECONE RESPONSE DEBUG ===")
    print(f"Number of matches: {len(res.matches)}")
    print(f"First match type: {type(first)}")
    print(f"First match attributes: {attrs}")
    print(f"First match dict: {first.__dict__ if hasattr(first, '__dict__') else 'no dict'}")
    if hasattr(first, 'values'):
        print(f"Values present: True, length: {len(first.values) if first.values else 0}")
        print(f"Values type: {type(first.values)}")
        print(f"First few values: {first.values[:5] if first.values else 'empty'}")
    else:
        print(f"Values present: False")
    print(f"=== END DEBUG ===\n")

    assert has_values_any, f"No vectors returned on matches; first attrs={attrs}"


