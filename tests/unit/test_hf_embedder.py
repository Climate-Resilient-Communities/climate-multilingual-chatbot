"""
Unit tests for HFEmbedder — BGE-M3 embeddings via HuggingFace Inference API.

All HuggingFace API calls are mocked so these tests run without network access.

NOTE: test_app_nova_session_init.py injects stubs for numpy/tqdm into
sys.modules. This corrupts later imports of these modules. To work around
this, encode/batching tests create HFEmbedder instances via object.__new__()
and patch the numpy import inside encode() to use the real numpy captured
at test-module load time.
"""

import sys
import pytest
import numpy as _real_np  # capture real numpy before any test can corrupt it
import tqdm as _real_tqdm  # capture real tqdm before any test can corrupt it
from unittest.mock import patch, MagicMock
from src.models.cohere_flow import HFEmbedder


def _make_embedder_with_mock_client():
    """Create an HFEmbedder without calling __init__ (avoids huggingface_hub import).

    Sets up the minimum attributes needed for encode() to work.
    Returns (embedder, mock_client).
    """
    emb = object.__new__(HFEmbedder)
    mock_client = MagicMock()
    emb.client = mock_client
    emb.model = HFEmbedder.EMBED_MODEL
    return emb, mock_client


# ──────────────────────────────────────────────────────────────
# Class-level constants (no init needed)
# ──────────────────────────────────────────────────────────────

class TestHFEmbedderConstants:
    """Test HFEmbedder class-level configuration."""

    def test_model_constants(self):
        """EMBED_MODEL and EMBED_DIM should match the BGE-M3 spec."""
        assert HFEmbedder.EMBED_MODEL == "BAAI/bge-m3"
        assert HFEmbedder.EMBED_DIM == 1024
        assert HFEmbedder._BATCH_SIZE == 32


# ──────────────────────────────────────────────────────────────
# Initialization (requires mocking huggingface_hub import)
# ──────────────────────────────────────────────────────────────

class TestHFEmbedderInit:
    """Test HFEmbedder initialization."""

    @pytest.fixture(autouse=True)
    def _protect_tqdm(self):
        """Ensure tqdm module is not corrupted by other tests."""
        saved_tqdm = sys.modules.get("tqdm")
        saved_tqdm_auto = sys.modules.get("tqdm.auto")
        sys.modules["tqdm"] = _real_tqdm
        # Restore tqdm.auto if it exists
        if hasattr(_real_tqdm, "auto"):
            sys.modules["tqdm.auto"] = _real_tqdm.auto
        yield
        if saved_tqdm is not None:
            sys.modules["tqdm"] = saved_tqdm
        if saved_tqdm_auto is not None:
            sys.modules["tqdm.auto"] = saved_tqdm_auto

    @patch("huggingface_hub.InferenceClient")
    def test_init_uses_provided_api_key(self, mock_client_cls):
        """When an explicit api_key is passed, it should be used as the token."""
        embedder = HFEmbedder(api_key="test-token-123")
        mock_client_cls.assert_called_once_with(token="test-token-123")
        assert embedder.model == "BAAI/bge-m3"

    @patch.dict("os.environ", {"HF_TOKEN": "env-token"}, clear=False)
    @patch("huggingface_hub.InferenceClient")
    def test_init_falls_back_to_env_hf_token(self, mock_client_cls):
        """When no api_key is passed, HF_TOKEN env var should be used."""
        embedder = HFEmbedder()
        mock_client_cls.assert_called_once_with(token="env-token")


# ──────────────────────────────────────────────────────────────
# Encoding — shape and format
#
# These tests patch the local `import numpy as np` inside encode()
# to use the real numpy captured at module load time, avoiding
# sys.modules corruption from other tests.
# ──────────────────────────────────────────────────────────────

