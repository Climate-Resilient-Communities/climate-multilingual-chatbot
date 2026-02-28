"""
Cohere Flow Module — Tiny-Aya regional models + embed-english-v3.0 embeddings.

Replaces both the old CohereModel (Command-A) and local BGE-M3 embeddings
with a unified Cohere-API-based approach.
"""
import os
import sys
import cohere
import json
import asyncio
import logging
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.env_loader import load_environment
from src.models.system_messages import CLIMATE_SYSTEM_MESSAGE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tiny-Aya regional language sets
# ---------------------------------------------------------------------------
# Fire: South Asian languages
FIRE_LANGUAGES = {
    'hi', 'bn', 'pa', 'ur', 'gu', 'ta', 'te', 'mr',
    'ne', 'si', 'ml', 'kn', 'or', 'as', 'sd', 'ks',
}

# Earth: African languages
EARTH_LANGUAGES = {
    'sw', 'yo', 'ha', 'ig', 'am', 'so', 'rw', 'sn', 'zu', 'xh',
    'st', 'tn', 'ny', 'lg', 'wo', 'ff', 'bm', 'ti', 'om', 'rn',
}

# Water: Asia-Pacific + Western Asia + Europe (excluding English)
WATER_LANGUAGES = {
    # Asia-Pacific
    'zh', 'ja', 'ko', 'th', 'vi', 'id', 'ms', 'tl', 'my', 'km',
    'lo', 'mn', 'ka', 'jv',
    # Western Asia
    'ar', 'he', 'fa', 'tr', 'ku',
    # Europe (non-English)
    'ru', 'uk', 'pl', 'cs', 'ro', 'el', 'bg', 'sr', 'hr', 'sk',
    'sl', 'hu', 'lt', 'lv', 'et', 'nl', 'de', 'fr', 'it', 'pt',
    'es', 'sv', 'da', 'no', 'fi', 'is', 'ca', 'gl', 'eu', 'sq',
    'bs', 'mk', 'mt',
}


def resolve_tiny_aya_model(language_code: str) -> Tuple[str, str]:
    """Return (model_id, region_label) for a language code.

    Priority: fire → earth → water → global.
    """
    lc = (language_code or 'en').lower().split('-')[0]
    if lc in FIRE_LANGUAGES:
        return 'tiny-aya-fire', 'fire'
    if lc in EARTH_LANGUAGES:
        return 'tiny-aya-earth', 'earth'
    if lc in WATER_LANGUAGES:
        return 'tiny-aya-water', 'water'
    return 'tiny-aya-global', 'global'


