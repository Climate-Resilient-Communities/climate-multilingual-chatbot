"""
Boundary fakes for keyless end-to-end QA.

Everything inside the app runs for real — FastAPI routers, the
ClimateQueryPipeline, query rewriting/classification parsing, routing,
translation orchestration, caching, guards, and response contracts. Only the
EXTERNAL network clients are replaced with deterministic fakes:

    - AWS Bedrock (Nova)      → heuristic classifier/translator
    - Cohere API (Tiny-Aya)   → templated generation + marked translations
    - HuggingFace embeddings  → hash-based vectors
    - Pinecone retrieval      → keyword search over data/rag_docs fixtures
    - Redis                   → in-memory dict

Every faked call is appended to an audit log (JSONL) so QA scenarios can
assert not just the HTTP response but what the pipeline asked the models to
do (e.g. "translation was requested with target=spanish").

Magic query triggers for regression scenarios:
    "qa wrongscript ..."  → generation returns a pure-Chinese answer even
                            though English was requested (the pre-fix
                            numbers-bug condition)
    "qa digitsonly ..."   → generation returns digits/punctuation only
                            (must be rejected, never rendered)
"""

import json
import logging
import os
import re
import time
from pathlib import Path

logger = logging.getLogger("qa.boundary")

REPO_ROOT = Path(__file__).parent.parent.parent
AUDIT_LOG = Path(os.getenv("QA_AUDIT_LOG", "/tmp/qa_boundary_audit.jsonl"))

# Visible per-language markers so tests (and humans reading screenshots) can
# see which language the pipeline requested. Real MT is not available offline.
TRANSLATION_MARKERS = {
    "spanish": "[Respuesta en español]",
    "french": "[Réponse en français]",
    "german": "[Antwort auf Deutsch]",
    "chinese": "【中文回复】",
    "japanese": "【日本語の回答】",
    "korean": "[한국어 답변]",
    "arabic": "[الإجابة بالعربية]",
    "urdu": "[اردو میں جواب]",
    "hindi": "[हिंदी में उत्तर]",
    "russian": "[Ответ на русском]",
    "portuguese": "[Resposta em português]",
    "italian": "[Risposta in italiano]",
    "polish": "[Odpowiedź po polsku]",
    "tagalog": "[Sagot sa Filipino]",
    "filipino": "[Sagot sa Filipino]",
    "english": "[English answer]",
}

CHINESE_SAMPLE_ANSWER = (
    "# 气候变化的影响\n\n"
    "气候变化是指温度和天气模式的长期变化。多伦多的社区正面临洪水、"
    "极端高温和空气质量恶化等问题。居民可以采取节能、绿化和应急准备等行动。"
    "了解更多信息请访问市政府网站。气候适应需要社区共同努力。"
)


def _audit(kind: str, **fields):
    try:
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "kind": kind, **fields}, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Fixture corpus: the real migrated community docs + a few general docs
# ---------------------------------------------------------------------------

def _load_fixture_docs():
    docs = []
    tp_path = REPO_ROOT / "data" / "rag_docs" / "thorncliffe-park.json"
    if tp_path.exists():
        for d in json.loads(tp_path.read_text(encoding="utf-8")):
            docs.append({
                "title": d["title"],
                "url": [d["url"]] if d.get("url") else [],
                "content": d["text"],
                "chunk_text": d["text"],
                "section_title": d.get("section_title", ""),
                "score": 0.0,
            })
    docs.extend([
        {
            "title": "Toronto Climate Impacts Overview",
            "url": ["https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/transformto/"],
            "content": (
                "Toronto faces increasing climate impacts including more frequent extreme heat events, "
                "riverine and urban flooding from intense rainfall, ice storms, and deteriorating air "
                "quality from wildfire smoke. The TransformTO strategy targets net-zero emissions by 2040. "
                "Residents can prepare emergency kits, use cooling centres during heat warnings, and "
                "reduce their carbon footprint through transit, retrofits, and waste reduction."
            ),
            "chunk_text": "", "section_title": "General", "score": 0.0,
        },
        {
            "title": "Household Flooding Preparedness Guide",
            "url": ["https://www.toronto.ca/services-payments/water-environment/managing-rain-melted-snow/basement-flooding/"],
            "content": (
                "To prepare for flooding: keep valuables out of basements, install a backwater valve, "
                "clear eavestroughs and downspouts, know your building's emergency plan, sign up for "
                "weather alerts, and prepare a 72-hour emergency kit with water, food, and medications. "
                "During heavy rain, avoid underpasses and never walk or drive through floodwater."
            ),
            "chunk_text": "", "section_title": "General", "score": 0.0,
        },
        {
            "title": "Reducing Your Carbon Footprint",
            "url": ["https://www.canada.ca/en/environment-climate-change.html"],
            "content": (
                "Effective personal climate actions include taking public transit, reducing food waste, "
                "improving home insulation, switching to a heat pump, and choosing energy-efficient "
                "appliances. Community actions like tree planting and repair cafes multiply the impact."
            ),
            "chunk_text": "", "section_title": "General", "score": 0.0,
        },
    ])
    for d in docs:
        d["chunk_text"] = d["chunk_text"] or d["content"]
    return docs