class TestHFEmbedderEncode:
    """Test the encode() method returns correct shapes and formats."""

    @pytest.fixture
    def embedder(self):
        emb, mock_client = _make_embedder_with_mock_client()
        emb._mock_client = mock_client
        return emb

    @pytest.fixture(autouse=True)
    def _protect_numpy(self):
        """Ensure encode() sees the real numpy even if sys.modules is corrupted."""
        import sys
        saved = sys.modules.get("numpy")
        sys.modules["numpy"] = _real_np
        yield
        if saved is not None:
            sys.modules["numpy"] = saved

    def test_encode_single_text(self, embedder):
        """Single text should return (1, 1024) dense_vecs."""
        fake_embedding = _real_np.random.rand(1, 1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_embedding

        result = embedder.encode("climate change is real")

        assert "dense_vecs" in result
        assert "lexical_weights" in result
        assert result["dense_vecs"].shape == (1, 1024)
        assert len(result["lexical_weights"]) == 1
        assert result["lexical_weights"][0] == {}

    def test_encode_multiple_texts(self, embedder):
        """Multiple texts should return (N, 1024) dense_vecs."""
        texts = ["climate change", "global warming", "sea level rise"]
        fake_embeddings = _real_np.random.rand(3, 1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_embeddings

        result = embedder.encode(texts)

        assert result["dense_vecs"].shape == (3, 1024)
        assert len(result["lexical_weights"]) == 3
        assert all(w == {} for w in result["lexical_weights"])

    def test_encode_string_auto_wraps_to_list(self, embedder):
        """A plain string should be auto-wrapped to a list."""
        fake_embedding = _real_np.random.rand(1, 1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_embedding

        result = embedder.encode("single query")

        embedder._mock_client.feature_extraction.assert_called_once()
        call_args = embedder._mock_client.feature_extraction.call_args
        assert isinstance(call_args[0][0], list)

    def test_encode_3d_response_cls_pooling(self, embedder):
        """When HF returns (batch, seq_len, dim), CLS token (index 0) should be taken."""
        fake_3d = _real_np.random.rand(2, 10, 1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_3d

        result = embedder.encode(["text1", "text2"])

        assert result["dense_vecs"].shape == (2, 1024)

    def test_encode_1d_response_reshaped(self, embedder):
        """When HF returns a flat 1D vector, it should be reshaped to (1, dim)."""
        fake_1d = _real_np.random.rand(1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_1d

        result = embedder.encode("single text")

        assert result["dense_vecs"].shape == (1, 1024)

    def test_encode_dtype_is_float32(self, embedder):
        """Dense vectors should be float32 for Pinecone compatibility."""
        fake_embedding = _real_np.random.rand(1, 1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_embedding

        result = embedder.encode("test")

        assert result["dense_vecs"].dtype == _real_np.float32


# ──────────────────────────────────────────────────────────────
# Batching
# ──────────────────────────────────────────────────────────────

class TestHFEmbedderBatching:
    """Test that large inputs are batched correctly."""

    @pytest.fixture
    def embedder(self):
        emb, mock_client = _make_embedder_with_mock_client()
        emb._mock_client = mock_client
        return emb

    @pytest.fixture(autouse=True)
    def _protect_numpy(self):
        """Ensure encode() sees the real numpy even if sys.modules is corrupted."""
        import sys
        saved = sys.modules.get("numpy")
        sys.modules["numpy"] = _real_np
        yield
        if saved is not None:
            sys.modules["numpy"] = saved

    def test_batch_splitting(self, embedder):
        """Texts exceeding _BATCH_SIZE should be split into multiple API calls."""
        n_texts = 50
        texts = [f"text {i}" for i in range(n_texts)]

        def fake_feature_extraction(batch, model=None):
            return _real_np.random.rand(len(batch), 1024).tolist()

        embedder._mock_client.feature_extraction.side_effect = fake_feature_extraction

        result = embedder.encode(texts)

        assert result["dense_vecs"].shape == (n_texts, 1024)
        assert len(result["lexical_weights"]) == n_texts
        assert embedder._mock_client.feature_extraction.call_count == 2

    def test_exact_batch_size_single_call(self, embedder):
        """Exactly _BATCH_SIZE texts should result in exactly 1 API call."""
        n_texts = 32
        texts = [f"text {i}" for i in range(n_texts)]
        fake_embeddings = _real_np.random.rand(n_texts, 1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_embeddings

        result = embedder.encode(texts)

        assert embedder._mock_client.feature_extraction.call_count == 1
        assert result["dense_vecs"].shape == (32, 1024)

    def test_uses_correct_model_param(self, embedder):
        """feature_extraction should be called with model=BAAI/bge-m3."""
        fake_embedding = _real_np.random.rand(1, 1024).tolist()
        embedder._mock_client.feature_extraction.return_value = fake_embedding

        embedder.encode("test")

        call_kwargs = embedder._mock_client.feature_extraction.call_args
        assert call_kwargs[1]["model"] == "BAAI/bge-m3"
