"""
Unit tests for UnifiedResponseGenerator — verifies model propagation fix.

The Codex finding: pipeline calls `self.cohere_model.with_model(model_id)` to
route to a regional Tiny-Aya model, but UnifiedResponseGenerator was ignoring
this and always using its own internal CohereModel (tiny-aya-global).

The fix adds an optional `model=` parameter to `generate_response()` so the
pipeline can pass the routed model directly.

All LLM calls are mocked — no network access required.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models.gen_response_unified import UnifiedResponseGenerator


@pytest.fixture
def generator():
    """Create a UnifiedResponseGenerator with mocked internals."""
    with patch("src.models.gen_response_unified.BedrockModel"), \
         patch("src.models.gen_response_unified.CohereModel"):
        gen = UnifiedResponseGenerator()
        # Give mock models identifiable model_id attributes
        gen.nova_model.model_id = "nova-lite"
        gen.cohere_model.model_id = "tiny-aya-global"
        return gen


@pytest.fixture
def sample_docs():
    return [
        {
            "title": "Climate Change Overview",
            "content": "Climate change refers to long-term shifts in temperatures and weather patterns, primarily driven by human activities.",
            "url": "https://example.com/climate"
        }
    ]


class TestModelPropagation:
    """Test that the model= parameter correctly overrides internal model selection."""

    @pytest.mark.asyncio
    async def test_provided_cohere_model_is_used(self, generator, sample_docs):
        """When model= is passed, generate should use it instead of internal cohere_model."""
        # Create a mock "routed" model (e.g., tiny-aya-fire)
        routed_model = MagicMock()
        routed_model.model_id = "tiny-aya-fire"
        routed_model.generate_response = AsyncMock(return_value="Response from fire model")

        response, citations = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="cohere",
            model=routed_model,
        )

        # The routed model should have been called, not the internal one
        routed_model.generate_response.assert_called_once()
        generator.cohere_model.generate_response.assert_not_called()
        assert response == "Response from fire model"

    @pytest.mark.asyncio
    async def test_none_model_defaults_to_internal_cohere(self, generator, sample_docs):
        """When model=None (default), internal cohere_model should be used."""
        generator.cohere_model.generate_response = AsyncMock(
            return_value="Response from global"
        )

        response, citations = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="cohere",
            model=None,
        )

        generator.cohere_model.generate_response.assert_called_once()
        assert response == "Response from global"

    @pytest.mark.asyncio
    async def test_none_model_defaults_to_internal_nova(self, generator, sample_docs):
        """When model=None and model_type='nova', internal nova_model should be used."""
        generator.nova_model.generate_response = AsyncMock(
            return_value="Response from nova"
        )

        response, citations = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="nova",
            model=None,
        )

        generator.nova_model.generate_response.assert_called_once()
        assert response == "Response from nova"

    @pytest.mark.asyncio
    async def test_provided_model_overrides_nova_too(self, generator, sample_docs):
        """model= parameter should work for nova model_type as well."""
        custom_nova = MagicMock()
        custom_nova.generate_response = AsyncMock(return_value="Custom nova response")

        response, citations = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="nova",
            model=custom_nova,
        )

        custom_nova.generate_response.assert_called_once()
        generator.nova_model.generate_response.assert_not_called()


class TestCitationExtraction:
    """Test that citations are properly extracted from processed documents."""

    @pytest.mark.asyncio
    async def test_citations_include_title_url_content(self, generator, sample_docs):
        """Each citation should have title, url, content, and snippet."""
        generator.cohere_model.generate_response = AsyncMock(return_value="Test response")

        _, citations = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="cohere",
        )

        assert len(citations) >= 1
        citation = citations[0]
        assert "title" in citation
        assert "url" in citation
        assert "content" in citation
        assert "snippet" in citation

    @pytest.mark.asyncio
    async def test_conversation_context_excluded_from_citations(self, generator):
        """Synthetic 'Conversation Context' docs should not appear in citations."""
        generator.cohere_model.generate_response = AsyncMock(return_value="Test response")

        # Trigger the empty-docs + conversation_history fallback
        _, citations = await generator.generate_response(
            query="Tell me more",
            documents=[],
            model_type="cohere",
            conversation_history=[
                {"role": "user", "content": "What is climate change?"},
                {"role": "assistant", "content": "Climate change is..."},
            ],
        )

        # No citation should have title 'Conversation Context' with empty URL
        for c in citations:
            if c["title"] == "Conversation Context":
                assert c["url"], "Conversation Context with empty URL should be filtered"


class TestDocPreprocessing:
    """Test the _doc_preprocessing method."""

    @pytest.fixture
    def generator_plain(self):
        with patch("src.models.gen_response_unified.BedrockModel"), \
             patch("src.models.gen_response_unified.CohereModel"):
            return UnifiedResponseGenerator()

    def test_skips_empty_content(self, generator_plain):
        """Documents with no content should be filtered out."""
        docs = [
            {"title": "Empty", "content": "", "url": "https://example.com"},
            {"title": "Valid Doc", "content": "This is a sufficiently long piece of text about climate.", "url": "https://example.com/valid"},
        ]
        result = generator_plain._doc_preprocessing(docs)
        assert len(result) == 1
        assert result[0]["title"] == "Valid Doc"

    def test_skips_short_content(self, generator_plain):
        """Documents with content < 10 chars should be filtered out."""
        docs = [
            {"title": "Too Short", "content": "Hi", "url": "https://example.com"},
        ]
        result = generator_plain._doc_preprocessing(docs)
        assert len(result) == 0

    def test_url_extraction_from_list(self, generator_plain):
        """URL in list format should extract the first element."""
        docs = [
            {"title": "Doc", "content": "Enough content for preprocessing to accept this document.", "url": ["https://a.com", "https://b.com"]},
        ]
        result = generator_plain._doc_preprocessing(docs)
        assert result[0]["url"] == "https://a.com"

    def test_snippet_truncation(self, generator_plain):
        """Content > 200 chars should have a truncated snippet."""
        long_content = "x" * 300
        docs = [
            {"title": "Long", "content": long_content, "url": "https://example.com"},
        ]
        result = generator_plain._doc_preprocessing(docs)
        assert result[0]["snippet"].endswith("...")
        assert len(result[0]["snippet"]) == 203  # 200 + "..."

    def test_content_cleaning(self, generator_plain):
        """Escaped newlines and quotes should be cleaned."""
        docs = [
            {"title": "Dirty", "content": 'Line one\\nLine two\\\"quoted\\\"', "url": "https://example.com"},
        ]
        result = generator_plain._doc_preprocessing(docs)
        assert "\\n" not in result[0]["content"]
        assert '\\"' not in result[0]["content"]


class TestEnglishGuard:
    """Test the hard guard that strips non-ASCII from English responses."""

    @pytest.mark.asyncio
    async def test_english_response_strips_non_latin(self, generator, sample_docs):
        """When language_code is 'en', non-ASCII characters should be removed."""
        # Model returns response with Chinese characters mixed in
        mixed_response = "Climate change is real. \u6c14\u5019\u53d8\u5316 This is important."
        generator.cohere_model.generate_response = AsyncMock(return_value=mixed_response)

        response, _ = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="cohere",
            language_code="en",
        )

        # Chinese characters should be stripped
        assert "\u6c14\u5019\u53d8\u5316" not in response
        assert "Climate change is real." in response

    @pytest.mark.asyncio
    async def test_non_english_response_preserves_characters(self, generator, sample_docs):
        """When language_code is NOT 'en', non-ASCII characters should be preserved."""
        chinese_response = "\u6c14\u5019\u53d8\u5316\u662f\u771f\u5b9e\u7684\u3002"
        generator.cohere_model.generate_response = AsyncMock(return_value=chinese_response)

        response, _ = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="cohere",
            language_code="zh",
        )

        assert "\u6c14\u5019\u53d8\u5316" in response

    @pytest.mark.asyncio
    async def test_english_guard_preserves_urls(self, generator, sample_docs):
        """URLs in English responses should not be mangled by the guard."""
        response_with_url = "See [Climate Info](https://example.com/path?q=\u00e9) for details."
        generator.cohere_model.generate_response = AsyncMock(return_value=response_with_url)

        response, _ = await generator.generate_response(
            query="What is climate change?",
            documents=sample_docs,
            model_type="cohere",
            language_code="en",
        )

        assert "https://example.com" in response


class TestErrorHandling:
    """Test error paths in generate_response."""

    @pytest.mark.asyncio
    async def test_invalid_model_type_raises(self, generator, sample_docs):
        """Invalid model_type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid model_type"):
            await generator.generate_response(
                query="test",
                documents=sample_docs,
                model_type="invalid",
            )

    @pytest.mark.asyncio
    async def test_empty_docs_no_history_raises(self, generator):
        """Empty documents with no conversation history should raise ValueError."""
        with pytest.raises(ValueError, match="No valid documents"):
            await generator.generate_response(
                query="test",
                documents=[],
                model_type="cohere",
            )

    @pytest.mark.asyncio
    async def test_empty_docs_with_history_uses_fallback(self, generator):
        """Empty documents with conversation history should use fallback doc."""
        generator.cohere_model.generate_response = AsyncMock(return_value="Fallback response")

        response, _ = await generator.generate_response(
            query="Tell me more",
            documents=[],
            model_type="cohere",
            conversation_history=[
                {"role": "user", "content": "What is climate change?"},
                {"role": "assistant", "content": "It is..."},
            ],
        )

        assert response == "Fallback response"