FIXTURE_DOCS = _load_fixture_docs()


def _score_docs(query: str):
    q_tokens = set(re.findall(r"[a-z]{3,}", (query or "").lower()))
    scored = []
    for d in FIXTURE_DOCS:
        text = (d["title"] + " " + d["content"]).lower()
        score = sum(1 for t in q_tokens if t in text)
        if score > 0:
            scored.append(({**d, "score": float(score)}, score))
    scored.sort(key=lambda x: -x[1])
    top = [d for d, _ in scored[:5]]
    return top or [dict(FIXTURE_DOCS[-3])]  # general overview fallback


# ---------------------------------------------------------------------------
# Fake model behaviors
# ---------------------------------------------------------------------------

def _detect_lang_heuristic(text: str) -> str:
    t = text or ""
    if re.search(r"[一-鿿]", t):
        return "zh"
    if re.search(r"[぀-ヿ]", t):
        return "ja"
    if re.search(r"[가-힯]", t):
        return "ko"
    if re.search(r"[؀-ۿ]", t):
        return "ar"
    if re.search(r"[Ѐ-ӿ]", t):
        return "ru"
    if re.search(r"[ऀ-ॿ]", t):
        return "hi"
    tl = f" {t.lower()} "
    es_hits = sum(1 for w in (" el ", " la ", " qué ", " que ", " es ", " del ", " cambio ", " escribe ", " sobre ", " un ", " en ") if w in tl)
    en_hits = sum(1 for w in (" the ", " is ", " what ", " how ", " in ", " about ", " me ", " a ", " write ", " can ") if w in tl)
    fr_hits = sum(1 for w in (" le ", " les ", " est ", " qu'est-ce ", " climatique ", " écris ") if w in tl)
    if es_hits >= 2 and es_hits > en_hits:
        return "es"
    if fr_hits >= 2 and fr_hits > en_hits:
        return "fr"
    return "en"


_GREETINGS = ("hello", "hi ", "hey", "hola", "bonjour", "你好", "salut", "how are you")
_THANKS = ("thank", "gracias", "merci", "谢谢")
_GOODBYES = ("bye", "goodbye", "adiós", "adios", "au revoir", "再见")
_INSTRUCTION = ("how do i use", "how does this work", "how to use this", "how to get started")
_OFFTOPIC_HINTS = ("shoes", "shopping", "stock market", "pizza", "football")
_CLIMATE_ES_FR = ("inundacion", "inundaciones", "clima", "climático", "climatico", "calor",
                  "sequía", "sequia", "climatique", "inondation", "chaleur", "carbone")


def _classify(query_lower: str, looks_climate) -> str:
    stripped = query_lower.strip()
    if any(stripped.startswith(g) or f" {g}" in f" {stripped}" for g in _GREETINGS) and len(stripped) < 30:
        return "greeting"
    if any(t in stripped for t in _THANKS) and len(stripped) < 40:
        return "thanks"
    if any(g in stripped for g in _GOODBYES) and len(stripped) < 30:
        return "goodbye"
    if any(i in stripped for i in _INSTRUCTION):
        return "instruction"
    if any(o in stripped for o in _OFFTOPIC_HINTS):
        return "off-topic"
    if looks_climate(stripped) or any(w in stripped for w in _CLIMATE_ES_FR):
        return "on-topic"
    return "off-topic"