# ---------------------------------------------------------------------------
# CohereEmbedder — replaces local BGE-M3
# ---------------------------------------------------------------------------
class CohereEmbedder:
    """Cohere embed-english-v3.0 API wrapper that replaces local BGE-M3.

    Produces 1024-dim dense embeddings (same dimension as BGE-M3).
    No sparse embeddings — pipeline uses dense-only search (alpha=1.0).
    """

    def __init__(self, api_key: Optional[str] = None):
        load_environment()
        self._api_key = api_key or os.getenv("COHERE_API_KEY")
        self._client = cohere.Client(self._api_key)
        self.model_id = "embed-english-v3.0"
        self.dimensions = 1024
        logger.info("CohereEmbedder initialized (embed-english-v3.0, 1024-dim)")

    def encode(self, texts: List[str], input_type: str = "search_query",
               return_dense: bool = True, return_sparse: bool = False,
               return_colbert_vecs: bool = False) -> Dict[str, Any]:
        """Mimic BGE-M3 encode() interface so downstream code needs minimal changes.

        Returns dict with:
            dense_vecs: np.ndarray of shape (N, 1024)
            lexical_weights: list of empty dicts (sparse not available)
        """
        t0 = time.perf_counter()
        response = self._client.embed(
            texts=texts,
            model=self.model_id,
            input_type=input_type,
            embedding_types=["float"],
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        dense_vecs = np.array(response.embeddings.float_, dtype=np.float32)
        logger.info(
            f"dep=cohere_embed op=encode ms={elapsed_ms} n_texts={len(texts)} "
            f"dim={dense_vecs.shape[1] if dense_vecs.ndim == 2 else 0}"
        )
        return {
            'dense_vecs': dense_vecs,
            'lexical_weights': [{} for _ in texts],  # empty sparse for compatibility
        }


# ---------------------------------------------------------------------------
# CohereModel — Tiny-Aya chat + translation + classification
# ---------------------------------------------------------------------------
class CohereModel:
    """Cohere chat model using Tiny-Aya regional models via the Cohere API."""

    def __init__(self, model_id: str = "tiny-aya-global"):
        """Initialize CohereModel with Cohere client."""
        try:
            load_environment()
            self.client = cohere.Client(os.getenv("COHERE_API_KEY"))
            self.model_id = model_id
            logger.info(f"CohereModel initialized (model={model_id})")
        except Exception as e:
            logger.error(f"CohereModel init failed: {e}")
            raise

    def with_model(self, model_id: str) -> "CohereModel":
        """Return a lightweight copy using a different model_id (shares the same client)."""
        new = object.__new__(CohereModel)
        new.client = self.client
        new.model_id = model_id
        return new

    # ----- Low-level call wrapper -----
    def _chat_sync(self, message: str, preamble: Optional[str] = None,
                   chat_history: Optional[List[Dict]] = None,
                   temperature: float = 0.3, max_tokens: int = 2000,
                   model_override: Optional[str] = None) -> str:
        """Synchronous Cohere chat call."""
        t0 = time.perf_counter()
        model = model_override or self.model_id
        kwargs: Dict[str, Any] = {
            "model": model,
            "message": message,
            "temperature": temperature,
        }
        if preamble:
            kwargs["preamble"] = preamble
        if chat_history:
            kwargs["chat_history"] = chat_history
        response = self.client.chat(**kwargs)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(f"dep=cohere_chat model={model} ms={elapsed_ms} status=OK")
        return (response.text or "").strip()

    async def _chat_async(self, message: str, **kwargs) -> str:
        """Run sync chat in executor to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._chat_sync(message, **kwargs))

    # ----- Public API (mirrors BedrockModel interface) -----

    async def classify(self, prompt: str, system_message: Optional[str] = None,
                       options: Optional[List[str]] = None) -> str:
        try:
            if not prompt:
                return ""
            options_instruction = ""
            if options:
                options_instruction = f"Choose exactly one option from: {', '.join(options)}."
            user_message = f"{prompt}\n{options_instruction}\nAnswer with ONLY the classification result, no explanations."
            result = await self._chat_async(user_message, preamble=system_message, temperature=0.1)
            if options and result not in options:
                for opt in options:
                    if opt.lower() in result.lower():
                        return opt
                logger.warning(f"Classification '{result}' not in {options}, using first")
                return options[0]
            return result
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return options[0] if options else ""

    async def content_generation(self, prompt: str, system_message: Optional[str] = None,
                                 max_tokens: int = 2000) -> str:
        try:
            return await self._chat_async(prompt, preamble=system_message, temperature=0.1)
        except Exception as e:
            logger.error(f"Content generation error: {e}")
            return ""

    async def query_normalizer(self, query: str, language: str) -> str:
        try:
            msg = (f"Rephrase the following query to its simplest, most basic form:\n"
                   f"1. Remove any personal information.\n"
                   f"2. Convert to simple, direct questions.\n"
                   f"3. If already simple, leave it unchanged.\n"
                   f"Respond with ONLY the rephrased query in {language}.\n"
                   f"Query: {query}")
            return await self._chat_async(msg, temperature=0.1)
        except Exception as e:
            logger.error(f"Query normalization error: {e}")
            return query.lower().strip()

    async def translate(self, text: str, source_lang: Optional[str] = None,
                        target_lang: Optional[str] = None) -> str:
        try:
            if not text or source_lang == target_lang:
                return text
            src = (source_lang or "source language").strip()
            tgt = (target_lang or "target language").strip()
            terminology_rules = (
                "When responding in a non-English language, use professional, domain-specific "
                "climate terminology consistent with authoritative sources (IPCC translations, "
                "national climate reports). Preserve scientific accuracy."
            )
            zh_rules = (
                "If target is Chinese, use standard terms from CMA/IPCC: "
                "'全球气候变化' for global phenomenon, '气候变化缓解' for mitigation, '极端气候事件' for extreme events."
            )
            extra = zh_rules if tgt.lower() in {"zh", "zh-cn", "zh-tw", "chinese"} else ""
            msg = (
                "You are a professional climate-science translator.\n"
                f"Translate from {src} to {tgt}.\n"
                f"Style: Formal. Tone: Informative.\n{terminology_rules}{extra}\n"
                "Provide ONLY the translation, no preface or notes.\n\n"
                f"Text:\n{text}\n\nTranslation:"
            )
            return await self._chat_async(msg, temperature=0.1)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    # Backward-compatibility aliases
    async def nova_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        return await self.translate(text, source_lang, target_lang)

    async def nova_classification(self, prompt: str, system_message: Optional[str] = None,
                                  options: Optional[List[str]] = None) -> str:
        return await self.classify(prompt, system_message, options)

    async def cohere_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        return await self.translate(text, source_lang, target_lang)

    async def cohere_classification(self, prompt: str, system_message: Optional[str] = None,
                                    options: Optional[List[str]] = None) -> str:
        return await self.classify(prompt, system_message, options)

    async def cohere_content_generation(self, prompt: str, system_message: Optional[str] = None) -> str:
        return await self.content_generation(prompt, system_message)

    async def generate_response(
        self,
        query: str,
        documents: List[dict],
        description: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """Generate a climate-aware response using Tiny-Aya."""
        try:
            formatted_docs = "\n\n".join([
                f"Document {i+1}:\n{doc.get('content', '')}"
                for i, doc in enumerate(documents)
            ])
            custom = description or "Provide a clear, accurate response based on the given context."
            user_message = (
                f"Based on the following documents and any relevant conversation history, "
                f"provide a direct answer to this question: {query}\n\n"
                f"Documents for context:\n{formatted_docs}\n\n"
                f"Additional Instructions:\n"
                f"1. {custom}\n"
                "2. Use proper markdown formatting with headers\n"
                "3. Write in plain, conversational English\n"
                "4. Include relatable examples when appropriate\n"
                "5. Suggest realistic, low-cost actions when relevant\n"
                "6. Ensure headers have a space after # symbols\n"
                "7. Start with a clear main header summarizing the topic\n"
                "8. DO NOT repeat the user's question as the header"
            )
            chat_history = []
            if conversation_history:
                for msg in conversation_history:
                    if "user" in msg and "assistant" in msg:
                        chat_history.append({"role": "USER", "message": str(msg["user"] or "")})
                        chat_history.append({"role": "CHATBOT", "message": str(msg["assistant"] or "")})
                    elif msg.get("role") == "user":
                        chat_history.append({"role": "USER", "message": str(msg.get("content", ""))})
                    elif msg.get("role") in ("assistant", "chatbot"):
                        chat_history.append({"role": "CHATBOT", "message": str(msg.get("content", ""))})
                chat_history = [m for m in chat_history if m.get("message", "").strip()]

            result = await self._chat_async(
                user_message,
                preamble=CLIMATE_SYSTEM_MESSAGE,
                chat_history=chat_history or None,
                temperature=0.3,
            )
            return self._ensure_proper_markdown(result)
        except Exception as e:
            logger.error(f"generate_response error: {e}")
            raise

    @staticmethod
    def _ensure_proper_markdown(text: str) -> str:
        if not text:
            return text
        lines = text.split("\n")
        formatted = []
        for line in lines:
            if line.strip().startswith('#'):
                pos = len(line) - len(line.lstrip('#'))
                if pos < len(line) and line[pos] != ' ':
                    line = line[:pos] + ' ' + line[pos:]
            formatted.append(line)
        return "\n".join(formatted)

    async def close(self):
        """Graceful shutdown (Cohere client is sync, nothing to await)."""
        pass


async def main():
    load_environment()
    model = CohereModel()
    test = "What is climate change and how does it affect us?"
    print("Query normalization:")
    print(await model.query_normalizer(test, "english"))
    print("\nTranslation:")
    print(await model.translate("Climate change is a serious issue.", "english", "spanish"))

if __name__ == "__main__":
    asyncio.run(main())