async def fake_nova_content_generation(self, prompt: str, system_message: str = None) -> str:
    from src.models.query_rewriter import _looks_climate_any, detect_language_request

    p = prompt or ""

    # Query-rewriter classification prompt. Parse ONLY the [CONTEXT] section at
    # the end — the prompt body contains few-shot examples with their own
    # 'User Query:' lines that must not be mistaken for the real query.
    if "[EXPECTED OUTPUT KEYS]" in p:
        ctx = p.split("[CONTEXT]")[-1]
        m = re.search(r'User Query: "(.*?)"\s*\nEXPECTED LANGUAGE', ctx, re.DOTALL)
        query = m.group(1) if m else ""
        m = re.search(r'Expected Language: "(\w+)"', ctx)
        expected = (m.group(1) if m else "en").lower()

        detected = _detect_lang_heuristic(query)
        requested = detect_language_request(query)
        classification = _classify(query.lower(), _looks_climate_any)
        rewrite = None
        if classification == "on-topic":
            rewrite = query if detected == "en" else "What are the impacts of climate change and how can people prepare?"
            # Strip a leading language directive from the rewrite like a good model
            rewrite = re.sub(r"\b(in|en)\s+(spanish|french|german|chinese|español|inglés)\b", "", rewrite, flags=re.I).strip() or rewrite

        payload = {
            "reason": "qa-fake heuristic classification",
            "language": detected,
            "expected_language": expected,
            "language_match": detected == expected,
            "classification": classification,
            "rewrite_en": rewrite,
            "requested_language": requested,
            "ask_how_to_use": classification == "instruction",
            "how_it_works": None,
            "error": None,
        }
        _audit("nova.rewriter", query=query, out=payload)
        return json.dumps(payload, ensure_ascii=False)

    # Faithfulness evaluation prompt
    if "faithfulness" in p.lower():
        _audit("nova.faithfulness")
        return json.dumps({
            "faithfulness_score": 0.92,
            "supported_claims": ["grounded"],
            "unsupported_claims": [],
            "reasoning": "qa-fake: answer grounded in context",
        })

    # Conversation-relevance scoring prompt
    if "relevance scores" in p.lower():
        _audit("nova.relevance")
        return "3,4,5"

    _audit("nova.generic", prompt_head=p[:80])
    return "QA fake generic response."


async def fake_nova_classification(self, prompt: str, system_message: str = None, options=None) -> str:
    _audit("nova.classification", options=options)
    return (options or ["NO"])[0 if not options else len(options) - 1]  # "NO" for YES/NO follow-up checks


async def fake_translate(self, text: str, source_lang=None, target_lang=None) -> str:
    if not text:
        return text
    target = str(target_lang or "").strip().lower()
    marker = TRANSLATION_MARKERS.get(target)
    _audit("translate", source=str(source_lang), target=target, text_head=text[:60])
    if target in ("english", "en"):
        # Translating INTO English (query translation / wrong-script recovery):
        # return English regardless of the input script.
        if re.search(r"[一-鿿؀-ۿЀ-ӿ]", text):
            return ("Climate change refers to long-term shifts in temperatures and weather "
                    "patterns. Toronto communities face flooding, extreme heat, and air "
                    "quality impacts; residents can prepare with emergency kits and cooling centres.")
        return text
    if marker:
        return f"{marker} {text}"
    return f"[Translated to {target_lang}] {text}"


async def fake_cohere_generate_response(self, query: str, documents=None, description=None, conversation_history=None) -> str:
    q = (query or "").lower()
    _audit("cohere.generate", query=query[:120], model_id=getattr(self, "model_id", "?"), n_docs=len(documents or []))

    if "qa wrongscript" in q:
        return CHINESE_SAMPLE_ANSWER          # wrong-script regression trigger
    if "qa digitsonly" in q:
        return "2050 1.5 30% 26.9 ..."        # digits-only regression trigger

    docs = documents or []
    doc_bits = "\n".join(
        f"- {d.get('title', 'Source')}: {d.get('content', '')[:220]}"
        for d in docs[:3]
    )
    return (
        "# Climate Guidance\n\n"
        f"Here is what the retrieved sources say about your question ({query[:80]}):\n\n"
        f"{doc_bits}\n\n"
        "## What you can do\n\n"
        "- Sign up for local weather alerts and know where the nearest cooling centre is\n"
        "- Prepare a 72-hour emergency kit\n"
        "- Reduce energy use at home to cut emissions\n"
    )


async def fake_cohere_content_generation(self, prompt: str, system_message: str = None) -> str:
    _audit("cohere.content", prompt_head=(prompt or "")[:80])
    if "relevance scores" in (prompt or "").lower():
        return "3,4"
    return "QA fake cohere content."


async def fake_cohere_classify(self, prompt: str, system_message=None, options=None) -> str:
    _audit("cohere.classify", options=options)
    return (options or [""])[0]


class FakeEmbedder:
    EMBED_DIM = 1024

    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texts, **kwargs):
        import numpy as np
        if isinstance(texts, str):
            texts = [texts]
        vecs = []
        for t in texts:
            seed = int.from_bytes(str(t)[:32].encode("utf-8", "ignore").ljust(4, b"x")[:4], "little")
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(self.EMBED_DIM).astype("float32")
            vecs.append(v / (np.linalg.norm(v) or 1.0))
        import numpy as np
        return {"dense_vecs": np.stack(vecs), "lexical_weights": [{} for _ in texts]}


class _FakeRawRedis:
    """Raw redis-py surface used by the consent router (sync get/setex/delete)."""

    def __init__(self, store):
        self._store = store

    def get(self, key):
        return self._store.get(("raw", key))

    def setex(self, key, ttl, value):
        self._store[("raw", key)] = value
        return True

    def delete(self, key):
        return 1 if self._store.pop(("raw", key), None) is not None else 0

    def ping(self):
        return True


class FakeCache:
    """In-memory ClimateCache replacement so cache hits can be QA'd."""
    store = {}

    def __init__(self, *args, **kwargs):
        self.redis_client = _FakeRawRedis(FakeCache.store)

    async def get(self, key):
        hit = FakeCache.store.get(key)
        _audit("cache.get", key=key[:48], hit=hit is not None)
        return hit

    async def set(self, key, value, *args, **kwargs):
        _audit("cache.set", key=key[:48])
        FakeCache.store[key] = value
        return True

    async def get_list(self, key, start, end):
        return []

    async def add_to_list(self, key, value):
        return True

    async def close(self):
        return None


async def fake_get_documents(query, index, embed_model, cohere_client):
    docs = _score_docs(query)
    _audit("retrieval", query=(query or "")[:120], returned=[d["title"] for d in docs])
    return docs


async def fake_link_validation(text):
    return text, {"broken": 0}


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

def install():
    """Patch the external-client boundary. Call BEFORE the app starts."""
    from src.models import nova_flow, cohere_flow, climate_pipeline
    from src.webui.api import main as api_main
    from src.webui.api.routers import chat as chat_router
    from src.webui.api.utils import link_validator

    AUDIT_LOG.write_text("", encoding="utf-8")

    # Nova / Bedrock
    nova_flow.BedrockModel.__init__ = lambda self, *a, **k: setattr(self, "model_id", "qa-fake-nova")
    nova_flow.BedrockModel.content_generation = fake_nova_content_generation
    nova_flow.BedrockModel.nova_content_generation = fake_nova_content_generation
    nova_flow.BedrockModel.translate = fake_translate
    nova_flow.BedrockModel.nova_translation = fake_translate
    nova_flow.BedrockModel.nova_classification = fake_nova_classification

    async def _noop_close(self):
        return None
    nova_flow.BedrockModel.close = _noop_close
    nova_flow.BedrockModel.generate_response = fake_cohere_generate_response

    # Cohere / Tiny-Aya
    cohere_flow.CohereModel.__init__ = lambda self, model_id="tiny-aya-global", *a, **k: setattr(self, "model_id", model_id) or setattr(self, "client", object())
    cohere_flow.CohereModel.generate_response = fake_cohere_generate_response
    cohere_flow.CohereModel.translate = fake_translate
    cohere_flow.CohereModel.cohere_translation = fake_translate
    cohere_flow.CohereModel.content_generation = fake_cohere_content_generation
    cohere_flow.CohereModel.cohere_content_generation = fake_cohere_content_generation
    cohere_flow.CohereModel.classify = fake_cohere_classify
    cohere_flow.CohereModel.cohere_classification = fake_cohere_classify

    # Embeddings + Pinecone + Redis + retrieval
    cohere_flow.HFEmbedder = FakeEmbedder
    climate_pipeline.HFEmbedder = FakeEmbedder
    climate_pipeline.ClimateQueryPipeline._initialize_pinecone_index = lambda self: object()
    climate_pipeline.ClimateQueryPipeline._init_cohere = lambda self: object()
    climate_pipeline.ClimateCache = FakeCache
    climate_pipeline.get_documents = fake_get_documents
    api_main.ClimateCache = FakeCache

    # Background link validation (network)
    link_validator.validate_and_fix_inline_links = fake_link_validation
    chat_router.validate_and_fix_inline_links = fake_link_validation

    logger.info("✅ QA boundary fakes installed (audit log: %s)", AUDIT_LOG)
